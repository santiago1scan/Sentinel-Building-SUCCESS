import styles from "./StatTile.module.css";

/** Un dato destacado: etiqueta pequeña arriba y valor en grande. `hint` es texto de apoyo opcional. */
function StatTile({ label, value, hint }) {
  return (
    <div className={styles.tile}>
      <dt className={styles.label}>{label}</dt>
      <dd className={styles.value}>{value}</dd>
      {hint && <dd className={styles.hint}>{hint}</dd>}
    </div>
  );
}

export default StatTile;
