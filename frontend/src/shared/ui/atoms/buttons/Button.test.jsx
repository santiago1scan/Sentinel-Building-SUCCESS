import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import Button from "./Button";

describe("Button", () => {
  afterEach(() => cleanup());

  it("es de tipo button por omisión, para no enviar formularios sin querer", () => {
    render(<Button>Guardar</Button>);
    expect(screen.getByRole("button", { name: "Guardar" }).getAttribute("type")).toBe("button");
  });

  it("ejecuta onClick en las variantes activas", () => {
    const onClick = vi.fn();
    render(<Button variant="active" onClick={onClick}>Agregar zona</Button>);

    fireEvent.click(screen.getByRole("button", { name: "Agregar zona" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("la variante disabled no está disponible y no ejecuta onClick", () => {
    const onClick = vi.fn();
    render(<Button variant="disabled" onClick={onClick}>Agregar zona</Button>);

    const button = screen.getByRole("button", { name: "Agregar zona" });
    expect(button.disabled).toBe(true);
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("la prop disabled también desactiva el botón", () => {
    render(<Button variant="active" disabled>Guardar</Button>);
    expect(screen.getByRole("button", { name: "Guardar" }).disabled).toBe(true);
  });

  it("cada variante se renderiza con su propio botón", () => {
    render(
      <>
        <Button variant="inline">Ver</Button>
        <Button variant="ghost">Editar</Button>
        <Button variant="active">Agregar zona</Button>
        <Button variant="disabled">Eliminar</Button>
      </>,
    );
    expect(screen.getAllByRole("button")).toHaveLength(4);
  });
});
