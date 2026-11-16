import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

vi.mock("../../features/login/services/authService", () => ({
  authService: { signInWithGoogle: vi.fn() },
}));

import { authService } from "../../features/login/services/authService";
import LoginPage from "./LoginPage";

const BUTTON = "Continuar con Google";

function renderLogin(initialEntry = "/login") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/" element={<p>Inicio de prueba</p>} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/panel" element={<p>Panel de prueba</p>} />
        <Route path="/eventos" element={<p>Eventos de prueba</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("muestra el título de acceso y el enlace para volver al inicio", () => {
    renderLogin();

    expect(screen.getByRole("heading", { name: "Iniciar sesión" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Volver al inicio" })).toBeTruthy();
  });

  it("ofrece el botón para continuar con Google", () => {
    renderLogin();

    expect(screen.getByRole("button", { name: BUTTON })).toBeTruthy();
  });

  it("llama a signInWithGoogle al pulsar el botón", async () => {
    authService.signInWithGoogle.mockResolvedValue({ email: "admin@sentinel.local" });
    renderLogin();

    fireEvent.click(screen.getByRole("button", { name: BUTTON }));

    await waitFor(() => expect(authService.signInWithGoogle).toHaveBeenCalledTimes(1));
  });

  it("entra al panel por defecto después de iniciar sesión", async () => {
    authService.signInWithGoogle.mockResolvedValue({});
    renderLogin("/login");

    fireEvent.click(screen.getByRole("button", { name: BUTTON }));

    expect(await screen.findByText("Panel de prueba")).toBeTruthy();
  });

  it("vuelve a la ruta que pidió el usuario antes de entrar", async () => {
    authService.signInWithGoogle.mockResolvedValue({});
    render(
      <MemoryRouter initialEntries={[{ pathname: "/login", state: { from: "/eventos" } }]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/eventos" element={<p>Eventos de prueba</p>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: BUTTON }));

    expect(await screen.findByText("Eventos de prueba")).toBeTruthy();
  });

  it("muestra el mensaje de permisos cuando la cuenta no es administradora", async () => {
    authService.signInWithGoogle.mockRejectedValue(
      new Error("Tu cuenta no tiene permisos de administrador en el panel."),
    );
    renderLogin();

    fireEvent.click(screen.getByRole("button", { name: BUTTON }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "Tu cuenta no tiene permisos de administrador en el panel.",
    );
  });

  it("explica cuando el usuario cierra la ventana de Google", async () => {
    authService.signInWithGoogle.mockRejectedValue(
      Object.assign(new Error("closed"), { code: "auth/popup-closed-by-user" }),
    );
    renderLogin();

    fireEvent.click(screen.getByRole("button", { name: BUTTON }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "Cerraste la ventana de Google antes de terminar.",
    );
  });

  it("usa un mensaje genérico para errores desconocidos y vuelve a habilitar el botón", async () => {
    authService.signInWithGoogle.mockRejectedValue(new Error("raro"));
    renderLogin();

    fireEvent.click(screen.getByRole("button", { name: BUTTON }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "No pudimos iniciar sesión. Intenta de nuevo.",
    );
    expect(screen.getByRole("button", { name: BUTTON }).disabled).toBe(false);
  });
});
