import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import BuildingForm from "./BuildingForm";

describe("BuildingForm", () => {
  afterEach(() => cleanup());

  it("envía nombre y dirección sin espacios sobrantes", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<BuildingForm onSubmit={onSubmit} onCancel={() => {}} />);

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "  Torre Norte " } });
    fireEvent.change(screen.getByLabelText("Dirección (opcional)"), { target: { value: " Calle 5 " } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar edificio" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({ name: "Torre Norte", address: "Calle 5" }));
  });

  it("la dirección vacía se envía como null", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<BuildingForm onSubmit={onSubmit} onCancel={() => {}} />);

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Bloque Sur" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar edificio" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({ name: "Bloque Sur", address: null }));
  });

  it("sin nombre no envía y muestra el error", () => {
    const onSubmit = vi.fn();
    render(<BuildingForm onSubmit={onSubmit} onCancel={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Guardar edificio" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toContain("El nombre del edificio es obligatorio.");
  });

  it("si el guardado falla muestra el error y deja el formulario editable", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("red"));
    render(<BuildingForm onSubmit={onSubmit} onCancel={() => {}} />);

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Torre" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar edificio" }));

    expect(await screen.findByText(/No pudimos guardar el edificio/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Guardar edificio" }).disabled).toBe(false);
  });

  it("Cancelar llama a onCancel", () => {
    const onCancel = vi.fn();
    render(<BuildingForm onSubmit={vi.fn()} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onCancel).toHaveBeenCalled();
  });
});
