import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./httpClient", () => ({
  httpClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { httpClient } from "./httpClient";
import { buildingsService } from "./buildingsService";

describe("buildingsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list usa límite y offset por defecto", () => {
    buildingsService.list();
    expect(httpClient.get).toHaveBeenCalledWith("/buildings", {
      params: { limit: 100, offset: 0 },
    });
  });

  it("getById y listZones construyen la ruta correcta", () => {
    buildingsService.getById(3);
    buildingsService.listZones(3);
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/buildings/3");
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/buildings/3/zones");
  });

  it("create envía name y address", () => {
    const payload = { name: "Edificio SB-001", address: "Bogotá" };
    buildingsService.create(payload);
    expect(httpClient.post).toHaveBeenCalledWith("/buildings", payload);
  });

  it("update hace PATCH y remove hace DELETE", () => {
    buildingsService.update(3, { address: "Popayán" });
    buildingsService.remove(3);
    expect(httpClient.patch).toHaveBeenCalledWith("/buildings/3", { address: "Popayán" });
    expect(httpClient.delete).toHaveBeenCalledWith("/buildings/3");
  });
});
