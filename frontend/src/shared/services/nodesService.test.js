import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./httpClient", () => ({
  httpClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { httpClient } from "./httpClient";
import { nodesService } from "./nodesService";

describe("nodesService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list usa límite y offset por defecto", () => {
    nodesService.list();
    expect(httpClient.get).toHaveBeenCalledWith("/nodes", {
      params: { limit: 100, offset: 0 },
    });
  });

  it("getById y getByCode construyen la ruta correcta", () => {
    nodesService.getById(1);
    nodesService.getByCode("NODE-001");
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/nodes/1");
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/nodes/code/NODE-001");
  });

  it("listByZone, listSensors, listConnectivityLogs y listReceivedReadings usan sus rutas anidadas", () => {
    nodesService.listByZone(4);
    nodesService.listSensors(1);
    nodesService.listConnectivityLogs(1);
    nodesService.listReceivedReadings(1);
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/nodes/zone/4");
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/nodes/1/sensors");
    expect(httpClient.get).toHaveBeenNthCalledWith(3, "/nodes/1/connectivity-logs");
    expect(httpClient.get).toHaveBeenNthCalledWith(4, "/nodes/1/received-readings");
  });

  it("update hace PATCH y remove hace DELETE", () => {
    nodesService.update(1, { name: "Nuevo" });
    nodesService.remove(1);
    expect(httpClient.patch).toHaveBeenCalledWith("/nodes/1", { name: "Nuevo" });
    expect(httpClient.delete).toHaveBeenCalledWith("/nodes/1");
  });

  it("revoke hace POST a la ruta de revocación", () => {
    nodesService.revoke(1);
    expect(httpClient.post).toHaveBeenCalledWith("/nodes/1/revoke");
  });
});
