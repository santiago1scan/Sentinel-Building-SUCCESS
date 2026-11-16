/**
 * Borradores de pisos: lógica pura, sin React.
 *
 * Cada borrador es { key, kind, name, saved }, con kind "basement" (sótano, siempre nivel -1 y primero
 * de la lista) o "floor" (los pisos normales). El nivel no se guarda: sale de la posición. El primer
 * piso normal es el nivel 1 ("Piso 1"), el siguiente el 2, y así. El nivel 0 no se usa.
 */
import { levelLabel } from "../../levels";

export { levelLabel };

export const DEFAULT_FLOORS = 2;
export const MIN_FLOORS = 1;
export const MAX_FLOORS = 30;

let keySeq = 0;

export function makeDraft(kind = "floor", name = "") {
  keySeq += 1;
  return { key: `floor-${keySeq}`, kind, name, saved: false };
}

export function createDrafts(count = DEFAULT_FLOORS) {
  return Array.from({ length: count }, () => makeDraft("floor"));
}

export function floorsOf(drafts) {
  return drafts.filter((d) => d.kind === "floor");
}

export function hasBasement(drafts) {
  return drafts.some((d) => d.kind === "basement");
}

/** Nivel de un borrador: -1 para el sótano, y para los pisos su posición entre los pisos normales, desde 1. */
export function levelOf(drafts, key) {
  const draft = drafts.find((d) => d.key === key);
  if (!draft) return null;
  if (draft.kind === "basement") return -1;
  return floorsOf(drafts).indexOf(draft) + 1;
}


/** Ajusta la cantidad de pisos normales. Agrega al final, o quita desde el final (sin tocar los guardados). */
export function setFloorCount(drafts, count) {
  let next = drafts;
  const current = floorsOf(next).length;
  if (count > current) {
    next = [...next, ...Array.from({ length: count - current }, () => makeDraft("floor"))];
  } else {
    let toRemove = current - count;
    for (let i = next.length - 1; i >= 0 && toRemove > 0; i -= 1) {
      if (next[i].kind === "floor" && !next[i].saved) {
        next = next.filter((_, j) => j !== i);
        toRemove -= 1;
      }
    }
  }
  return next;
}

/** Activa o quita el sótano. Va siempre primero. Un sótano ya guardado no se quita. */
export function setBasement(drafts, on) {
  const existing = drafts.find((d) => d.kind === "basement");
  if (on && !existing) return [makeDraft("basement"), ...drafts];
  if (!on && existing && !existing.saved) return drafts.filter((d) => d.key !== existing.key);
  return drafts;
}

/** Quita un piso normal que todavía no está guardado. */
export function removeFloor(drafts, key) {
  return drafts.filter((d) => !(d.key === key && d.kind === "floor" && !d.saved));
}

export function patchFloor(drafts, key, patch) {
  return drafts.map((d) => (d.key === key ? { ...d, ...patch } : d));
}

/**
 * Mueve el piso `fromKey` a la posición de `toKey`. Solo se reordenan pisos normales, y solo mientras
 * ninguno está guardado: así los niveles de la base de datos nunca quedan desordenados.
 */
export function moveFloor(drafts, fromKey, toKey) {
  if (fromKey === toKey || drafts.some((d) => d.saved)) return drafts;
  const from = drafts.find((d) => d.key === fromKey);
  const to = drafts.find((d) => d.key === toKey);
  if (!from || !to || from.kind !== "floor" || to.kind !== "floor") return drafts;

  const floors = floorsOf(drafts);
  const order = floors.filter((d) => d.key !== fromKey);
  order.splice(order.findIndex((d) => d.key === toKey), 0, from);
  // Ajuste: al bajar un piso, insertarlo en la posición del destino lo deja después de él.
  if (floors.indexOf(from) < floors.indexOf(to)) {
    order.splice(order.findIndex((d) => d.key === from.key), 1);
    order.splice(order.findIndex((d) => d.key === toKey) + 1, 0, from);
  }

  let index = 0;
  return drafts.map((d) => (d.kind === "floor" ? order[index++] : d));
}
