import { NODE_STATUS } from "./nodeStatus";
import styles from "./NodeStatusBadge.module.css";

/** Píldora de estado: ícono + etiqueta, legible sin depender del color. */
function NodeStatusBadge({ status }) {
  const info = NODE_STATUS[status];
  return (
    <span className={styles.badge} data-status={status}>
      <span aria-hidden="true">{info.icon}</span>
      {info.label}
    </span>
  );
}

export default NodeStatusBadge;
