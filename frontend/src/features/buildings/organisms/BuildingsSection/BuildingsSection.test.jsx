import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import BuildingsSection from "./BuildingsSection";
import { buildingsService } from "../../../../shared/services/buildingsService";

vi.mock("../../../../shared/services/buildingsService", () => ({
  buildingsService: { list: vi.fn() },
}));

describe("BuildingsSection", () => {
  afterEach(() => cleanup());

  it("muestra una tarjeta por edificio", async () => {
    buildingsService.list.mockResolvedValue([
      { building_id: 1, name: "Torre Norte", address: "Calle 5" },
      { building_id: 2, name: "Bloque Sur", address: null },
    ]);
    render(<MemoryRouter><BuildingsSection /></MemoryRouter>);

    expect(await screen.findByRole("heading", { name: "Torre Norte" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Bloque Sur" })).toBeTruthy();
  });

  it("el botón Agregar edificio lleva al formulario", async () => {
    buildingsService.list.mockResolvedValue([]);
    render(<MemoryRouter><BuildingsSection /></MemoryRouter>);

    expect(await screen.findByRole("button", { name: "Agregar edificio" })).toBeTruthy();
  });

  it("sin edificios muestra un mensaje", async () => {
    buildingsService.list.mockResolvedValue([]);
    render(<MemoryRouter><BuildingsSection /></MemoryRouter>);

    expect(await screen.findByText("Aún no hay edificios registrados.")).toBeTruthy();
  });

  it("si falla la carga muestra el error", async () => {
    buildingsService.list.mockRejectedValue(new Error("red"));
    render(<MemoryRouter><BuildingsSection /></MemoryRouter>);

    expect(await screen.findByText("No pudimos cargar los edificios.")).toBeTruthy();
  });
});
