import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import BuildingCard from "./BuildingCard";

const building = { building_id: 1, name: "Torre Norte", address: "Calle 5 # 10-20" };

describe("BuildingCard", () => {
  afterEach(() => cleanup());

  it("muestra el nombre y la dirección", () => {
    render(<BuildingCard building={building} />);

    expect(screen.getByRole("heading", { name: "Torre Norte" })).toBeTruthy();
    expect(screen.getByText("Calle 5 # 10-20")).toBeTruthy();
  });

  it("sin dirección muestra 'Sin dirección'", () => {
    render(<BuildingCard building={{ ...building, address: null }} />);
    expect(screen.getByText("Sin dirección")).toBeTruthy();
  });

  it("muestra los conteos solo si se pasan", () => {
    const { rerender } = render(<BuildingCard building={building} />);
    expect(screen.queryByText("Zonas")).toBeNull();

    rerender(<BuildingCard building={building} zoneCount={3} nodeCount={12} />);
    expect(screen.getByText("Zonas")).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
  });

  it("muestra las acciones que recibe", () => {
    const onEdit = vi.fn();
    render(
      <BuildingCard building={building}>
        <button type="button" onClick={onEdit}>Editar</button>
      </BuildingCard>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    expect(onEdit).toHaveBeenCalled();
  });
});
