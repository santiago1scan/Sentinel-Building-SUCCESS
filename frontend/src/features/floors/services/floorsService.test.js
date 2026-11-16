import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../../shared/services/httpClient", () => ({
  httpClient: { get: vi.fn(), post: vi.fn() },
}));

import { httpClient } from "../../../shared/services/httpClient";
import { floorsService } from "./floorsService";

describe("floorsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listByBuilding pide los pisos del edificio", () => {
    floorsService.listByBuilding(7);
    expect(httpClient.get).toHaveBeenCalledWith("/floors/building/7");
  });

  it("create envía building_id, level y name a /floors", () => {
    floorsService.create({ building_id: 7, level: -1, name: null });
    expect(httpClient.post).toHaveBeenCalledWith("/floors", { building_id: 7, level: -1, name: null });
  });
});
