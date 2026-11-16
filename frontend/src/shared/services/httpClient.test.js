import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  request,
  httpClient,
  ApiError,
  BASE_URL,
  addRequestInterceptor,
} from "./httpClient";

function jsonResponse(status, body) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("httpClient", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("construye la URL con la base y omite los params vacíos", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, []));

    await request("/alerts", {
      params: { limit: 10, offset: 0, empty: "", missing: undefined, nothing: null },
    });

    const calledUrl = new URL(fetchMock.mock.calls[0][0]);
    expect(calledUrl.origin).toBe(new URL(BASE_URL).origin);
    expect(calledUrl.pathname).toBe("/alerts");
    expect(calledUrl.searchParams.get("limit")).toBe("10");
    expect(calledUrl.searchParams.get("offset")).toBe("0");
    expect(calledUrl.searchParams.has("empty")).toBe(false);
    expect(calledUrl.searchParams.has("missing")).toBe(false);
    expect(calledUrl.searchParams.has("nothing")).toBe(false);
  });

  it("envía el body como JSON con Content-Type", async () => {
    fetchMock.mockResolvedValue(jsonResponse(201, { id: 1 }));

    const result = await httpClient.post("/zones", { name: "Piso 1", floor: 1 });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body)).toEqual({ name: "Piso 1", floor: 1 });
    expect(result).toEqual({ id: 1 });
  });

  it("no envía Content-Type ni body en un GET", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, {}));

    await httpClient.get("/nodes");

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["Content-Type"]).toBeUndefined();
    expect(init.body).toBeUndefined();
  });

  it("devuelve null en un 204 sin cuerpo", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    const result = await httpClient.delete("/zones/1");

    expect(result).toBeNull();
  });

  it("convierte una respuesta de error en ApiError con los datos del backend", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(409, {
        status: 409,
        error: "ConflictError",
        message: "Ya existe un nodo con código NODE-001",
        path: "/registrations",
        request_id: "a1b2c3d4",
      }),
    );

    const error = await httpClient.post("/registrations", {}).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(409);
    expect(error.error).toBe("ConflictError");
    expect(error.message).toBe("Ya existe un nodo con código NODE-001");
    expect(error.requestId).toBe("a1b2c3d4");
  });

  it("usa un mensaje genérico cuando el error no trae JSON", async () => {
    fetchMock.mockResolvedValue(new Response("<html>502</html>", { status: 502 }));

    const error = await httpClient.get("/nodes").catch((e) => e);

    expect(error.status).toBe(502);
    expect(error.message).toBe("Error HTTP 502");
    expect(error.error).toBe("HTTPException");
    expect(error.requestId).toBeNull();
  });

  it("ejecuta los interceptores registrados antes de llamar a fetch", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, {}));
    const remove = addRequestInterceptor((context) => ({
      ...context,
      headers: { ...context.headers, "X-Test": "yes" },
    }));

    try {
      await httpClient.get("/nodes");
      expect(fetchMock.mock.calls[0][1].headers["X-Test"]).toBe("yes");
    } finally {
      remove();
    }
  });

  it("no envía la solicitud si un interceptor lanza error", async () => {
    const remove = addRequestInterceptor(() => {
      throw new ApiError(401, { message: "sin sesión" });
    });

    try {
      await expect(httpClient.get("/nodes")).rejects.toMatchObject({ status: 401 });
      expect(fetchMock).not.toHaveBeenCalled();
    } finally {
      remove();
    }
  });

  it("deja de aplicar un interceptor después de quitarlo", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, {}));
    const remove = addRequestInterceptor((context) => ({
      ...context,
      headers: { ...context.headers, "X-Temp": "1" },
    }));
    remove();

    await httpClient.get("/nodes");

    expect(fetchMock.mock.calls[0][1].headers["X-Temp"]).toBeUndefined();
  });
});
