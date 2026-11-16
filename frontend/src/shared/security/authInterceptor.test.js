import { describe, it, expect, vi } from "vitest";
import { authRequestInterceptor } from "./authInterceptor";
import { setAuthTokenProvider } from "../services/authToken";
import { ApiError } from "../services/httpClient";

describe("authRequestInterceptor", () => {
  it("no agrega token a rutas públicas", async () => {
    const provider = vi.fn().mockResolvedValue("token-123");
    setAuthTokenProvider(provider);

    const context = { method: "GET", path: "/health", headers: {} };
    const result = await authRequestInterceptor(context);

    expect(result.headers.Authorization).toBeUndefined();
    expect(provider).not.toHaveBeenCalled();
  });

  it("agrega Bearer token a rutas protegidas", async () => {
    setAuthTokenProvider(async () => "token-123");

    const context = { method: "GET", path: "/nodes", headers: { Accept: "application/json" } };
    const result = await authRequestInterceptor(context);

    expect(result.headers.Authorization).toBe("Bearer token-123");
    expect(result.headers.Accept).toBe("application/json");
  });

  it("no modifica el contexto original", async () => {
    setAuthTokenProvider(async () => "token-123");

    const context = { method: "POST", path: "/zones", headers: {} };
    await authRequestInterceptor(context);

    expect(context.headers.Authorization).toBeUndefined();
  });

  it("cancela con 401 cuando no hay sesión y no sale a la red", async () => {
    setAuthTokenProvider(async () => null);

    const context = { method: "GET", path: "/nodes", headers: {} };

    await expect(authRequestInterceptor(context)).rejects.toMatchObject({
      status: 401,
    });
    await expect(authRequestInterceptor(context)).rejects.toBeInstanceOf(ApiError);
  });

  it("trata como protegida una ruta que solo se parece a una pública", async () => {
    setAuthTokenProvider(async () => null);

    const context = { method: "GET", path: "/health/nodes", headers: {} };

    await expect(authRequestInterceptor(context)).rejects.toMatchObject({ status: 401 });
  });
});
