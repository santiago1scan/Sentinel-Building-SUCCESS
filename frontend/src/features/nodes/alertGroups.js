/**
 * Agrupa las alertas abiertas de un nodo por categoría (temperatura, movimiento, energía…).
 *
 * El backend crea una alerta por sensor, variable y dirección, así que un solo incidente abre varias.
 * El panel las presenta como UNA alerta viva por nodo y categoría, que sigue ahí hasta que alguien la
 * marque como atendida (la regla de visibilidad ya conserva una alerta terminada hasta atenderla).
 * Las filas del backend no cambian: siguen siendo el detalle de cada variable, para el historial.
 */

/** Orden en que se muestran las categorías. */
export const CATEGORIES = {
  temperature: { label: "Temperatura", title: "Alerta de temperatura" },
  motion: { label: "Movimiento", title: "Alerta de movimiento" },
  energy: { label: "Energía", title: "Alerta de energía" },
  air: { label: "Calidad del aire", title: "Alerta de calidad del aire" },
  node: { label: "Nodo", title: "Alerta del nodo" },
  other: { label: "Otros", title: "Otras alertas" },
};
const CATEGORY_ORDER = Object.keys(CATEGORIES);

/** Variable del catálogo (metric_code) → categoría. */
const METRIC_CATEGORY = {
  maximum_c: "temperature", average_c: "temperature", hot_pixels: "temperature", temperature_c: "temperature",
  x_g: "motion", y_g: "motion", z_g: "motion", rms_g: "motion", frequency_hz: "motion",
  bus_voltage_v: "energy", current_ma: "energy", power_mw: "energy", power_source: "energy", battery_low: "energy",
  humidity_percent: "air", pressure_hpa: "air", iaq_index: "air", tvoc_ppb: "air",
};

/** Si la variable no está en el catálogo conocido, se usa el modelo del sensor. */
const MODEL_CATEGORY = { ADXL355: "motion", AMG8833: "temperature", INA219: "energy", BME688: "air" };

/** Avisos técnicos: qué dicen y si son una falla del sensor. */
const TECHNICAL = {
  SENSOR_STUCK: { label: "Fallando: valor sin variación", fault: true },
  SENSOR_IMPOSSIBLE: { label: "Fallando: valor imposible", fault: true },
  BATTERY_LOW: { label: "Batería baja", fault: false },
  ON_BATTERY_POWER: { label: "Funciona con batería", fault: false },
  NODE_SILENT: { label: "Sin enviar datos", fault: true },
};

const DIRECTION_LABEL = { above: "Por encima del rango normal", below: "Por debajo del rango normal" };

const formatNumber = (value) => {
  const number = Number(value);
  return Number.isInteger(number) ? String(number) : String(Number(number.toFixed(2)));
};

/** "17–35 °C", o null si la variable no tiene rango. */
function formatRange(metric) {
  if (!metric || metric.normal_minimum == null || metric.normal_maximum == null) return null;
  const unit = metric.unit ? ` ${metric.unit}` : "";
  return `${formatNumber(metric.normal_minimum)}–${formatNumber(metric.normal_maximum)}${unit}`;
}

/** Índices del catálogo para resolver sensor, tipo y variable de una alerta. */
export function buildCatalog(sensors = [], sensorTypes = []) {
  const sensorById = new Map(sensors.map((sensor) => [sensor.sensor_id, sensor]));
  const typeById = new Map(sensorTypes.map((type) => [type.sensor_type_id, type]));
  const metricById = new Map();
  for (const type of sensorTypes) {
    for (const metric of type.metrics ?? []) metricById.set(metric.metric_id, metric);
  }
  return { sensorById, typeById, metricById };
}

function categoryOf(alert, metric, model) {
  if (alert.sensor_id == null && alert.metric_id == null) return "node";
  return METRIC_CATEGORY[metric?.metric_code] ?? MODEL_CATEGORY[model] ?? "other";
}

/**
 * Etiquetas de un sensor dentro de la tarjeta, sin repetir: «Fuera de rango», «Fallando» o, para avisos
 * del nodo o de batería, el propio aviso. El detalle por variable queda en `items`.
 */
function sensorTags(sensorId, items) {
  const tags = new Map();
  for (const item of items) {
    const text = sensorId == null || item.tone === "notice"
      ? item.label
      : item.tone === "fault" ? "Fallando" : "Fuera de rango";
    if (!tags.has(text)) tags.set(text, { tone: item.tone, text });
  }
  return [...tags.values()];
}

/** Una línea del detalle: qué variable de qué sensor, y por qué está en la alerta. */
function describe(alert, metric) {
  const technical = TECHNICAL[alert.alert_code];
  let label;
  let tone;
  if (alert.alert_type === "out_of_range") {
    label = DIRECTION_LABEL[alert.direction] ?? "Fuera de rango";
    tone = "range";
  } else {
    label = technical?.label ?? alert.alert_code;
    tone = technical?.fault ? "fault" : "notice";
  }
  return {
    alert,
    tone,
    label,
    metricName: metric?.name || metric?.metric_code || null,
    range: alert.alert_type === "out_of_range" ? formatRange(metric) : null,
    active: !alert.ended_at,
  };
}

/**
 * @param {Array} alerts Alertas visibles de UN nodo.
 * @param {ReturnType<typeof buildCatalog>} catalog
 * @returns {Array<{key, category, title, label, severity, live, attended, alerts, unhandled, sensors}>}
 */
export function groupAlerts(alerts, catalog = buildCatalog()) {
  const groups = new Map();
  for (const alert of alerts) {
    const sensor = catalog.sensorById.get(alert.sensor_id) ?? null;
    const type = sensor ? catalog.typeById.get(sensor.sensor_type_id) : null;
    const metric = catalog.metricById.get(alert.metric_id) ?? null;
    const category = categoryOf(alert, metric, type?.name);

    if (!groups.has(category)) {
      groups.set(category, { category, nodeId: alert.node_id, alerts: [], sensorMap: new Map() });
    }
    const group = groups.get(category);
    group.alerts.push(alert);

    const sensorKey = alert.sensor_id ?? "node";
    if (!group.sensorMap.has(sensorKey)) {
      group.sensorMap.set(sensorKey, {
        sensorId: alert.sensor_id ?? null,
        code: sensor?.code ?? (alert.sensor_id != null ? `Sensor #${alert.sensor_id}` : "Nodo completo"),
        model: type?.name ?? null,
        items: [],
      });
    }
    group.sensorMap.get(sensorKey).items.push(describe(alert, metric));
  }

  return CATEGORY_ORDER.filter((category) => groups.has(category)).map((category) => {
    const group = groups.get(category);
    const unhandled = group.alerts.filter((alert) => !alert.handled_by_user_id);
    return {
      key: `${group.nodeId}:${category}`,
      category,
      title: CATEGORIES[category].title,
      label: CATEGORIES[category].label,
      // Fuera de rango manda sobre un aviso técnico.
      severity: group.alerts.some((alert) => alert.alert_type === "out_of_range") ? "alert" : "warning",
      // Viva = alguna de sus variables sigue fuera de rango (o con el aviso abierto).
      live: group.alerts.some((alert) => !alert.ended_at),
      attended: unhandled.length === 0,
      alerts: group.alerts,
      unhandled,
      sensors: [...group.sensorMap.values()]
        .map((sensor) => ({ ...sensor, tags: sensorTags(sensor.sensorId, sensor.items) }))
        .sort((a, b) => a.code.localeCompare(b.code)),
    };
  });
}
