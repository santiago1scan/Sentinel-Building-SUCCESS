import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
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

  it("lista cada alerta con su tipo y permite marcarla como atendida", () => {
    const onHandle = vi.fn();
    render(
      <NodeCard
        node={node}
        status="alert"
        onHandle={onHandle}
        openAlerts={[
          { alert_id: 7, alert_type: "out_of_range", alert_code: "OUT_OF_RANGE_ABOVE", handled_by_user_id: null },
          { alert_id: 8, alert_type: "technical", alert_code: "NODE_SILENT", handled_by_user_id: 5 },
        ]}
      />,
    );

    expect(screen.getByText("Fuera de rango")).toBeTruthy();
    expect(screen.getByText("Aviso técnico")).toBeTruthy();
    expect(screen.getByText("✓ Atendida")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Marcar atendida" }));
    expect(onHandle).toHaveBeenCalledWith(7);
  });

  it("muestra 'Guardando…' mientras se marca la alerta", () => {
    render(
      <NodeCard
        node={node}
        status="warning"
        openAlerts={[{ alert_id: 7, alert_type: "technical", alert_code: "X", handled_by_user_id: null }]}
        handling={{ 7: true }}
      />,
    );
    expect(screen.getByRole("button", { name: "Guardando…" }).disabled).toBe(true);
  });

  it("sin IP muestra 'Sin IP'", () => {
    render(<NodeCard node={{ ...node, ip_address: null }} status="off" />);
    expect(screen.getByText("Sin IP")).toBeTruthy();
  });
});
