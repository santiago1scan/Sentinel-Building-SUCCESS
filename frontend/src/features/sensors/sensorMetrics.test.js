import { describe, it, expect } from "vitest";
import { groupReadings } from "./sensorMetrics";

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
