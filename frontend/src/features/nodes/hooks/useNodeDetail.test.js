import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";
import { ApiError } from "../../../shared/services/httpClient";

vi.mock("../../../shared/services/nodesService", () => ({
  nodesService: {
    getById: vi.fn(),
    listSensors: vi.fn(),
    listConnectivityLogs: vi.fn(),
    listReceivedReadings: vi.fn(),
  },
}));
vi.mock("../../../shared/services/readingsService", () => ({
  sensorTypesService: { list: vi.fn() },
}));

import { nodesService } from "../../../shared/services/nodesService";
import { sensorTypesService } from "../../../shared/services/readingsService";
import { REFRESH_MS, useNodeDetail } from "./useNodeDetail";

function serve({ readings = [], logs = [] } = {}) {
  nodesService.getById.mockResolvedValue({ node_id: 1, code: "NODE-FLOOR-1" });
  nodesService.listSensors.mockResolvedValue([]);
  nodesService.listConnectivityLogs.mockResolvedValue(logs);
  nodesService.listReceivedReadings.mockResolvedValue(readings);
  sensorTypesService.list.mockResolvedValue([]);
}

const flush = () => act(async () => { await vi.advanceTimersByTimeAsync(0); });
const wait = (ms) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });

function setHidden(hidden) {
  Object.defineProperty(document, "hidden", { configurable: true, get: () => hidden });
}

describe("useNodeDetail", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    setHidden(false);
  });
  afterEach(() => {
    cleanup(); // sin globals de vitest, RTL no desmonta solo: un hook vivo seguiría pidiendo datos
    vi.useRealTimers();
    setHidden(false);
  });

  it("carga el nodo y lo vuelve a pedir cada REFRESH_MS sin volver a «cargando»", async () => {
    serve({ readings: [{ reading_id: 1 }] });
    const { result } = renderHook(() => useNodeDetail("1"));
    expect(result.current.status).toBe("loading");
    await flush();
    expect(result.current.status).toBe("ready");
    expect(result.current.readings).toHaveLength(1);

    serve({ readings: [{ reading_id: 1 }, { reading_id: 2 }] });
    await wait(REFRESH_MS);
    expect(result.current.status).toBe("ready");
    expect(result.current.readings).toHaveLength(2);
    expect(nodesService.listReceivedReadings).toHaveBeenCalledTimes(2);
  });

  it("al abrirse una sesión de conectividad, el siguiente refresco lo muestra como conectado", async () => {
    serve({ logs: [] });
    const { result } = renderHook(() => useNodeDetail("1"));
    await flush();
    expect(result.current.connectivity.connected).toBe(false);

    serve({ logs: [{ started_at: new Date().toISOString(), ended_at: null }] });
    await wait(REFRESH_MS);
    expect(result.current.connectivity.connected).toBe(true);
  });

  it("no pide datos mientras la pestaña está oculta y actualiza al volver a verla", async () => {
    serve();
    renderHook(() => useNodeDetail("1"));
    await flush();

    setHidden(true);
    await wait(REFRESH_MS * 3);
    expect(nodesService.listReceivedReadings).toHaveBeenCalledTimes(1);

    setHidden(false);
    await act(async () => { document.dispatchEvent(new Event("visibilitychange")); });
    await flush();
    expect(nodesService.listReceivedReadings).toHaveBeenCalledTimes(2);
  });

  it("si un refresco falla conserva lo que ya mostraba", async () => {
    serve({ readings: [{ reading_id: 1 }] });
    const { result } = renderHook(() => useNodeDetail("1"));
    await flush();

    nodesService.listReceivedReadings.mockRejectedValue(new Error("red caída"));
    await wait(REFRESH_MS);
    expect(result.current.status).toBe("ready");
    expect(result.current.readings).toHaveLength(1);
  });

  it("un nodo inexistente muestra notfound y no sigue preguntando", async () => {
    serve();
    nodesService.getById.mockRejectedValue(new ApiError(404, { message: "no existe" }));
    const { result } = renderHook(() => useNodeDetail("9"));
    await flush();
    expect(result.current.status).toBe("notfound");

    await wait(REFRESH_MS * 3);
    expect(nodesService.getById).toHaveBeenCalledTimes(1);
  });

  it("deja de actualizar al desmontarse", async () => {
    serve();
    const { unmount } = renderHook(() => useNodeDetail("1"));
    await flush();
    unmount();

    await wait(REFRESH_MS * 3);
    expect(nodesService.getById).toHaveBeenCalledTimes(1);
  });
});
