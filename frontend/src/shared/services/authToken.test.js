import { describe, it, expect } from "vitest";
import { setAuthTokenProvider, getAuthToken } from "./authToken";

describe("authToken", () => {
  it("devuelve null mientras no hay proveedor registrado", async () => {
    await expect(getAuthToken()).resolves.toBeNull();
  });

  it("devuelve el token del proveedor registrado", async () => {
    setAuthTokenProvider(async () => "token-1");
    await expect(getAuthToken()).resolves.toBe("token-1");
  });

  it("vuelve a null si se quita el proveedor", async () => {
    setAuthTokenProvider(async () => "token-1");
    setAuthTokenProvider(null);
    await expect(getAuthToken()).resolves.toBeNull();
  });
});
