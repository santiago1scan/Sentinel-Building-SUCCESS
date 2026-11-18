import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

vi.mock("../../shared/services/buildingsService", () => ({ buildingsService: { getById: vi.fn() } }));
vi.mock("../../shared/services/zonesService", () => ({ zonesService: { listByBuilding: vi.fn() } }));
vi.mock("../../features/floors/services/floorsService", () => ({ floorsService: { listByBuilding: vi.fn() } }));
vi.mock("../../shared/services/nodesService", () => ({ nodesService: { list: vi.fn() } }));
vi.mock("../../features/nodes/hooks/useAlertedNodes", () => ({ useAlertedNodes: vi.fn() }));
vi.mock("../../features/buildings/organisms/PendingRegistrations/PendingRegistrations", () => ({
  default: () => null,
}));

import { buildingsService } from "../../shared/services/buildingsService";
import { zonesService } from "../../shared/services/zonesService";
import { floorsService } from "../../features/floors/services/floorsService";
import { nodesService } from "../../shared/services/nodesService";
import { useAlertedNodes } from "../../features/nodes/hooks/useAlertedNodes";
import BuildingDetailPage from "./BuildingDetailPage";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/panel/builders/1"]}>
      <Routes>
        <Route path="/panel/builders/:buildingId" element={<BuildingDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("BuildingDetailPage con alertas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    buildingsService.getById.mockResolvedValue({ building_id: 1, name: "Sentinel Building", address: null });
    floorsService.listByBuilding.mockResolvedValue([{ floor_id: 1, level: 1, name: "Piso 1" }]);
    zonesService.listByBuilding.mockResolvedValue([{ zone_id: 1, building_id: 1, name: "Zona piso 1", floor_id: 1 }]);
    nodesService.list.mockResolvedValue([
      { node_id: 1, code: "NODE-FLOOR-1", name: "Nodo piso 1", zone_id: 1, ip_address: null },
      { node_id: 2, code: "NODE-FLOOR-2", name: "Nodo piso 2", zone_id: 1, ip_address: null },
    ]);
  });
  afterEach(() => cleanup());

  it("el nodo con una alerta se muestra en rojo y el que no la tiene queda normal", async () => {
    useAlertedNodes.mockReturnValue({ statusByNode: { 1: "alert" }, streamDown: false });
    const { container } = renderPage();

    await screen.findByText("Nodo piso 1");
    const cards = [...container.querySelectorAll("article")];
    const byName = (name) => cards.find((card) => card.textContent.includes(name));
    expect(byName("Nodo piso 1").getAttribute("data-status")).toBe("alert");
    expect(byName("Nodo piso 2").hasAttribute("data-status")).toBe(false);
    expect(screen.getByText("Alerta")).toBeTruthy();
  });

  it("un nodo con solo avisos técnicos queda en «Revisar»", async () => {
    useAlertedNodes.mockReturnValue({ statusByNode: { 2: "warning" }, streamDown: false });
    const { container } = renderPage();

    await screen.findByText("Nodo piso 2");
    const card = [...container.querySelectorAll("article")].find((c) => c.textContent.includes("Nodo piso 2"));
    expect(card.getAttribute("data-status")).toBe("warning");
  });

  it("sin alertas ningún nodo cambia de color", async () => {
    useAlertedNodes.mockReturnValue({ statusByNode: {}, streamDown: false });
    const { container } = renderPage();

    await screen.findByText("Nodo piso 1");
    expect(container.querySelectorAll("article[data-status]")).toHaveLength(0);
  });

  it("cada nodo sigue llevando a su detalle", async () => {
    useAlertedNodes.mockReturnValue({ statusByNode: { 1: "alert" }, streamDown: false });
    renderPage();

    const link = await screen.findByRole("link", { name: "Ver métricas de Nodo piso 1" });
    expect(link.getAttribute("href")).toBe("/panel/nodes/1");
  });
});
