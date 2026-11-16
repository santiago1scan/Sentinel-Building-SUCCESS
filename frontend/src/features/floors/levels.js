/** Texto que muestra un piso según su nivel: "Sótano" para -1 y "Piso N" para los demás. */
export function levelLabel(level) {
  if (level === -1) return "Sótano";
  return `Piso ${level}`;
}
