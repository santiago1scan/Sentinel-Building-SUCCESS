import { describe, expect, it } from "vitest";
import { buildCatalog, groupAlerts } from "./alertGroups";

const sensors = [
  { sensor_id: 1, code: "ADXL355-N1", sensor_type_id: 10 },
  { sensor_id: 2, code: "AMG8833-N1", sensor_type_id: 20 },
  { sensor_id: 3, code: "BME688-N1", sensor_type_id: 30 },
  { sensor_id: 4, code: "INA219-N1", sensor_type_id: 40 },
];
const types = [
  { sensor_type_id: 10, name: "ADXL355", metrics: [{ metric_id: 1, metric_code: "z_g", name: "Aceleración eje Z", unit: "g", normal_minimum: "0.99", normal_maximum: "1.01" }] },
  {
    sensor_type_id: 20,
    name: "AMG8833",
    metrics: [
      { metric_id: 6, metric_code: "maximum_c", name: "Temperatura máxima de la imagen", unit: "°C", normal_minimum: "17", normal_maximum: "35" },
      { metric_id: 7, metric_code: "average_c", name: "Temperatura promedio de la imagen", unit: "°C", normal_minimum: "17", normal_maximum: "26" },
    ],
  },
  {
    sensor_type_id: 30,
    name: "BME688",
    metrics: [
      { metric_id: 9, metric_code: "temperature_c", name: "Temperatura", unit: "°C", normal_minimum: "10", normal_maximum: "31" },
      { metric_id: 11, metric_code: "pressure_hpa", name: "Presión", unit: "hPa", normal_minimum: "815", normal_maximum: "835" },
    ],
  },
  { sensor_type_id: 40, name: "INA219", metrics: [{ metric_id: 14, metric_code: "bus_voltage_v", name: "Voltaje", unit: "V", normal_minimum: "11", normal_maximum: "12" }] },
];
const catalog = buildCatalog(sensors, types);

let id = 0;
const alert = (extra) => ({
  alert_id: ++id, node_id: 1, alert_type: "out_of_range", alert_code: "OUT_OF_RANGE_ABOVE", direction: "above",
  sensor_id: null, metric_id: null, ended_at: null, handled_by_user_id: null, ...extra,
});

describe("groupAlerts", () => {
  it("un incidente con varias variables queda en una sola alerta por categoría", () => {
    const groups = groupAlerts([
      alert({ sensor_id: 2, metric_id: 6 }),
      alert({ sensor_id: 2, metric_id: 7 }),
      alert({ sensor_id: 3, metric_id: 9 }), // temperatura del BME688: también «temperatura»
    ], catalog);

    expect(groups).toHaveLength(1);
    expect(groups[0].category).toBe("temperature");
    expect(groups[0].title).toBe("Alerta de temperatura");
    expect(groups[0].alerts).toHaveLength(3);
    expect(groups[0].sensors.map((s) => s.code)).toEqual(["AMG8833-N1", "BME688-N1"]);
    expect(groups[0].sensors[0].items.map((i) => i.metricName)).toEqual([
      "Temperatura máxima de la imagen", "Temperatura promedio de la imagen"]);
  });

  it("cada sensor trae sus etiquetas sin repetir: fuera de rango, fallando o el aviso propio", () => {
    const [temperature] = groupAlerts([
      alert({ sensor_id: 2, metric_id: 6 }),
      alert({ sensor_id: 2, metric_id: 7 }),
      alert({ alert_type: "technical", alert_code: "SENSOR_STUCK", direction: null, sensor_id: 2, metric_id: 6 }),
    ], catalog);
    expect(temperature.sensors.map((sensor) => sensor.tags.map((tag) => tag.text))).toEqual([
      ["Fuera de rango", "Fallando"]]);

    const [energy] = groupAlerts([
      alert({ alert_type: "technical", alert_code: "BATTERY_LOW", direction: null, sensor_id: 4, metric_id: 14 }),
    ], catalog);
    expect(energy.category).toBe("energy");
    expect(energy.sensors[0].tags).toEqual([{ tone: "notice", text: "Batería baja" }]);
  });

  it("separa temperatura, movimiento, energía y calidad del aire, en ese orden", () => {
    const groups = groupAlerts([
      alert({ sensor_id: 4, metric_id: 14 }),
      alert({ sensor_id: 3, metric_id: 11 }),
      alert({ sensor_id: 1, metric_id: 1, direction: "below" }),
      alert({ sensor_id: 2, metric_id: 6 }),
    ], catalog);

    expect(groups.map((g) => g.category)).toEqual(["temperature", "motion", "energy", "air"]);
    expect(new Set(groups.map((g) => g.key)).size).toBe(4);
  });

  it("describe la dirección y el rango normal de cada variable fuera de rango", () => {
    const [group] = groupAlerts([alert({ sensor_id: 3, metric_id: 11 })], catalog);
    const [item] = group.sensors[0].items;
    expect(item.label).toBe("Por encima del rango normal");
    expect(item.range).toBe("815–835 hPa");
    expect(item.tone).toBe("range");
  });

  it("marca como fallando un sensor con aviso técnico y lo cuenta en su categoría", () => {
    const [group] = groupAlerts([alert({
      alert_type: "technical", alert_code: "SENSOR_STUCK", direction: null, sensor_id: 2, metric_id: 6 })], catalog);
    expect(group.category).toBe("temperature");
    expect(group.severity).toBe("warning");
    expect(group.sensors[0].items[0]).toMatchObject({ tone: "fault", label: "Fallando: valor sin variación", range: null });
  });

  it("un aviso del nodo sin sensor va a su propio grupo", () => {
    const [group] = groupAlerts([alert({ alert_type: "technical", alert_code: "NODE_SILENT", direction: null })], catalog);
    expect(group.category).toBe("node");
    expect(group.sensors[0].code).toBe("Nodo completo");
  });

  it("fuera de rango manda sobre el aviso técnico en la severidad", () => {
    const [group] = groupAlerts([
      alert({ sensor_id: 2, metric_id: 6 }),
      alert({ alert_type: "technical", alert_code: "SENSOR_STUCK", sensor_id: 2, metric_id: 7 }),
    ], catalog);
    expect(group.severity).toBe("alert");
  });

  it("sigue viva mientras alguna variable no haya terminado, y pendiente hasta atender todas", () => {
    const ended = "2026-11-18T04:00:00Z";
    const [group] = groupAlerts([
      alert({ sensor_id: 2, metric_id: 6, ended_at: ended }),
      alert({ sensor_id: 2, metric_id: 7 }),
    ], catalog);
    expect(group.live).toBe(true);
    expect(group.attended).toBe(false);
    expect(group.unhandled).toHaveLength(2);

    const [done] = groupAlerts([
      alert({ sensor_id: 2, metric_id: 6, ended_at: ended, handled_by_user_id: 5 }),
      alert({ sensor_id: 2, metric_id: 7, ended_at: ended, handled_by_user_id: 5 }),
    ], catalog);
    expect(done.live).toBe(false);
    expect(done.attended).toBe(true);
  });

  it("una terminada sin atender sigue en el grupo (no está viva, pero queda pendiente)", () => {
    const [group] = groupAlerts([alert({ sensor_id: 2, metric_id: 6, ended_at: "2026-11-18T04:00:00Z" })], catalog);
    expect(group.live).toBe(false);
    expect(group.attended).toBe(false);
  });

  it("sin catálogo cae al modelo del sensor o a «otros», sin romperse", () => {
    const [group] = groupAlerts([alert({ sensor_id: 99, metric_id: 99 })]);
    expect(group.category).toBe("other");
    expect(group.sensors[0].code).toBe("Sensor #99");

    const byModel = buildCatalog(sensors, [{ sensor_type_id: 40, name: "INA219", metrics: [] }]);
    expect(groupAlerts([alert({ sensor_id: 4, metric_id: 123 })], byModel)[0].category).toBe("energy");
  });
});
