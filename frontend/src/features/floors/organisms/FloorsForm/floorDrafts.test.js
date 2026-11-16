import { describe, it, expect } from "vitest";
import {
  createDrafts, floorsOf, hasBasement, levelOf, levelLabel, setFloorCount, setBasement, removeFloor,
  patchFloor, moveFloor, makeDraft,
} from "./floorDrafts";

const names = (drafts) => drafts.map((d) => d.name);
const levels = (drafts) => drafts.filter((d) => d.kind === "floor" || d.kind === "basement").map((d) => levelOf(drafts, d.key));

describe("floorDrafts", () => {
  it("empieza con 2 pisos normales: nivel 1 y nivel 2", () => {
    const drafts = createDrafts();
    expect(floorsOf(drafts)).toHaveLength(2);
    expect(levels(drafts)).toEqual([1, 2]);
  });

  it("levelLabel: sótano, planta baja y pisos", () => {
    expect(levelLabel(-1)).toBe("Sótano");
    expect(levelLabel(0)).toBe("Piso 0");
    expect(levelLabel(3)).toBe("Piso 3");
  });

  it("setFloorCount agrega o quita pisos normales desde el final", () => {
    expect(floorsOf(setFloorCount(createDrafts(), 4))).toHaveLength(4);
    expect(floorsOf(setFloorCount(createDrafts(4), 2))).toHaveLength(2);
  });

  it("setFloorCount no quita los pisos ya guardados", () => {
    const [first, second] = createDrafts();
    const drafts = [{ ...first, saved: true }, second];
    expect(setFloorCount(drafts, 1).map((d) => d.key)).toEqual([first.key]);
  });

  it("setBasement agrega el sótano primero, con nivel -1", () => {
    const drafts = setBasement(createDrafts(), true);
    expect(drafts[0].kind).toBe("basement");
    expect(levelOf(drafts, drafts[0].key)).toBe(-1);
    expect(levels(drafts)).toEqual([-1, 1, 2]);
  });

  it("quitar el sótano lo elimina, pero no si ya está guardado", () => {
    const withBasement = setBasement(createDrafts(), true);
    expect(hasBasement(setBasement(withBasement, false))).toBe(false);

    const saved = withBasement.map((d) => (d.kind === "basement" ? { ...d, saved: true } : d));
    expect(hasBasement(setBasement(saved, false))).toBe(true);
  });

  it("con sótano, los pisos normales siguen empezando en el nivel 1", () => {
    const drafts = setBasement(createDrafts(), true);
    const floors = floorsOf(drafts);
    expect(levelOf(drafts, floors[0].key)).toBe(1);
    expect(levelOf(drafts, floors[1].key)).toBe(2);
  });

  it("removeFloor quita un piso normal sin guardar, y no quita el sótano ni los guardados", () => {
    const [a, b] = createDrafts();
    expect(removeFloor([a, b], a.key)).toEqual([b]);
    expect(removeFloor([{ ...a, saved: true }, b], a.key)).toHaveLength(2);
    const withBasement = setBasement([a, b], true);
    expect(removeFloor(withBasement, withBasement[0].key)).toHaveLength(3);
  });

  it("patchFloor cambia el nombre del borrador indicado", () => {
    const [a, b] = createDrafts();
    expect(patchFloor([a, b], b.key, { name: "Oficinas" })[1].name).toBe("Oficinas");
  });

  it("moveFloor reordena y el nivel sale de la nueva posición", () => {
    const [a, b, c] = [makeDraft("floor", "A"), makeDraft("floor", "B"), makeDraft("floor", "C")];
    // Llevar C antes de A: C pasa a ser el piso 1.
    const moved = moveFloor([a, b, c], c.key, a.key);
    expect(names(moved)).toEqual(["C", "A", "B"]);
    expect(levels(moved)).toEqual([1, 2, 3]);
  });

  it("moveFloor hacia abajo deja el piso después del destino", () => {
    const [a, b, c] = [makeDraft("floor", "A"), makeDraft("floor", "B"), makeDraft("floor", "C")];
    expect(names(moveFloor([a, b, c], a.key, c.key))).toEqual(["B", "C", "A"]);
  });

  it("el sótano no se mueve y ningún piso pasa por encima de él", () => {
    const drafts = setBasement(createDrafts(), true);
    const [basement, first, second] = drafts;
    const moved = moveFloor(drafts, second.key, first.key);
    expect(moved[0].key).toBe(basement.key);
    expect(moveFloor(drafts, first.key, basement.key)).toBe(drafts);
  });

  it("no reordena si ya hay pisos guardados", () => {
    const [a, b] = createDrafts();
    const drafts = [{ ...a, saved: true }, b];
    expect(moveFloor(drafts, b.key, a.key)).toBe(drafts);
  });
});
