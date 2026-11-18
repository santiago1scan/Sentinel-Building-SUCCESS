/** Funciones puras que preparan las lecturas de los sensores para las gráficas. */

export const AGGREGATION_LABEL = {
  avg: "Promedio",
  max: "Máximo",
  min: "Mínimo",
  raw: "Incidente",
};

const AGGREGATION_ORDER = ["avg", "max", "min", "raw"];

/**
 * Agrupa las lecturas por sensor y métrica. Cada grupo trae una serie por agregación
 * (promedio, máximo, mínimo, incidente) con puntos { x: ms, y: valor } ordenados en el tiempo.
 */
export function groupReadings(readings, sensors, sensorTypes) {
  const sensorById = new Map(sensors.map((sensor) => [sensor.sensor_id, sensor]));
  const typeById = new Map(sensorTypes.map((type) => [type.sensor_type_id, type]));
  const groups = new Map();

  for (const reading of readings) {
    const key = `${reading.sensor_id}:${reading.metric_id ?? "none"}`;
    if (!groups.has(key)) {
      const sensor = sensorById.get(reading.sensor_id) ?? null;
      groups.set(key, {
        key,
        sensorId: reading.sensor_id,
        sensor,
        type: sensor ? (typeById.get(sensor.sensor_type_id) ?? null) : null,
        metricId: reading.metric_id ?? null,
        byAggregation: {},
      });
    }
    const agg = reading.aggregation ?? "raw";
    const point = { x: new Date(reading.measured_at).getTime(), y: Number(reading.measured_value) };
    if (Number.isNaN(point.x) || Number.isNaN(point.y)) continue;
    (groups.get(key).byAggregation[agg] ??= []).push(point);
  }

  const metricsPerSensor = new Map();
  for (const group of groups.values()) {
    metricsPerSensor.set(group.sensorId, (metricsPerSensor.get(group.sensorId) ?? 0) + 1);
  }

  return [...groups.values()]
    .map((group) => {
      const series = AGGREGATION_ORDER.filter((agg) => group.byAggregation[agg]).map((agg) => ({
        id: agg,
        label: AGGREGATION_LABEL[agg],
        points: group.byAggregation[agg].sort((a, b) => a.x - b.x),
      }));
      const all = series.flatMap((s) => s.points).sort((a, b) => a.x - b.x);
      return {
        key: group.key,
        sensorId: group.sensorId,
        sensor: group.sensor,
        type: group.type,
        metricId: group.metricId,
        // La métrica del catálogo (nombre, unidad y rango normal); null si el tipo no la describe.
        metric: group.type?.metrics?.find((metric) => metric.metric_id === group.metricId) ?? null,
        singleMetric: metricsPerSensor.get(group.sensorId) === 1,
        series,
        count: all.length,
        last: all[all.length - 1] ?? null,
      };
    })
    .sort((a, b) => a.sensorId - b.sensorId || (a.metricId ?? 0) - (b.metricId ?? 0));
}

/** Avisos técnicos que son una falla del sensor (el resto es un aviso, como batería baja). */
const FAULT_CODES = new Set(["SENSOR_STUCK", "SENSOR_IMPOSSIBLE"]);

/**
 * Marca las gráficas que tienen una alerta visible del nodo y las sube al principio.
 *
 * Una gráfica (sensor + variable) está afectada si alguna alerta es de ese sensor y de esa variable (o del
 * sensor completo, sin variable). `alert` queda con {label, tone, live}, o null si no está afectada. Fuera de
 * rango va antes que una falla; dentro de cada grupo se conserva el orden original.
 */
export function markAffected(groups, alerts = []) {
  const rank = { range: 0, fault: 1, notice: 2 };
  const marked = groups.map((group, index) => {
    const matches = alerts.filter(
      (alert) => alert.sensor_id === group.sensorId && (alert.metric_id == null || alert.metric_id === group.metricId),
    );
    if (matches.length === 0) return { group: { ...group, alert: null }, index, rank: 3 };

    const outOfRange = matches.some((alert) => alert.alert_type === "out_of_range");
    const fault = matches.some((alert) => FAULT_CODES.has(alert.alert_code));
    const tone = outOfRange ? "range" : fault ? "fault" : "notice";
    const label = { range: "Fuera de rango", fault: "Fallando", notice: "Con aviso" }[tone];
    return {
      group: { ...group, alert: { label, tone, live: matches.some((alert) => !alert.ended_at) } },
      index,
      rank: rank[tone],
    };
  });
  return marked.sort((a, b) => a.rank - b.rank || a.index - b.index).map((item) => item.group);
}

