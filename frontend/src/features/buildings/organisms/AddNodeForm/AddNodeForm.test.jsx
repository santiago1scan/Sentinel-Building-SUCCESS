import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import AddNodeForm from "./AddNodeForm";

const zones = [
  { zone_id: 4, building_id: 1, name: "Recepción", floor: 1 },
  { zone_id: 5, building_id: 1, name: "Bodega", floor: null },
];
const pending = [{ registration_id: "r-1", name: "Sensor entrada", code: "N-77" }];

function renderForm(props = {}) {
  const onSubmit = vi.fn().mockResolvedValue();
  const onCancel = vi.fn();
  render(
    <AddNodeForm
      buildingName="Torre Norte"
      zones={zones}
      pendingRegistrations={pending}
      onSubmit={onSubmit}
      onCancel={onCancel}
      {...props}
    />,
  );
  return { onSubmit, onCancel };
}

describe("AddNodeForm", () => {
  afterEach(() => cleanup());

  it("muestra las zonas con su piso y las solicitudes pendientes", () => {
    renderForm();

    expect(screen.getByRole("option", { name: "Recepción · piso 1" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Bodega" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Sensor entrada · N-77" })).toBeTruthy();
  });

  it("envía la solicitud y la zona como número", async () => {
    const { onSubmit } = renderForm();

    fireEvent.change(screen.getByLabelText("Solicitud de registro"), { target: { value: "r-1" } });
    fireEvent.change(screen.getByLabelText("Zona"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar nodo" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({ registrationId: "r-1", zoneId: 5 }));
  });

  it("no se puede enviar hasta elegir solicitud y zona", () => {
    renderForm();
    expect(screen.getByRole("button", { name: "Agregar nodo" }).disabled).toBe(true);
  });

  it("sin zonas avisa y no permite enviar", () => {
    renderForm({ zones: [] });

    expect(screen.getByText(/aún no tiene zonas/)).toBeTruthy();
    expect(screen.getByLabelText("Zona").disabled).toBe(true);
  });

  it("sin solicitudes pendientes avisa que el nodo debe registrarse", () => {
    renderForm({ pendingRegistrations: [] });
    expect(screen.getByText(/No hay solicitudes de registro pendientes/)).toBeTruthy();
  });

  it("si el guardado falla muestra el error", async () => {
    renderForm({ onSubmit: vi.fn().mockRejectedValue(new Error("red")) });

    fireEvent.change(screen.getByLabelText("Solicitud de registro"), { target: { value: "r-1" } });
    fireEvent.change(screen.getByLabelText("Zona"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar nodo" }));

    expect(await screen.findByText(/No pudimos agregar el nodo/)).toBeTruthy();
  });
});
