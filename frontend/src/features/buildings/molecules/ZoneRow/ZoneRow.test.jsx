import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import ZoneRow from "./ZoneRow";

const zone = { key: "z1", name: "Piso 1", floor: "1" };

describe("ZoneRow", () => {
  afterEach(() => cleanup());

  it("muestra nombre y piso de la zona", () => {
    render(<ZoneRow zone={zone} onChange={() => {}} onRemove={() => {}} />);

    expect(screen.getByLabelText("Nombre de la zona").value).toBe("Piso 1");
    expect(screen.getByLabelText("Piso (opcional)").value).toBe("1");
  });

  it("avisa solo el campo que cambió", () => {
    const onChange = vi.fn();
    render(<ZoneRow zone={zone} onChange={onChange} onRemove={() => {}} />);

    fireEvent.change(screen.getByLabelText("Piso (opcional)"), { target: { value: "3" } });

    expect(onChange).toHaveBeenCalledWith({ floor: "3" });
  });

  it("Quitar zona llama a onRemove", () => {
    const onRemove = vi.fn();
    render(<ZoneRow zone={zone} onChange={() => {}} onRemove={onRemove} />);

    fireEvent.click(screen.getByRole("button", { name: "Quitar zona" }));

    expect(onRemove).toHaveBeenCalled();
  });
});
