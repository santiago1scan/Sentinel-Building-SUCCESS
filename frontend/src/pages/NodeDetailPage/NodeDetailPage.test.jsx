import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

vi.mock("../../features/nodes/hooks/useNodeDetail", () => ({ useNodeDetail: vi.fn() }));
vi.mock("../../features/nodes/hooks/useNodeAlerts", () => ({ useNodeAlerts: vi.fn() }));

import { useNodeDetail } from "../../features/nodes/hooks/useNodeDetail";
import { useNodeAlerts } from "../../features/nodes/hooks/useNodeAlerts";
import NodeDetailPage from "./NodeDetailPage";

const T = "2026-11-18T10:00:00Z";
const sensors = [
  { sensor_id: 1, code: "ADXL355-N1", sensor_type_id: 10 },
  { sensor_id: 2, code: "AMG8833-N1", sensor_type_id: 20 },
];
const sensorTypes = [
  { sensor_type_id: 10, name: "ADXL355", metrics: [{ metric_id: 1, metric_code: "z_g", name: "Aceleración eje Z", unit: "g" }] },
  { sensor_type_id: 20, name: "AMG8833", metrics: [{ metric_id: 6, metric_code: "maximum_c", name: "Temperatura máxima de la imagen", unit: "°C", normal_minimum: "17", normal_maximum: "35" }] },
];
// El acelerómetro va primero por id; la temperatura es la que está en alerta.
const readings = [
  { sensor_id: 1, metric_id: 1, aggregation: "avg", measured_at: T, measured_value: "1" },
  { sensor_id: 2, metric_id: 6, aggregation: "avg", measured_at: T, measured_value: "59" },
];

const detail = () => ({
  status: "ready",
  node: { node_id: 1, code: "NODE-FLOOR-1", name: "Piso 1", zone_id: 1, registered_at: T },
  sensors, sensorTypes, readings, logs: [], now: Date.parse(T),
  connectivity: { connected: true, connectedSince: Date.parse(T), connectedMs: 1000, sessions: 1 },
});

const temperatureAlert = {
  alert_id: 5, node_id: 1, alert_type: "out_of_range", alert_code: "OUT_OF_RANGE_ABOVE", direction: "above",
  sensor_id: 2, metric_id: 6, ended_at: null, handled_by_user_id: null,
};

function renderPage(alertState = {}) {
  useNodeDetail.mockReturnValue(detail());
  useNodeAlerts.mockReturnValue({
    alerts: [], streamDown: false, handling: {}, actionError: "", handleGroup: vi.fn(), ...alertState,
  });
  return render(
    <MemoryRouter initialEntries={["/panel/nodes/1"]}>
      <Routes>
        <Route path="/panel/nodes/:nodeId" element={<NodeDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const chartTitles = () => screen.getAllByRole("heading", { level: 3 })
  .map((h) => h.textContent)
  .filter((text) => text.includes(" · "));

describe("NodeDetailPage con alertas", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it("sin alertas no muestra la tarjeta y deja las gráficas en su orden", () => {
    renderPage();

    expect(screen.queryByText("Alertas del nodo")).toBeNull();
    expect(chartTitles()).toEqual(["Aceleración eje Z · ADXL355-N1", "Temperatura máxima de la imagen · AMG8833-N1"]);
  });

  it("con una alerta muestra la misma alerta por categoría que /panel", () => {
    renderPage({ alerts: [temperatureAlert] });

    const section = screen.getByRole("region", { name: "Alertas del nodo" });
    expect(within(section).getByText("Alerta de temperatura")).toBeTruthy();
    expect(within(section).getByText("AMG8833-N1")).toBeTruthy();
    expect(within(section).getByText("Fuera de rango")).toBeTruthy();
    expect(within(section).getByRole("button", { name: "Marcar atendida" })).toBeTruthy();
  });

  it("sube la gráfica afectada al principio y la marca en rojo", () => {
    const { container } = renderPage({ alerts: [temperatureAlert] });

    expect(chartTitles()).toEqual(["Temperatura máxima de la imagen · AMG8833-N1", "Aceleración eje Z · ADXL355-N1"]);
    const cards = [...container.querySelectorAll("article[data-alert]")];
    expect(cards).toHaveLength(1);
    expect(cards[0].textContent).toContain("Temperatura máxima de la imagen");
  });

  it("atender entrega la categoría completa al hook", () => {
    const handleGroup = vi.fn();
    renderPage({ alerts: [temperatureAlert], handleGroup });

    fireEvent.click(screen.getByRole("button", { name: "Marcar atendida" }));
    expect(handleGroup).toHaveBeenCalledTimes(1);
    expect(handleGroup.mock.calls[0][0]).toMatchObject({ category: "temperature", key: "1:temperature" });
  });

  it("avisa si se cae el stream de alertas y si no se pudo atender", () => {
    renderPage({ streamDown: true, actionError: "No pudimos marcar la alerta como atendida. Intenta de nuevo." });

    expect(screen.getByText(/Sin actualizaciones de alertas en vivo/)).toBeTruthy();
    expect(screen.getByText(/No pudimos marcar la alerta/)).toBeTruthy();
  });

  it("al atenderla deja de estar en rojo: la tarjeta queda neutra y las gráficas vuelven a su orden", () => {
    const attended = { ...temperatureAlert, handled_by_user_id: 5, handled_at: "2026-11-18T10:05:00Z" };
    const { container } = renderPage({ alerts: [attended] });

    // La condición sigue (la alerta no terminó), así que la fila se lista, pero atendida.
    const section = screen.getByRole("region", { name: "Alertas del nodo" });
    expect(section.getAttribute("data-status")).toBe("attended");
    expect(within(section).getByText("✓ Atendida")).toBeTruthy();
    expect(within(section).queryByRole("button", { name: "Marcar atendida" })).toBeNull();

    expect(container.querySelectorAll("article[data-alert]")).toHaveLength(0);
    expect(chartTitles()).toEqual(["Aceleración eje Z · ADXL355-N1", "Temperatura máxima de la imagen · AMG8833-N1"]);
  });

  it("si queda una categoría sin atender, el borde sigue en rojo y solo sus gráficas se marcan", () => {
    const attended = { ...temperatureAlert, handled_by_user_id: 5 };
    const motion = {
      alert_id: 6, node_id: 1, alert_type: "out_of_range", alert_code: "OUT_OF_RANGE_BELOW", direction: "below",
      sensor_id: 1, metric_id: 1, ended_at: null, handled_by_user_id: null,
    };
    const { container } = renderPage({ alerts: [attended, motion] });

    expect(screen.getByRole("region", { name: "Alertas del nodo" }).getAttribute("data-status")).toBe("alert");
    const marked = [...container.querySelectorAll("article[data-alert]")];
    expect(marked).toHaveLength(1);
    expect(marked[0].textContent).toContain("Aceleración eje Z"); // la de movimiento, que sigue sin atender
  });
});

