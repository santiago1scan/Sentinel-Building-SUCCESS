import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import FloorBox from "./FloorBox";

const floor = { key: "k1", kind: "floor", name: "Oficinas", saved: false };
const basement = { key: "b1", kind: "basement", name: "", saved: false };

describe("FloorBox", () => {
  afterEach(() => cleanup());

  it("muestra el nivel como texto, sin input", () => {
    render(<FloorBox draft={floor} level={2} draggable onChange={() => {}} onRemove={() => {}} onDropFloor={() => {}} />);

    expect(screen.getByRole("heading", { name: "Piso 2" })).toBeTruthy();
    expect(screen.queryByLabelText("Nivel")).toBeNull();
  });

  it("el sótano se muestra como Sótano, con estilo propio y sin botón de quitar", () => {
    const { container } = render(<FloorBox draft={basement} level={-1} draggable={false} onChange={() => {}} onRemove={() => {}} onDropFloor={() => {}} />);

    expect(screen.getByRole("heading", { name: "Sótano" })).toBeTruthy();
    expect(container.querySelector("article").getAttribute("data-kind")).toBe("basement");
    expect(screen.queryByRole("button", { name: "Quitar piso" })).toBeNull();
  });

  it("quitar el nombre y quitar el piso llaman a sus funciones", () => {
    const onChange = vi.fn();
    const onRemove = vi.fn();
    render(<FloorBox draft={floor} level={1} draggable onChange={onChange} onRemove={onRemove} onDropFloor={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Quitar nombre" }));
    expect(onChange).toHaveBeenCalledWith({ name: "" });

    fireEvent.click(screen.getByRole("button", { name: "Quitar piso" }));
    expect(onRemove).toHaveBeenCalled();
  });

  it("al soltar otro piso sobre esta caja avisa su clave", () => {
    const onDropFloor = vi.fn();
    render(<FloorBox draft={floor} level={1} draggable onChange={() => {}} onRemove={() => {}} onDropFloor={onDropFloor} />);

    fireEvent.drop(screen.getByRole("article"), { dataTransfer: { getData: () => "floor:k9" } });
    expect(onDropFloor).toHaveBeenCalledWith("k9");
  });

  it("el sótano no acepta piso soltado encima", () => {
    const onDropFloor = vi.fn();
    render(<FloorBox draft={basement} level={-1} draggable={false} onChange={() => {}} onRemove={() => {}} onDropFloor={onDropFloor} />);

    fireEvent.drop(screen.getByRole("article"), { dataTransfer: { getData: () => "floor:k9" } });
    expect(onDropFloor).not.toHaveBeenCalled();
  });

  it("al arrastrarla manda su clave", () => {
    const setData = vi.fn();
    render(<FloorBox draft={floor} level={1} draggable onChange={() => {}} onRemove={() => {}} onDropFloor={() => {}} />);

    fireEvent.dragStart(screen.getByRole("article"), { dataTransfer: { setData, effectAllowed: "" } });
    expect(setData).toHaveBeenCalledWith("text/plain", "floor:k1");
  });
});
