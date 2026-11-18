import { describe, it, expect, afterEach, vi } from "vitest";
import { render as baseRender, screen, cleanup, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import NodeCard from "./NodeCard";

/** La tarjeta lleva enlaces al detalle del nodo: necesita un Router. */
const render = (ui) => baseRender(<MemoryRouter>{ui}</MemoryRouter>);

const node = { node_id: 1, code: "N-01", name: "Sensor piso 2", zone_id: 4, ip_address: "10.0.0.5" };

describe("NodeCard", () => {
  afterEach(() => cleanup());

  it("muestra el nombre, la etiqueta de estado y los datos del nodo", () => {
    const { container } = render(<NodeCard node={node} status="connected" />);

    expect(screen.getByRole("heading", { name: "Sensor piso 2" })).toBeTruthy();
    expect(screen.getByText("Conectado")).toBeTruthy();
    expect(screen.getByText("N-01")).toBeTruthy();
    expect(screen.getByText("10.0.0.5")).toBeTruthy();
    expect(container.querySelector("article").getAttribute("data-status")).toBe("connected");
  });

  it("sin IP muestra 'Sin IP'", () => {
    render(<NodeCard node={{ ...node, ip_address: null }} status="off" />);
    expect(screen.getByText("Sin IP")).toBeTruthy();
  });

  it("sin zona muestra un guion", () => {
    render(<NodeCard node={{ ...node, zone_id: null }} status="off" />);
    expect(screen.getByText("—")).toBeTruthy();
  });

  const group = (extra = {}) => ({
    key: "1:temperature",
    category: "temperature",
    title: "Alerta de temperatura",
    label: "Temperatura",
    severity: "alert",
    live: true,
    attended: false,
    unhandled: [{ alert_id: 7 }],
    sensors: [
      { sensorId: 2, code: "AMG8833-N1", tags: [{ tone: "range", text: "Fuera de rango" }] },
      { sensorId: 3, code: "BME688-N1", tags: [{ tone: "fault", text: "Fallando" }] },
    ],
    ...extra,
  });

  it("muestra una sola alerta por categoría y qué sensores están fuera de rango o fallando", () => {
    render(<NodeCard node={node} status="alert" alertGroups={[group()]} />);

    expect(screen.getAllByText("Alerta de temperatura")).toHaveLength(1);
    expect(screen.getByText("Activa")).toBeTruthy();
    expect(screen.getByText("AMG8833-N1")).toBeTruthy();
    expect(screen.getByText("Fuera de rango")).toBeTruthy();
    expect(screen.getByText("BME688-N1")).toBeTruthy();
    expect(screen.getByText("Fallando")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Marcar atendida" })).toHaveLength(1);
  });

  it("no lista el detalle por variable (dirección, nombre, rango ni «ya volvió»)", () => {
    const value = group();
    value.sensors[0].items = [
      { alert: { alert_id: 7 }, tone: "range", label: "Por encima del rango normal", metricName: "Temperatura máxima de la imagen", range: "17–35 °C", active: false },
    ];
    render(<NodeCard node={node} status="alert" alertGroups={[value]} />);

    expect(screen.queryByText(/Por encima del rango normal/)).toBeNull();
    expect(screen.queryByText("Temperatura máxima de la imagen")).toBeNull();
    expect(screen.queryByText(/normal 17/)).toBeNull();
    expect(screen.queryByText(/ya volvió a la normalidad/)).toBeNull();
  });

  it("atender entrega el grupo completo", () => {
    const onHandle = vi.fn();
    const value = group();
    render(<NodeCard node={node} status="alert" alertGroups={[value]} onHandle={onHandle} />);

    fireEvent.click(screen.getByRole("button", { name: "Marcar atendida" }));
    expect(onHandle).toHaveBeenCalledWith(value);
  });

  it("una alerta que terminó pero no se atendió lo dice y sigue pidiendo atenderla", () => {
    render(<NodeCard node={node} status="alert" alertGroups={[group({ live: false })]} />);
    expect(screen.getByText("Terminó · sin atender")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Marcar atendida" })).toBeTruthy();
  });

  it("una categoría atendida muestra la marca en vez del botón", () => {
    render(<NodeCard node={node} status="alert" alertGroups={[group({ attended: true, unhandled: [] })]} />);
    expect(screen.getByText("✓ Atendida")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Marcar atendida" })).toBeNull();
  });

  it("muestra 'Guardando…' mientras se marca la categoría", () => {
    render(<NodeCard node={node} status="warning" alertGroups={[group()]} handling={{ "1:temperature": true }} />);
    expect(screen.getByRole("button", { name: "Guardando…" }).disabled).toBe(true);
  });

  it("hacer clic en la alerta lleva al detalle del nodo, y atender no navega", () => {
    const onHandle = vi.fn();
    baseRender(
      <MemoryRouter initialEntries={["/panel"]}>
        <Routes>
          <Route path="/panel" element={<NodeCard node={node} status="alert" alertGroups={[group()]} onHandle={onHandle} />} />
          <Route path="/panel/nodes/:nodeId" element={<p>Detalle del nodo</p>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Marcar atendida" }));
    expect(onHandle).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Detalle del nodo")).toBeNull();

    const link = screen.getByRole("link", { name: /alerta de temperatura/i });
    expect(link.getAttribute("href")).toBe("/panel/nodes/1");
    fireEvent.click(link);
    expect(screen.getByText("Detalle del nodo")).toBeTruthy();
  });
});

