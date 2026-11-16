import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./httpClient", () => ({
  httpClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { httpClient } from "./httpClient";
import { zonesService } from "./zonesService";

describe("zonesService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list usa límite y offset por defecto", () => {
    zonesService.list();
    expect(httpClient.get).toHaveBeenCalledWith("/zones", {
      params: { limit: 100, offset: 0 },
    });
  });

  it("getById y listByBuilding construyen la ruta correcta", () => {
    zonesService.getById(2);
    zonesService.listByBuilding(8);
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/zones/2");
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/zones/building/8");
  });

  it("create envía el payload con building_id, name y floor", () => {
    const payload = { building_id: 1, name: "Piso 1", floor: 1 };
    zonesService.create(payload);
    expect(httpClient.post).toHaveBeenCalledWith("/zones", payload);
  });

  it("update hace PATCH y remove hace DELETE", () => {
    zonesService.update(2, { name: "Piso 2" });
    zonesService.remove(2);
    expect(httpClient.patch).toHaveBeenCalledWith("/zones/2", { name: "Piso 2" });
    expect(httpClient.delete).toHaveBeenCalledWith("/zones/2");
  });
});
