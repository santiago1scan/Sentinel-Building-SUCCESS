import styles from "./Button.module.css";

const VARIANT_CLASS = {
  inline: styles.inline,
  ghost: styles.ghost,
  active: styles.active,
  disabled: styles.disabled,
};

/**
 * Botón genérico con cuatro variantes:
 * - inline: texto con apariencia de enlace, para acciones dentro de un texto o una fila.
 * - ghost: sin relleno y con borde, para acciones secundarias.
 * - active: relleno de color de marca, para la acción principal de la pantalla.
 * - disabled: apagado y sin acción. También desactiva el botón nativo.
 */
function Button({ variant = "ghost", type = "button", className = "", disabled, children, ...rest }) {
  const isDisabled = variant === "disabled" || Boolean(disabled);
  const classes = [styles.button, VARIANT_CLASS[variant] ?? styles.ghost, className].filter(Boolean).join(" ");

  return (
    <button type={type} className={classes} disabled={isDisabled} {...rest}>
      {children}
    </button>
  );
}

export default Button;
