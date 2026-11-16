import { describe, it, expect } from "vitest";
import { isPublicRoute, PUBLIC_ROUTES } from "./publicRoutes";

describe("isPublicRoute", () => {
  it("permite las rutas de la lista blanca", () => {
    expect(isPublicRoute("GET", "/")).toBe(true);
    expect(isPublicRoute("GET", "/health")).toBe(true);
  });

  it("compara el método sin distinguir mayúsculas", () => {
    expect(isPublicRoute("get", "/health")).toBe(true);
  });

  it("bloquea el mismo path con otro método", () => {
    expect(isPublicRoute("POST", "/health")).toBe(false);
    expect(isPublicRoute("DELETE", "/")).toBe(false);
  });

  it("no confunde rutas protegidas que empiezan igual", () => {
    expect(isPublicRoute("GET", "/health/nodes")).toBe(false);
    expect(isPublicRoute("GET", "/registrations/pending")).toBe(false);
  });

  it("no incluye las rutas del bridge ni el stream de registros", () => {
    expect(isPublicRoute("POST", "/registrations")).toBe(false);
    expect(isPublicRoute("GET", "/registrations/stream")).toBe(false);
  });

  it("la lista blanca contiene exactamente las rutas esperadas", () => {
    expect(PUBLIC_ROUTES).toEqual([
      { method: "GET", path: "/" },
      { method: "GET", path: "/health" },
    ]);
  });
});
