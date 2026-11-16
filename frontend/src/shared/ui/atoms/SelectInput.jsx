import styles from "./SelectInput.module.css";

/**
 * Lista desplegable genérica. `options` es una lista de { value, label }.
 */
function SelectInput({ id, label, value, onChange, options, ...rest }) {
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <select
        id={id}
        className={styles.select}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...rest}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default SelectInput;
