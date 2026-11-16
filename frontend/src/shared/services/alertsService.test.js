import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./httpClient", () => ({
  httpClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { httpClient } from "./httpClient";
import { alertsService } from "./alertsService";

describe("alertsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list usa límite y offset por defecto", () => {
    alertsService.list();
    expect(httpClient.get).toHaveBeenCalledWith("/alerts", {
      params: { limit: 100, offset: 0 },
    });
  });

  it("list acepta límite y offset personalizados", () => {
    alertsService.list({ limit: 5, offset: 10 });
    expect(httpClient.get).toHaveBeenCalledWith("/alerts", {
      params: { limit: 5, offset: 10 },
    });
  });

  it("listOpen y listUnhandled apuntan a sus rutas", () => {
    alertsService.listOpen();
    alertsService.listUnhandled();
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/alerts/open");
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/alerts/unhandled");
  });

  it("getById, getByReading y getByHandledUser construyen la ruta con el ID", () => {
    alertsService.getById(7);
    alertsService.getByReading(3);
    alertsService.getByHandledUser(9);
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/alerts/7");
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/alerts/reading/3");
    expect(httpClient.get).toHaveBeenNthCalledWith(3, "/alerts/handled-by/9");
  });

  it("getByEventUuid usa el UUID en la ruta", () => {
    alertsService.getByEventUuid("abc-123");
    expect(httpClient.get).toHaveBeenCalledWith("/alerts/event-uuid/abc-123");
  });

  it("handle hace POST sin body, porque el backend toma el usuario del token", () => {
    alertsService.handle(5);
    expect(httpClient.post).toHaveBeenCalledWith("/alerts/5/handle");
  });

  it("update hace PATCH con el payload", () => {
    alertsService.update(5, { status: "closed" });
    expect(httpClient.patch).toHaveBeenCalledWith("/alerts/5", { status: "closed" });
  });
});
