import TextInput from "../../../../shared/ui/atoms/inputs/TextInput";
import Button from "../../../../shared/ui/atoms/buttons/Button";
import styles from "./ZoneRow.module.css";

/**
 * Una zona en el editor: nombre, piso opcional y quitarla. Avisa los cambios con `onChange(patch)`
 * con solo los campos modificados.
 */
function ZoneRow({ zone, onChange, onRemove }) {
  return (
    <div className={styles.row}>
      <TextInput
        id={`zone-name-${zone.key}`}
        label="Nombre de la zona"
        value={zone.name}
        onChange={(name) => onChange({ name })}
        placeholder="Ej. Piso 2 · Oficinas"
        autoComplete="off"
      />
      <TextInput
        id={`zone-floor-${zone.key}`}
        label="Piso (opcional)"
        type="number"
        value={zone.floor}
        onChange={(floor) => onChange({ floor })}
        placeholder="Ej. 2"
      />
      <Button variant="inline" onClick={onRemove}>
        Quitar zona
      </Button>
    </div>
  );
}

export default ZoneRow;
