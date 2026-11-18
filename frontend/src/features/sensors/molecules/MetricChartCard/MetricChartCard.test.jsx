import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MetricChartCard from "./MetricChartCard";

const series = [{ id: "avg", label: "Promedio", points: [{ x: Date.UTC(2026, 10, 16, 10), y: 21.5 }] }];

function group(overrides = {}) {
  return {
    key: "1:5",
    sensorId: 1,
    sensor: { sensor_id: 1, code: "BME688-NODE-1" },
    type: { sensor_type_id: 7, name: "BME688", default_unit: null, normal_minimum: null, normal_maximum: null },
    metric: { metric_id: 5, metric_code: "temperature_c", name: "Temperatura", unit: "°C", normal_minimum: "18", normal_maximum: "28" },
    metricId: 5,
    singleMetric: false,
    series,
    count: 1,
    last: { x: series[0].points[0].x, y: 21.5 },
    ...overrides,
  };
}

describe("MetricChartCard", () => {
  it("titula con el nombre de la métrica, el sensor y la unidad del catálogo", () => {
    render(<MetricChartCard group={group()} />);

    expect(screen.getByRole("heading", { name: "Temperatura · BME688-NODE-1" })).toBeTruthy();
    expect(screen.getByText(/21\.50? °C|21\.5 °C/)).toBeTruthy();
  });

  it("si el catálogo no describe la métrica, cae al número de métrica", () => {
    render(<MetricChartCard group={group({ metric: null })} />);

    expect(screen.getByRole("heading", { name: "métrica #5 · BME688-NODE-1" })).toBeTruthy();
  });
});
