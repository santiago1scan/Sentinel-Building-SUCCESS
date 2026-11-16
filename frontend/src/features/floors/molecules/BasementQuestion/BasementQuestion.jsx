import Button from "../../../../shared/ui/atoms/buttons/Button";
import styles from "./BasementQuestion.module.css";

/** Pregunta de sí o no: ¿el edificio tiene sótano? `onChange` recibe true o false. */
function BasementQuestion({ value, disabled, onChange }) {
  return (
    <div className={styles.box} role="group" aria-labelledby="basement-question">
      <span id="basement-question" className={styles.question}>¿Tiene sótano?</span>
      <div className={styles.options}>
        <Button
          variant={value ? "active" : "ghost"}
          aria-pressed={value}
          disabled={disabled}
          onClick={() => onChange(true)}
        >
          Sí
        </Button>
        <Button
          variant={value ? "ghost" : "active"}
          aria-pressed={!value}
          disabled={disabled}
          onClick={() => onChange(false)}
        >
          No
        </Button>
      </div>
    </div>
  );
}

export default BasementQuestion;
