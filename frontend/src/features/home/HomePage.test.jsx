import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import HomePage from "./HomePage";

function renderHome() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
}

describe("HomePage (inicio público)", () => {
  afterEach(() => {
    cleanup();
  });

  it("presenta el proyecto con su propuesta de valor", () => {
    renderHome();

    expect(
      screen.getByRole("heading", { name: "Sabe qué pasa en cada piso, en tiempo real." }),
    ).toBeTruthy();
    expect(screen.getByText(/conecta los sensores de cada edificio/)).toBeTruthy();
  });

  it("el encabezado tiene el nombre del proyecto y el botón de inicio de sesión", () => {
    renderHome();

    expect(screen.getByRole("link", { name: "Sentinel Building" })).toBeTruthy();
    expect(
      screen.getByRole("banner").querySelector("a[href='/login']").textContent,
    ).toBe("Iniciar sesión");
  });

  it("el llamado a la acción también lleva al login", () => {
    renderHome();

    const links = screen.getAllByRole("link", { name: "Iniciar sesión" });
    expect(links.length).toBe(2);
    links.forEach((link) => expect(link.getAttribute("href")).toBe("/login"));
  });
});
