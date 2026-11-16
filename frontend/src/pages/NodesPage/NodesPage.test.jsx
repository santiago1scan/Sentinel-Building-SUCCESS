import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent, act } from "@testing-library/react";
import NodesPage from "./NodesPage";
import { nodesService } from "../../shared/services/nodesService";
import { alertsService } from "../../shared/services/alertsService";

vi.mock("../../shared/services/nodesService", () => ({
  nodesService: { list: vi.fn() },
}));
vi.mock("../../shared/services/alertsService", () => ({
  alertsService: { subscribeToAlerts: vi.fn(), handle: vi.fn() },
}));

const nodes = [
  { node_id: 1, code: "N-01", name: "Entrada", zone_id: 1, ip_address: null },
  { node_id: 2, code: "N-02", name: "Pasillo", zone_id: 1, ip_address: null },
  { node_id: 3, code: "N-03", name: "Bodega", zone_id: 2, ip_address: null },
];

let stream;
const closeStream = vi.fn();

function alert(id, nodeId, type = "out_of_range", extra = {}) {
  return {
    alert_id: id,
    node_id: nodeId,
    alert_type: type,
    alert_code: "X",
    ended_at: null,
    handled_by_user_id: null,
    visible: true,
    ...extra,
  };
}

/** Simula que el stream entrega el estado actual al conectarse y avisa que terminó. */
function sendSnapshot(alerts) {
  act(() => {
    alerts.forEach((a) => stream.onAlert(a));
    stream.onReady();
  });
}

async function renderWithSnapshot(alerts) {
  render(<NodesPage />);
  await act(async () => {});
  sendSnapshot(alerts);
}

describe("NodesPage", () => {
  beforeEach(() => {
    stream = null;
    closeStream.mockReset();
    nodesService.list.mockResolvedValue(nodes);
    alertsService.handle.mockReset();
    alertsService.subscribeToAlerts.mockImplementation((handlers) => {
      stream = handlers;
      return closeStream;
    });
  });

  afterEach(() => cleanup());

  it("no carga alertas por GET: se conecta al stream y muestra lo que llega", async () => {
    await renderWithSnapshot([alert(9, 2)]);

    expect(screen.getByRole("heading", { name: "Pasillo" })).toBeTruthy();
    expect(alertsService.subscribeToAlerts).toHaveBeenCalledTimes(1);
  });

  it("muestra solo los nodos con alertas, con la alerta fuera de rango primero", async () => {
    const { container } = render(<NodesPage />);
    await act(async () => {});
    sendSnapshot([alert(9, 2), alert(10, 1, "technical")]);

    const names = [...container.querySelectorAll("article h3")].map((h) => h.textContent);
    expect(names).toEqual(["Pasillo", "Entrada"]);
    expect(screen.queryByRole("heading", { name: "Bodega" })).toBeNull();
  });

  it("muestra 'No hay nodos' cuando el snapshot llega vacío", async () => {
    await renderWithSnapshot([]);
    expect(screen.getByText("No hay nodos con alertas abiertas.")).toBeTruthy();
  });

  it("agrega un nodo cuando llega una alerta en vivo", async () => {
    await renderWithSnapshot([alert(9, 2)]);

    act(() => stream.onAlert(alert(11, 3, "technical")));

    expect(await screen.findByRole("heading", { name: "Bodega" })).toBeTruthy();
  });

  it("una alerta terminada que nadie atendió sigue en el panel", async () => {
    await renderWithSnapshot([alert(9, 2)]);

    act(() => stream.onAlert(alert(9, 2, "out_of_range", { ended_at: "2026-11-16T10:30:00Z", visible: true })));

    expect(screen.getByRole("heading", { name: "Pasillo" })).toBeTruthy();
  });

  it("quita el nodo cuando la alerta llega como no visible, sin borrarla", async () => {
    await renderWithSnapshot([alert(9, 2)]);

    act(() =>
      stream.onAlert(alert(9, 2, "out_of_range", {
        ended_at: "2026-11-16T10:30:00Z",
        handled_by_user_id: 5,
        visible: false,
      })),
    );

    expect(screen.queryByRole("heading", { name: "Pasillo" })).toBeNull();
    expect(screen.getByText("No hay nodos con alertas abiertas.")).toBeTruthy();
  });

  it("al reconectar, el nuevo snapshot reemplaza la lista (no quedan alertas fantasma)", async () => {
    vi.useFakeTimers();
    try {
      await renderWithSnapshot([alert(9, 2), alert(10, 1, "technical")]);
      expect(screen.getByRole("heading", { name: "Pasillo" })).toBeTruthy();

      // Se cae el stream y, mientras, la alerta 9 se atendió y terminó.
      act(() => stream.onError(new Error("red")));
      act(() => vi.advanceTimersByTime(5000));
      sendSnapshot([alert(10, 1, "technical")]);

      expect(screen.queryByRole("heading", { name: "Pasillo" })).toBeNull();
      expect(screen.getByRole("heading", { name: "Entrada" })).toBeTruthy();
    } finally {
      vi.useRealTimers();
    }
  });

  it("atender una alerta llama al servicio y la marca en la tarjeta", async () => {
    alertsService.handle.mockResolvedValue(alert(9, 2, "out_of_range", { handled_by_user_id: 5 }));
    await renderWithSnapshot([alert(9, 2)]);

    fireEvent.click(screen.getByRole("button", { name: "Marcar atendida" }));

    expect(alertsService.handle).toHaveBeenCalledWith(9);
    expect(await screen.findByText("✓ Atendida")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Marcar atendida" })).toBeNull();
  });

  it("si atender falla muestra el error y deja la alerta visible", async () => {
    alertsService.handle.mockRejectedValue(new Error("red"));
    await renderWithSnapshot([alert(9, 2)]);

    fireEvent.click(screen.getByRole("button", { name: "Marcar atendida" }));

    expect(await screen.findByText(/No pudimos marcar la alerta/)).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Pasillo" })).toBeTruthy();
  });

  it("si el stream se cae antes del snapshot, avisa y reintenta", async () => {
    vi.useFakeTimers();
    try {
      render(<NodesPage />);
      await act(async () => {});
      act(() => stream.onError(new Error("503")));

      expect(screen.getByText(/Reintentando/)).toBeTruthy();
      expect(closeStream).toHaveBeenCalled();

      act(() => vi.advanceTimersByTime(5000));
      expect(alertsService.subscribeToAlerts).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it("si cae el stream con datos cargados, muestra el aviso y conserva la lista", async () => {
    await renderWithSnapshot([alert(9, 2)]);

    act(() => stream.onError(new Error("red")));

    expect(screen.getByText(/Sin actualizaciones en vivo/)).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Pasillo" })).toBeTruthy();
  });

  it("si falla la carga de nodos muestra el error y permite reintentar", async () => {
    nodesService.list.mockRejectedValueOnce(new Error("fallo"));
    render(<NodesPage />);
    await act(async () => {});
    sendSnapshot([alert(9, 2)]);

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText("No pudimos cargar los nodos.")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    sendSnapshot([alert(9, 2)]);

    expect(await screen.findByRole("heading", { name: "Pasillo" })).toBeTruthy();
  });

  it("filtra por texto dentro de las alertas", async () => {
    await renderWithSnapshot([alert(9, 2), alert(10, 1, "technical")]);

    fireEvent.change(screen.getByLabelText("Buscar por nombre o código"), { target: { value: "entr" } });

    expect(screen.queryByRole("heading", { name: "Pasillo" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Entrada" })).toBeTruthy();
  });
});
