import TextInput from "../../../../shared/ui/atoms/inputs/TextInput";
import Button from "../../../../shared/ui/atoms/buttons/Button";
import { FLOOR_PREFIX } from "../../dnd";
import { levelLabel } from "../../levels";
import styles from "./FloorBox.module.css";

/**
 * Caja de un piso. El nivel no es un campo: es un texto que dice qué piso es (Sótano, Piso 0, Piso 1...)
 * y cambia al arrastrar la caja. El sótano (kind "basement") se distingue, no se arrastra y no se quita aquí.
 */
function FloorBox({ draft, level, draggable, disabled, onChange, onRemove, onDropFloor }) {
  const isBasement = draft.kind === "basement";

  function handleDragStart(event) {
    event.dataTransfer.setData("text/plain", `${FLOOR_PREFIX}${draft.key}`);
    event.dataTransfer.effectAllowed = "move";
  }

  function handleDrop(event) {
    const data = event.dataTransfer.getData("text/plain");
    if (!isBasement && data.startsWith(FLOOR_PREFIX)) {
      event.preventDefault();
      event.stopPropagation();
      onDropFloor(data.slice(FLOOR_PREFIX.length));
    }
  }

  return (
    <article
      className={styles.box}
      data-kind={draft.kind}
      data-saved={draft.saved ? "true" : "false"}
      draggable={draggable}
      onDragStart={handleDragStart}
      onDragOver={(event) => event.preventDefault()}
      onDrop={handleDrop}
    >
      <header className={styles.head}>
        {draggable && (
          <span className={styles.handle} aria-hidden="true" title="Arrastra para reordenar">⠿</span>
        )}
        <h3 className={styles.level}>{levelLabel(level)}</h3>
        <span className={styles.badge}>{draft.saved ? "Guardado" : isBasement ? "Sótano" : "Nuevo"}</span>
        {!isBasement && (
          <Button variant="inline" onClick={onRemove} disabled={disabled || draft.saved}>
            Quitar piso
          </Button>
        )}
      </header>

      <TextInput
        id={`floor-name-${draft.key}`}
        label="Nombre (opcional)"
        value={draft.name}
        onChange={(name) => onChange({ name })}
        placeholder={isBasement ? "Ej. Parqueadero" : "Ej. Oficinas"}
        autoComplete="off"
        disabled={disabled}
      />

      {draft.name && !disabled && (
        <Button variant="inline" onClick={() => onChange({ name: "" })}>
          Quitar nombre
        </Button>
      )}
    </article>
  );
}

export default FloorBox;
