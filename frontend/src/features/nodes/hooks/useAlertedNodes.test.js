import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";

vi.mock("../../../shared/services/alertsService", () => ({
  alertsService: { subscribeToAlerts: vi.fn() },
}));

import { alertsService } from "../../../shared/services/alertsService";
import { useAlertedNodes } from "./useAlertedNodes";

let stream;
const alert = (id, nodeId, type = "out_of_range", extra = {}) => ({
  alert_id: id, node_id: nodeId, alert_type: type, ended_at: null, handled_by_user_id: null, visible: true, ...extra,
});

describe("useAlertedNodes", () => {
  beforeEach(() => {
    stream = null;
    alertsService.subscribeToAlerts.mockReset();
    alertsService.subscribeToAlerts.mockImplementation((handlers) => {
      stream = handlers;
      return vi.fn();
    });
  });
  afterEach(() => cleanup());

  it("marca en alerta (roja) el nodo con una alerta fuera de rango y en revisar el que solo tiene avisos técnicos", () => {
    const { result } = renderHook(() => useAlertedNodes());
    act(() => {
      [alert(1, 1), alert(2, 1, "technical"), alert(3, 2, "technical")].forEach((a) => stream.onAlert(a));
      stream.onReady();
    });

    expect(result.current.statusByNode).toEqual({ 1: "alert", 2: "warning" });
  });

  it("un nodo sin alertas no aparece, y vuelve a salir cuando la alerta se atiende y termina", () => {
    const { result } = renderHook(() => useAlertedNodes());
    act(() => {
      stream.onAlert(alert(1, 1));
      stream.onReady();
    });
    expect(result.current.statusByNode[3]).toBeUndefined();
    expect(result.current.statusByNode[1]).toBe("alert");

    act(() => stream.onAlert(alert(1, 1, "out_of_range", { visible: false, ended_at: "x", handled_by_user_id: 5 })));
    expect(result.current.statusByNode).toEqual({});
  });

  it("ignora las alertas sin nodo y avisa si se cae el stream", () => {
    const { result } = renderHook(() => useAlertedNodes());
    act(() => {
      stream.onAlert(alert(1, null));
      stream.onReady();
    });
    expect(result.current.statusByNode).toEqual({});

    act(() => stream.onError(new Error("503")));
    expect(result.current.streamDown).toBe(true);
  });

  it("una alerta atendida deja de pintar el nodo aunque siga abierta", () => {
    const { result } = renderHook(() => useAlertedNodes());
    act(() => {
      stream.onAlert(alert(1, 1, "out_of_range", { handled_by_user_id: 5 })); // atendida, sin terminar: sigue visible
      stream.onAlert(alert(2, 2));
      stream.onReady();
    });

    expect(result.current.statusByNode).toEqual({ 2: "alert" });
  });

  it("si de dos alertas del nodo atiende solo una, el nodo sigue en alerta", () => {
    const { result } = renderHook(() => useAlertedNodes());
    act(() => {
      stream.onAlert(alert(1, 1, "out_of_range", { handled_by_user_id: 5 }));
      stream.onAlert(alert(2, 1));
      stream.onReady();
    });
    expect(result.current.statusByNode).toEqual({ 1: "alert" });

    act(() => stream.onAlert(alert(2, 1, "out_of_range", { handled_by_user_id: 5 })));
    expect(result.current.statusByNode).toEqual({});
  });
});

