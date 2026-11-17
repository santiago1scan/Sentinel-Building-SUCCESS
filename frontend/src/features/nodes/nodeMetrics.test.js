import { describe, it, expect } from "vitest";
import { groupReadings, summarizeConnectivity, formatDuration } from "./nodeMetrics";

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

describe("summarizeConnectivity", () => {
  it("suma el tiempo conectado y detecta la sesión abierta", () => {
    const now = new Date("2026-11-16T12:00:00Z").getTime();
    const summary = summarizeConnectivity(
      [
        { started_at: "2026-11-16T08:00:00Z", ended_at: "2026-11-16T09:00:00Z" },
        { started_at: "2026-11-16T11:00:00Z", ended_at: null },
      ],
      now,
    );
    expect(summary.sessions).toBe(2);
    expect(summary.connected).toBe(true);
    expect(summary.connectedMs).toBe(2 * 3600 * 1000);
  });
});

describe("formatDuration", () => {
  it("formatea segundos, minutos, horas y días", () => {
    expect(formatDuration(40_000)).toBe("40 s");
    expect(formatDuration(15 * 60_000)).toBe("15 min");
    expect(formatDuration(125 * 60_000)).toBe("2 h 05 min");
    expect(formatDuration(50 * 3600_000)).toBe("2 d 2 h");
  });
});
