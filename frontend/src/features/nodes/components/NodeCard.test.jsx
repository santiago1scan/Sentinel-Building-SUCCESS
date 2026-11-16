import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import NodeCard from "./NodeCard";

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

  it("indica las alertas abiertas en singular y plural", () => {
    const { rerender } = render(
      <NodeCard node={node} status="warning" openAlerts={[{ alert_type: "technical" }]} />,
    );
    expect(screen.getByText(/1 alerta abierta/)).toBeTruthy();

    rerender(
      <NodeCard
        node={node}
        status="alert"
        openAlerts={[{ alert_type: "out_of_range" }, { alert_type: "technical" }]}
      />,
    );
    expect(screen.getByText(/2 alertas abiertas/)).toBeTruthy();
  });

  it("sin IP muestra 'Sin IP'", () => {
    render(<NodeCard node={{ ...node, ip_address: null }} status="off" />);
    expect(screen.getByText("Sin IP")).toBeTruthy();
  });
});
