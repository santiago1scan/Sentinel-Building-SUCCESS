import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../../shared/services/httpClient", () => ({
  httpClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock("../../../shared/services/eventStream", () => ({
  subscribeToStream: vi.fn(),
}));

import { httpClient } from "../../../shared/services/httpClient";
import { subscribeToStream } from "../../../shared/services/eventStream";
import { registrationsService } from "./registrationsService";

describe("registrationsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listPending consulta /registrations/pending", () => {
    registrationsService.listPending();
    expect(httpClient.get).toHaveBeenCalledWith("/registrations/pending");
  });

  it("approve envía zone_id como número en el body", () => {
    registrationsService.approve("reg-1", 3);
    expect(httpClient.post).toHaveBeenCalledWith("/registrations/reg-1/approve", {
      zone_id: 3,
    });
  });

  it("reject hace POST sin body", () => {
    registrationsService.reject("reg-1");
    expect(httpClient.post).toHaveBeenCalledWith("/registrations/reg-1/reject");
  });

  it("subscribePending abre el stream en /registrations/stream", () => {
    const close = vi.fn();
    subscribeToStream.mockReturnValue(close);

    const result = registrationsService.subscribePending({
      onPending: vi.fn(),
      onError: vi.fn(),
    });

    expect(subscribeToStream).toHaveBeenCalledWith(
      "/registrations/stream",
      expect.objectContaining({ onEvent: expect.any(Function) }),
    );
    expect(result).toBe(close);
  });

  it("subscribePending entrega solo los eventos 'pending' a onPending", () => {
    const onPending = vi.fn();
    registrationsService.subscribePending({ onPending, onError: vi.fn() });

    const { onEvent } = subscribeToStream.mock.calls[0][1];
    const lista = [{ registration_id: "r1" }];

    onEvent("pending", lista);
    onEvent("otro-evento", { ignorado: true });

    expect(onPending).toHaveBeenCalledTimes(1);
    expect(onPending).toHaveBeenCalledWith(lista);
  });

  it("subscribePending pasa onError al stream", () => {
    const onError = vi.fn();
    registrationsService.subscribePending({ onPending: vi.fn(), onError });

    expect(subscribeToStream.mock.calls[0][1].onError).toBe(onError);
  });
});
