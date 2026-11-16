import Button from "../../../../shared/ui/atoms/buttons/Button";
import styles from "./FloorCountStepper.module.css";

/** Contador con − y +, dentro de su propia caja. `onChange` recibe el nuevo número. */
function FloorCountStepper({ label, value, min, max, onChange, disabled }) {
  return (
    <div className={styles.box} role="group" aria-label={label}>
      <span className={styles.label}>{label}</span>
      <div className={styles.controls}>
        <Button
          variant="ghost"
          aria-label="Quitar un piso"
          onClick={() => onChange(value - 1)}
          disabled={disabled || value <= min}
        >
          −
        </Button>
        <output className={styles.value} aria-live="polite">{value}</output>
        <Button
          variant="ghost"
          aria-label="Agregar un piso"
          onClick={() => onChange(value + 1)}
          disabled={disabled || value >= max}
        >
          +
        </Button>
      </div>
    </div>
  );
}

export default FloorCountStepper;
