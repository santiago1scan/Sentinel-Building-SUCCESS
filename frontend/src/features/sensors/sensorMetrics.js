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
