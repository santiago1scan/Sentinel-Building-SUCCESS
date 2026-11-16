import { Link } from "react-router";
import styles from "./PublicHeader.module.css";

/**
 * Encabezado de las pantallas públicas (inicio y login).
 * action: { to, label } opcional, se muestra como botón a la derecha.
 */
function PublicHeader({ action }) {
  return (
    <header className={styles.header}>
      <Link to="/" className={styles.brand}>
        Sentinel Building
      </Link>

      {action && (
        <Link to={action.to} className={styles.button}>
          {action.label}
        </Link>
      )}
    </header>
  );
}

export default PublicHeader;
