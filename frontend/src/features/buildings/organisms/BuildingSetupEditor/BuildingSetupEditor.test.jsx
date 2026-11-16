import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { useState } from "react";
import BuildingSetupEditor from "./BuildingSetupEditor";

function Harness() {
  const [zones, setZones] = useState([]);
  return <BuildingSetupEditor zones={zones} onChange={setZones} />;
}

describe("BuildingSetupEditor", () => {
  afterEach(() => cleanup());

  it("empieza sin zonas y explica que son opcionales", () => {
    render(<Harness />);

    expect(screen.getByText(/Puedes agregarlas después/)).toBeTruthy();
    expect(screen.queryByLabelText("Nombre de la zona")).toBeNull();
  });

  it("+ Agregar zona crea una fila con nombre y piso", () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole("button", { name: "+ Agregar zona" }));

    expect(screen.getByLabelText("Nombre de la zona")).toBeTruthy();
    expect(screen.getByLabelText("Piso (opcional)")).toBeTruthy();
  });

  it("Quitar zona elimina la fila", () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole("button", { name: "+ Agregar zona" }));
    fireEvent.click(screen.getByRole("button", { name: "Quitar zona" }));

    expect(screen.queryByLabelText("Nombre de la zona")).toBeNull();
  });
});
