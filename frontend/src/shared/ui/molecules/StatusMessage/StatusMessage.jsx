import { MdCheckCircle, MdErrorOutline, MdInfoOutline } from "react-icons/md";
import styles from "./StatusMessage.module.css";

const STATUS = {
  success: { icon: MdCheckCircle, role: "status" },
  error: { icon: MdErrorOutline, role: "alert" },
  info: { icon: MdInfoOutline, role: "status" },
};

/**
 * Mensaje de estado con icono: éxito, error o información. El texto principal es `title`;
 * `children` admite texto de apoyo y acciones (por ejemplo, un botón).
 */
function StatusMessage({ status = "info", title, children }) {
  const { icon: Icon, role } = STATUS[status] ?? STATUS.info;

  return (
    <section className={`${styles.message} ${styles[status] ?? ""}`} role={role}>
      <Icon className={styles.icon} aria-hidden="true" />
      <h2 className={styles.title}>{title}</h2>
      {children && <div className={styles.body}>{children}</div>}
    </section>
  );
}

export default StatusMessage;
