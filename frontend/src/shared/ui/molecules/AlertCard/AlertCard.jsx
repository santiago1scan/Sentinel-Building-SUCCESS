import { MdErrorOutline, MdInfoOutline, MdWarningAmber } from "react-icons/md";
import styles from "./AlertCard.module.css";

const VARIANT = {
  info: { icon: MdInfoOutline, role: "status" },
  warning: { icon: MdWarningAmber, role: "alert" },
  error: { icon: MdErrorOutline, role: "alert" },
};

/**
 * Alerta genérica: icono, `title`, texto de apoyo (`children`) y acciones (`actions`).
 * `variant`: info, warning o error.
 */
function AlertCard({ variant = "info", title, children, actions }) {
  const { icon: Icon, role } = VARIANT[variant] ?? VARIANT.info;

  return (
    <article className={`${styles.alert} ${styles[variant] ?? ""}`} role={role}>
      <Icon className={styles.icon} aria-hidden="true" />
      <div className={styles.content}>
        <h3 className={styles.title}>{title}</h3>
        {children && <div className={styles.body}>{children}</div>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </article>
  );
}

export default AlertCard;
