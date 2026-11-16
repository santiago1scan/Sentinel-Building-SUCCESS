import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import FloorsForm from "./FloorsForm";
import { zonesService } from "../../../../shared/services/zonesService";

vi.mock("../../../../shared/services/zonesService", () => ({
  zonesService: { create: vi.fn() },
}));

function fillFloor(value) {
  fireEvent.change(screen.getByLabelText("Número de piso"), { target: { value } });
}

describe("FloorsForm", () => {
  beforeEach(() => {
    zonesService.create.mockImplementation(async ({ floor, name }) => ({
      zone_id: 100 + floor, building_id: 7, floor, name,
    }));
  });

  afterEach(() => cleanup());

  it("agrega un piso al edificio y lo lista", async () => {
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);

    fillFloor("2");
    fireEvent.click(screen.getByRole("button", { name: "Agregar piso" }));

    await waitFor(() => expect(zonesService.create).toHaveBeenCalledWith({ building_id: 7, name: "Piso 2", floor: 2 }));
    const list = await screen.findByRole("list", { name: "Pisos agregados" });
    expect(list.textContent).toContain("Piso 2");
  });

  it("usa el nombre escrito cuando lo hay", async () => {
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);

    fillFloor("0");
    fireEvent.change(screen.getByLabelText("Nombre (opcional)"), { target: { value: " Lobby " } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar piso" }));

    await waitFor(() => expect(zonesService.create).toHaveBeenCalledWith({ building_id: 7, name: "Lobby", floor: 0 }));
  });

  it("no acepta un piso que no sea entero", () => {
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);

    fillFloor("2.5");
    fireEvent.click(screen.getByRole("button", { name: "Agregar piso" }));

    expect(screen.getByRole("alert").textContent).toContain("número de piso entero");
    expect(zonesService.create).not.toHaveBeenCalled();
  });

  it("no agrega dos veces el mismo piso", async () => {
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);

    fillFloor("3");
    fireEvent.click(screen.getByRole("button", { name: "Agregar piso" }));
    await screen.findByRole("list", { name: "Pisos agregados" });

    fillFloor("3");
    fireEvent.click(screen.getByRole("button", { name: "Agregar piso" }));

    expect(await screen.findByText(/El piso 3 ya está agregado/)).toBeTruthy();
    expect(zonesService.create).toHaveBeenCalledTimes(1);
  });

  it("si el backend falla muestra el error", async () => {
    zonesService.create.mockRejectedValue(new Error("red"));
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);

    fillFloor("1");
    fireEvent.click(screen.getByRole("button", { name: "Agregar piso" }));

    expect(await screen.findByText(/No pudimos agregar el piso/)).toBeTruthy();
  });
});
