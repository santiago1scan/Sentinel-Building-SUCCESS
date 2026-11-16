import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import FloorCountStepper from "./FloorCountStepper";

describe("FloorCountStepper", () => {
  afterEach(() => cleanup());

  it("muestra el valor y avisa el siguiente al pulsar + y −", () => {
    const onChange = vi.fn();
    render(<FloorCountStepper label="Número de pisos" value={2} min={1} max={5} onChange={onChange} />);

    expect(screen.getByText("2")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Agregar un piso" }));
    expect(onChange).toHaveBeenLastCalledWith(3);
    fireEvent.click(screen.getByRole("button", { name: "Quitar un piso" }));
    expect(onChange).toHaveBeenLastCalledWith(1);
  });

  it("no baja del mínimo ni sube del máximo", () => {
    const { rerender } = render(<FloorCountStepper label="Pisos" value={1} min={1} max={5} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Quitar un piso" }).disabled).toBe(true);

    rerender(<FloorCountStepper label="Pisos" value={5} min={1} max={5} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Agregar un piso" }).disabled).toBe(true);
  });
});
