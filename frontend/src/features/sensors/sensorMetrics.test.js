import { describe, it, expect } from "vitest";
import { groupReadings, markAffected } from "./sensorMetrics";

const sensors = [{ sensor_id: 1, code: "S1", sensor_type_id: 7 }];
const types = [{ sensor_type_id: 7, name: "Temperatura", default_unit: "°C" }];

describe("groupReadings", () => {
  it("agrupa por sensor y métrica con una serie por agregación, ordenada en el tiempo", () => {
    const readings = [
      { sensor_id: 1, metric_id: 5, aggregation: "avg", measured_at: "2026-11-16T10:30:00Z", measured_value: "22.5" },
      { sensor_id: 1, metric_id: 5, aggregation: "avg", measured_at: "2026-11-16T10:00:00Z", measured_value: "21" },
      { sensor_id: 1, metric_id: 5, aggregation: "max", measured_at: "2026-11-16T10:00:00Z", measured_value: "24" },
      { sensor_id: 1, metric_id: 6, aggregation: "avg", measured_at: "2026-11-16T10:00:00Z", measured_value: "50" },
    ];
    const groups = groupReadings(readings, sensors, types);

    expect(groups).toHaveLength(2);
    expect(groups[0].type.name).toBe("Temperatura");
    expect(groups[0].series.map((s) => s.id)).toEqual(["avg", "max"]);
    expect(groups[0].series[0].points.map((p) => p.y)).toEqual([21, 22.5]);
    expect(groups[0].last.y).toBe(22.5);
  });

  it("adjunta la métrica del catálogo del tipo (nombre y unidad), o null si no la describe", () => {
    const withMetrics = [
      {
        ...types[0],
        metrics: [{ metric_id: 5, metric_code: "temperature_c", name: "Temperatura", unit: "°C" }],
      },
    ];
    const readings = [
      { sensor_id: 1, metric_id: 5, aggregation: "avg", measured_at: "2026-11-16T10:00:00Z", measured_value: "21" },
      { sensor_id: 1, metric_id: 99, aggregation: "avg", measured_at: "2026-11-16T10:00:00Z", measured_value: "3" },
    ];
    const [known, unknown] = groupReadings(readings, sensors, withMetrics);

    expect(known.metric.name).toBe("Temperatura");
    expect(unknown.metric).toBeNull();
  });

  it("tolera lecturas de un sensor desconocido", () => {
    const groups = groupReadings(
      [{ sensor_id: 9, metric_id: null, measured_at: "2026-11-16T10:00:00Z", measured_value: "1" }],
      sensors,
      types,
    );
    expect(groups[0].sensor).toBeNull();
    expect(groups[0].series[0].id).toBe("raw");
  });
});

describe("markAffected", () => {
  const chart = (sensorId, metricId) => ({ key: `${sensorId}:${metricId}`, sensorId, metricId });
  const charts = [chart(1, 1), chart(1, 2), chart(2, 3), chart(3, 4)];
  const range = (sensorId, metricId, extra = {}) => ({
    alert_type: "out_of_range", alert_code: "OUT_OF_RANGE_ABOVE", sensor_id: sensorId, metric_id: metricId, ended_at: null, ...extra,
  });

  it("sin alertas deja el orden y no marca nada", () => {
    const result = markAffected(charts, []);
    expect(result.map((c) => c.key)).toEqual(["1:1", "1:2", "2:3", "3:4"]);
    expect(result.every((c) => c.alert === null)).toBe(true);
  });

  it("sube al principio las gráficas afectadas (sensor y variable) y conserva el orden del resto", () => {
    const result = markAffected(charts, [range(2, 3), range(1, 2)]);
    expect(result.map((c) => c.key)).toEqual(["1:2", "2:3", "1:1", "3:4"]);
    expect(result[0].alert).toEqual({ label: "Fuera de rango", tone: "range", live: true });
    expect(result[2].alert).toBeNull();
  });

  it("una alerta de otra variable del mismo sensor no marca las demás gráficas de ese sensor", () => {
    const result = markAffected(charts, [range(1, 2)]);
    expect(result.find((c) => c.key === "1:1").alert).toBeNull();
  });

  it("una alerta del sensor sin variable marca todas sus gráficas", () => {
    const result = markAffected(charts, [range(1, null)]);
    expect(result.filter((c) => c.alert).map((c) => c.key)).toEqual(["1:1", "1:2"]);
  });

  it("fuera de rango va antes que una falla, y una falla antes que un aviso", () => {
    const stuck = { alert_type: "technical", alert_code: "SENSOR_STUCK", sensor_id: 1, metric_id: 1, ended_at: null };
    const battery = { alert_type: "technical", alert_code: "BATTERY_LOW", sensor_id: 3, metric_id: 4, ended_at: null };
    const result = markAffected(charts, [battery, stuck, range(2, 3)]);
    expect(result.map((c) => [c.key, c.alert?.label])).toEqual([
      ["2:3", "Fuera de rango"], ["1:1", "Fallando"], ["3:4", "Con aviso"], ["1:2", undefined]]);
  });

  it("indica si la alerta ya terminó pero sigue sin atender", () => {
    const [first] = markAffected(charts, [range(1, 1, { ended_at: "2026-11-18T04:00:00Z" })]);
    expect(first.alert.live).toBe(false);
  });
});
