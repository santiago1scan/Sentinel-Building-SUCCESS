import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import CreateBuildingPage from "./CreateBuildingPage";
import { buildingsService } from "../../shared/services/buildingsService";

vi.mock("../../shared/services/buildingsService", () => ({
  buildingsService: { create: vi.fn() },
}));
vi.mock("../../shared/services/zonesService", () => ({
  zonesService: { create: vi.fn() },
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <CreateBuildingPage />
    </MemoryRouter>,
  );
}

describe("CreateBuildingPage", () => {
  beforeEach(() => {
    buildingsService.create.mockResolvedValue({ building_id: 1 });
  });

  afterEach(() => cleanup());

  it("muestra el formulario de crear edificio y el icono decorativo, sin zonas ni nodos", () => {
    const { container } = renderPage();

    expect(screen.getByRole("heading", { name: "Datos del edificio" })).toBeTruthy();
    expect(container.querySelector("svg")).toBeTruthy();
    expect(screen.queryByText(/Zonas/)).toBeNull();
    expect(screen.queryByText(/Nodo/)).toBeNull();
  });

  it("guardar crea el edificio en el backend y muestra el mensaje de éxito en lugar del formulario", async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Torre Sur" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar edificio" }));

    expect(await screen.findByRole("heading", { name: "Edificio creado exitosamente" })).toBeTruthy();
    expect(buildingsService.create).toHaveBeenCalledWith({ name: "Torre Sur", address: null });
    expect(screen.getByText(/“Torre Sur” ya está registrado/)).toBeTruthy();
    expect(screen.queryByLabelText("Nombre")).toBeNull();
  });

  it("tras guardar, la columna 2 muestra el formulario de pisos del edificio", async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Torre Sur" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar edificio" }));

    expect(await screen.findByRole("heading", { name: "Pisos de Torre Sur" })).toBeTruthy();
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("si el backend falla, el formulario sigue visible con el error", async () => {
    buildingsService.create.mockRejectedValue(new Error("red"));
    renderPage();

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Torre Sur" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar edificio" }));

    expect(await screen.findByText(/No pudimos guardar el edificio/)).toBeTruthy();
    expect(screen.getByLabelText("Nombre")).toBeTruthy();
    expect(screen.queryByText("Edificio creado exitosamente")).toBeNull();
  });
});
