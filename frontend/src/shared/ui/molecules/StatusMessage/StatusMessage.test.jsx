import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import StatusMessage from "./StatusMessage";

describe("StatusMessage", () => {
  afterEach(() => cleanup());

  it("muestra el título y el texto de apoyo", () => {
    render(<StatusMessage status="success" title="Listo">Se guardó todo.</StatusMessage>);

    expect(screen.getByRole("heading", { name: "Listo" })).toBeTruthy();
    expect(screen.getByText("Se guardó todo.")).toBeTruthy();
  });

  it("el éxito se anuncia como estado y el error como alerta", () => {
    const { rerender } = render(<StatusMessage status="success" title="Bien" />);
    expect(screen.getByRole("status")).toBeTruthy();

    rerender(<StatusMessage status="error" title="Mal" />);
    expect(screen.getByRole("alert")).toBeTruthy();
  });

  it("muestra acciones que recibe como hijos", () => {
    render(
      <StatusMessage status="success" title="Listo">
        <button type="button">Volver</button>
      </StatusMessage>,
    );
    expect(screen.getByRole("button", { name: "Volver" })).toBeTruthy();
  });
});
