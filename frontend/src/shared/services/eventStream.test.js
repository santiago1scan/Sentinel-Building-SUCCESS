import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { subscribeToStream } from "./eventStream";
import { setAuthTokenProvider } from "./authToken";
import { registerAuthInterceptor } from "../security/authInterceptor";

/** Crea una respuesta SSE a partir de fragmentos de texto. */
function sseResponse(chunks) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("subscribeToStream", () => {
  let fetchMock;
  let unregisterAuth;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    setAuthTokenProvider(async () => "token-abc");
    // Sin el interceptor registrado, el stream no recibe token (ver shared/security)
    unregisterAuth = registerAuthInterceptor();
  });

  afterEach(() => {
    unregisterAuth();
    vi.unstubAllGlobals();
  });

  it("parsea eventos con datos JSON y omite comentarios keepalive", async () => {
    fetchMock.mockResolvedValue(
      sseResponse([
        ": keepalive\n\n",
        'event: pending\ndata: [{"registration_id":"abc","code":"NODE-001"}]\n\n',
      ]),
    );
    const onEvent = vi.fn();

    subscribeToStream("/registrations/stream", { onEvent });

    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(1));
    expect(onEvent).toHaveBeenCalledWith("pending", [
      { registration_id: "abc", code: "NODE-001" },
    ]);
  });

  it("envía el token en el header Authorization y no en la URL", async () => {
    fetchMock.mockResolvedValue(sseResponse([]));

    subscribeToStream("/registrations/stream", { onEvent: () => {} });

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).not.toContain("access_token");
    expect(init.headers.Authorization).toBe("Bearer token-abc");
    expect(init.headers.Accept).toBe("text/event-stream");
  });

  it("une un evento partido en varios fragmentos", async () => {
    fetchMock.mockResolvedValue(
      sseResponse(['event: pen', 'ding\ndata: {"n":', "1}\n\n"]),
    );
    const onEvent = vi.fn();

    subscribeToStream("/registrations/stream", { onEvent });

    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(1));
    expect(onEvent).toHaveBeenCalledWith("pending", { n: 1 });
  });

  it("entrega texto plano cuando el dato no es JSON", async () => {
    fetchMock.mockResolvedValue(sseResponse(["event: msg\ndata: hola\n\n"]));
    const onEvent = vi.fn();

    subscribeToStream("/x", { onEvent });

    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(1));
    expect(onEvent).toHaveBeenCalledWith("msg", "hola");
  });

  it("llama a onError cuando la respuesta no es correcta", async () => {
    fetchMock.mockResolvedValue(new Response("forbidden", { status: 403 }));
    const onError = vi.fn();

    subscribeToStream("/registrations/stream", { onEvent: () => {}, onError });

    await vi.waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    expect(onError.mock.calls[0][0].message).toBe("Stream HTTP 403");
  });

  it("no llama a onError al cerrar la conexión manualmente", async () => {
    fetchMock.mockImplementation(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init.signal.addEventListener("abort", () => {
            const error = new Error("aborted");
            error.name = "AbortError";
            reject(error);
          });
        }),
    );
    const onError = vi.fn();

    const close = subscribeToStream("/registrations/stream", { onEvent: () => {}, onError });
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    close();

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(onError).not.toHaveBeenCalled();
  });
});
