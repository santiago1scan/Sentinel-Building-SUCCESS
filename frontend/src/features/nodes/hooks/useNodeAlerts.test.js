import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";

vi.mock("../../../shared/services/alertsService", () => ({
  alertsService: { subscribeToAlerts: vi.fn(), handle: vi.fn() },
}));

import { alertsService } from "../../../shared/services/alertsService";
import { useNodeAlerts } from "./useNodeAlerts";

let stream;
const closeStream = vi.fn();

const alert = (id, nodeId, extra = {}) => ({
  alert_id: id, node_id: nodeId, alert_type: "out_of_range", alert_code: "OUT_OF_RANGE_ABOVE",
  ended_at: null, handled_by_user_id: null, visible: true, ...extra,
});

const snapshot = (alerts) => act(() => { alerts.forEach((a) => stream.onAlert(a)); stream.onReady(); });

describe("useNodeAlerts", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    stream = null;
    closeStream.mockReset();
    alertsService.handle.mockReset();
    alertsService.subscribeToAlerts.mockReset();
    alertsService.subscribeToAlerts.mockImplementation((handlers) => {
      stream = handlers;
      return closeStream;
    });
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("solo conserva las alertas de su nodo", () => {
    const { result } = renderHook(() => useNodeAlerts("1"));
    snapshot([alert(1, 1), alert(2, 2), alert(3, 1)]);

    expect(result.current.alerts.map((a) => a.alert_id).sort()).toEqual([1, 3]);
  });

  it("aplica los cambios en vivo: agrega, y quita la que terminó y ya fue atendida", () => {
    const { result } = renderHook(() => useNodeAlerts("1"));
    snapshot([alert(1, 1)]);

    act(() => stream.onAlert(alert(4, 1)));
    expect(result.current.alerts).toHaveLength(2);
    act(() => stream.onAlert(alert(5, 2))); // de otro nodo: no aparece
    expect(result.current.alerts).toHaveLength(2);
    act(() => stream.onAlert(alert(1, 1, { visible: false, ended_at: "x", handled_by_user_id: 5 })));
    expect(result.current.alerts.map((a) => a.alert_id)).toEqual([4]);
  });

  it("al reconectar, el nuevo estado reemplaza la lista (no quedan alertas fantasma)", () => {
    const { result } = renderHook(() => useNodeAlerts("1"));
    snapshot([alert(1, 1), alert(2, 1)]);

    act(() => stream.onError(new Error("503")));
    expect(result.current.streamDown).toBe(true);
    expect(closeStream).toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(5000));
    expect(alertsService.subscribeToAlerts).toHaveBeenCalledTimes(2);
    snapshot([alert(2, 1)]); // la 1 se atendió mientras no había conexión
    expect(result.current.alerts.map((a) => a.alert_id)).toEqual([2]);
    expect(result.current.streamDown).toBe(false);
  });

  it("al cambiar de nodo muestra solo las del nuevo, sin reconectar el stream", () => {
    const { result, rerender } = renderHook(({ id }) => useNodeAlerts(id), { initialProps: { id: "1" } });
    snapshot([alert(1, 1), alert(2, 2)]);
    expect(result.current.alerts.map((a) => a.alert_id)).toEqual([1]);

    rerender({ id: "2" });
    expect(result.current.alerts.map((a) => a.alert_id)).toEqual([2]);
    expect(alertsService.subscribeToAlerts).toHaveBeenCalledTimes(1);
  });

  it("atender una categoría atiende todas sus alertas pendientes", async () => {
    alertsService.handle.mockImplementation(async (id) => alert(id, 1, { handled_by_user_id: 5 }));
    const { result } = renderHook(() => useNodeAlerts("1"));
    snapshot([alert(1, 1), alert(2, 1)]);

    await act(async () => {
      await result.current.handleGroup({ key: "1:temperature", unhandled: [{ alert_id: 1 }, { alert_id: 2 }] });
    });

    expect(alertsService.handle.mock.calls.map(([id]) => id)).toEqual([1, 2]);
    expect(result.current.alerts.every((a) => a.handled_by_user_id === 5)).toBe(true);
    expect(result.current.handling).toEqual({});
    expect(result.current.actionError).toBe("");
  });

  it("si una no se pudo atender, conserva la que quedó pendiente y avisa", async () => {
    alertsService.handle.mockImplementation(async (id) => {
      if (id === 2) throw new Error("red");
      return alert(id, 1, { handled_by_user_id: 5 });
    });
    const { result } = renderHook(() => useNodeAlerts("1"));
    snapshot([alert(1, 1), alert(2, 1)]);

    await act(async () => {
      await result.current.handleGroup({ key: "1:temperature", unhandled: [{ alert_id: 1 }, { alert_id: 2 }] });
    });

    expect(result.current.actionError).toMatch(/No pudimos marcar/);
    expect(result.current.alerts.find((a) => a.alert_id === 2).handled_by_user_id).toBeNull();
  });

  it("al desmontarse cierra el stream y deja de reintentar", () => {
    const { unmount } = renderHook(() => useNodeAlerts("1"));
    act(() => stream.onError(new Error("503")));
    unmount();
    closeStream.mockClear();

    act(() => vi.advanceTimersByTime(20000));
    expect(alertsService.subscribeToAlerts).toHaveBeenCalledTimes(1);
  });
});
