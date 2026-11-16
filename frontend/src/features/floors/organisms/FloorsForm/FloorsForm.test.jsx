import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent, waitFor, within } from "@testing-library/react";
import FloorsForm from "./FloorsForm";
import { floorsService } from "../../services/floorsService";

vi.mock("../../services/floorsService", () => ({
  floorsService: { create: vi.fn() },
}));

const list = () => screen.getByRole("list", { name: "Pisos del edificio" });
const boxes = () => within(list()).getAllByRole("article");
const headings = () => boxes().map((box) => within(box).getByRole("heading").textContent);

describe("FloorsForm", () => {
  beforeEach(() => {
    floorsService.create.mockImplementation(async ({ level, name }) => ({
      floor_id: 100 + level, building_id: 7, level, name: name ?? `Nivel ${level}`,
    }));
  });

  afterEach(() => cleanup());

  it("parte con 2 pisos: Piso 1 y Piso 2, sin sótano", () => {
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);

    expect(headings()).toEqual(["Piso 1", "Piso 2"]);
    expect(screen.getByRole("button", { name: "No" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("marcar Sí agrega el sótano primero, con su propio estilo", () => {
    const { container } = render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);

    fireEvent.click(screen.getByRole("button", { name: "Sí" }));

    expect(headings()).toEqual(["Sótano", "Piso 1", "Piso 2"]);
    expect(container.querySelector('[data-kind="basement"]')).toBeTruthy();
  });

  it("el contador agrega y quita pisos normales, sin tocar el sótano", () => {
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);
    fireEvent.click(screen.getByRole("button", { name: "Sí" }));

    fireEvent.click(screen.getByRole("button", { name: "Agregar un piso" }));
    expect(headings()).toEqual(["Sótano", "Piso 1", "Piso 2", "Piso 3"]);

    fireEvent.click(screen.getByRole("button", { name: "Quitar un piso" }));
    fireEvent.click(screen.getByRole("button", { name: "Quitar un piso" }));
    expect(headings()).toEqual(["Sótano", "Piso 1"]);
  });

  it("arrastrar un piso sobre otro cambia su nivel según la nueva posición", () => {
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);
    const [first, second] = boxes();
    fireEvent.change(within(first).getByLabelText("Nombre (opcional)"), { target: { value: "Lobby" } });

    const payload = {};
    fireEvent.dragStart(second, { dataTransfer: { setData: (_, value) => { payload.value = value; }, effectAllowed: "" } });
    fireEvent.drop(first, { dataTransfer: { getData: () => payload.value } });

    expect(headings()).toEqual(["Piso 1", "Piso 2"]);
    expect(within(boxes()[0]).getByLabelText("Nombre (opcional)").value).toBe("");
    expect(within(boxes()[1]).getByLabelText("Nombre (opcional)").value).toBe("Lobby");
  });

  it("guardar crea cada piso con el nivel de su posición y lo marca como guardado", async () => {
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);
    fireEvent.click(screen.getByRole("button", { name: "Sí" }));
    fireEvent.change(within(boxes()[0]).getByLabelText("Nombre (opcional)"), { target: { value: " Parqueadero " } });

    fireEvent.click(screen.getByRole("button", { name: "Guardar pisos" }));

    await waitFor(() => expect(floorsService.create).toHaveBeenCalledTimes(3));
    expect(floorsService.create).toHaveBeenNthCalledWith(1, { building_id: 7, level: -1, name: "Parqueadero" });
    expect(floorsService.create).toHaveBeenNthCalledWith(2, { building_id: 7, level: 1, name: null });
    expect(floorsService.create).toHaveBeenNthCalledWith(3, { building_id: 7, level: 2, name: null });
    expect(await screen.findByText("Pisos guardados.")).toBeTruthy();
    expect(screen.getAllByText("Guardado")).toHaveLength(3);
  });

  it("una vez guardado un piso no se puede reordenar ni cambiar el contador", async () => {
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);
    fireEvent.click(screen.getByRole("button", { name: "Guardar pisos" }));
    await screen.findByText("Pisos guardados.");

    expect(screen.getByRole("button", { name: "Agregar un piso" }).disabled).toBe(true);
    expect(boxes().every((box) => box.getAttribute("draggable") === "false")).toBe(true);
  });

  it("si falla a mitad, lo guardado queda y el resto sigue pendiente", async () => {
    floorsService.create.mockResolvedValueOnce({ floor_id: 1, level: 1, name: "Piso 1" });
    floorsService.create.mockRejectedValueOnce(new Error("red"));
    render(<FloorsForm buildingId={7} buildingName="Torre Norte" />);

    fireEvent.click(screen.getByRole("button", { name: "Guardar pisos" }));

    expect(await screen.findByText(/No pudimos guardar los pisos/)).toBeTruthy();
    expect(screen.getAllByText("Guardado")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Guardar pisos" }).disabled).toBe(false);
  });
});
