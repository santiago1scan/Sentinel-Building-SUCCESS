import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

vi.mock("../features/login/services/authService", () => ({
  authService: { onSessionChange: vi.fn() },
}));

import { authService } from "../features/login/services/authService";
import ProtectedRoute from "./ProtectedRoute";

/** Simula el estado de sesión que entregaría Firebase. */
function emitSession(user) {
  authService.onSessionChange.mockImplementation((callback) => {
    callback(user);
    return () => {};
  });
}

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={["/nodos"]}>
      <Routes>
        <Route
          path="/nodos"
          element={
            <ProtectedRoute>
              <p>Contenido privado</p>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<p>Pantalla de acceso</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("muestra el contenido cuando hay sesión", () => {
    emitSession({ email: "admin@sentinel.local" });

    renderProtected();

    expect(screen.getByText("Contenido privado")).toBeTruthy();
  });

  it("redirige a /login cuando no hay sesión", () => {
    emitSession(null);

    renderProtected();

    expect(screen.getByText("Pantalla de acceso")).toBeTruthy();
    expect(screen.queryByText("Contenido privado")).toBeNull();
  });

  it("muestra un estado de carga mientras se verifica la sesión", () => {
    authService.onSessionChange.mockImplementation(() => () => {});

    renderProtected();

    expect(screen.getByRole("status").textContent).toContain("Verificando sesión");
    expect(screen.queryByText("Contenido privado")).toBeNull();
  });

  it("cancela la suscripción al desmontarse", () => {
    const unsubscribe = vi.fn();
    authService.onSessionChange.mockImplementation(() => unsubscribe);

    const { unmount } = renderProtected();
    unmount();

    expect(unsubscribe).toHaveBeenCalledTimes(1);
  });
});
