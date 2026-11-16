import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import NodesPage from "./NodesPage";
import { nodesService } from "../../shared/services/nodesService";
import { alertsService } from "../../shared/services/alertsService";
import { connectivityService } from "../../shared/services/connectivityService";

vi.mock("../../shared/services/nodesService", () => ({
  nodesService: { list: vi.fn() },
}));
vi.mock("../../shared/services/alertsService", () => ({
  alertsService: { listOpen: vi.fn() },
}));
vi.mock("../../shared/services/connectivityService", () => ({
  connectivityService: { listActiveByNode: vi.fn() },
}));

const nodes = [
  { node_id: 1, code: "N-01", name: "Entrada", zone_id: 1, ip_address: null },
  { node_id: 2, code: "N-02", name: "Pasillo", zone_id: 1, ip_address: null },
  { node_id: 3, code: "N-03", name: "Bodega", zone_id: 2, ip_address: null },
];

describe("NodesPage", () => {
  beforeEach(() => {
    nodesService.list.mockResolvedValue(nodes);
    alertsService.listOpen.mockResolvedValue([
      { alert_id: 9, node_id: 2, alert_type: "out_of_range" },
    ]);
    connectivityService.listActiveByNode.mockImplementation(async (id) =>
      id === 1 || id === 2 ? [{ connectivity_id: id, node_id: id }] : [],
    );
  });

  afterEach(() => cleanup());

  it("muestra cada nodo con su estado derivado y ordena primero la alerta", async () => {
    const { container } = render(<NodesPage />);

    await screen.findByRole("heading", { name: "Pasillo" });
    const order = [...container.querySelectorAll("article h3")].map((h) => h.textContent);
    expect(order).toEqual(["Pasillo", "Entrada", "Bodega"]);

    const states = [...container.querySelectorAll("article")].map((a) => a.dataset.status);
    expect(states).toEqual(["alert", "connected", "off"]);
  });

  it("filtra por texto y por estado", async () => {
    render(<NodesPage />);
    await screen.findByRole("heading", { name: "Pasillo" });

    fireEvent.change(screen.getByLabelText("Buscar por nombre o código"), {
      target: { value: "bod" },
    });
    expect(screen.queryByRole("heading", { name: "Pasillo" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Bodega" })).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Buscar por nombre o código"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Estado"), { target: { value: "connected" } });
    expect(screen.getByRole("heading", { name: "Entrada" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Bodega" })).toBeNull();
  });

  it("muestra un error con opción de reintentar si la carga falla", async () => {
    nodesService.list.mockRejectedValueOnce(new Error("fallo"));
    render(<NodesPage />);

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText("No pudimos cargar los nodos.")).toBeTruthy();
  });
});
