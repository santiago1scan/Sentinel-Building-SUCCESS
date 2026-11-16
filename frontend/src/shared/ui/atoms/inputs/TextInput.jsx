import styles from "./TextInput.module.css";

/**
 * Campo de texto genérico: etiqueta visible, control accesible y valor controlado.
 * Cualquier pantalla puede usarlo; no conoce el dominio.
 */
function TextInput({ id, label, value, onChange, type = "text", placeholder, ...rest }) {
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <input
        id={id}
        type={type}
        className={styles.input}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        {...rest}
      />
    </div>
  );
}

export default TextInput;
