import { NODE_STATUS } from "../nodeStatus";
import styles from "./NodeCard.module.css";

/** Píldora de estado: ícono + etiqueta, legible sin depender del color. */
export function NodeStatusBadge({ status }) {
  const info = NODE_STATUS[status];
  return (
    <span className={styles.badge}>
      <span aria-hidden="true">{info.icon}</span>
      {info.label}
    </span>
  );
}

/**
 * Tarjeta de un nodo sensor. Su color de fondo y de borde sale del estado,
 * para identificarlo de un vistazo.
 */
function NodeCard({ node, status, openAlerts = [] }) {
  return (
    <article className={styles.card} data-status={status}>
      <header className={styles.header}>
        <h3 className={styles.name}>{node.name}</h3>
        <NodeStatusBadge status={status} />
      </header>

      <dl className={styles.details}>
        <div>
          <dt>Código</dt>
          <dd>{node.code}</dd>
        </div>
        <div>
          <dt>Zona</dt>
          <dd>#{node.zone_id}</dd>
        </div>
        <div>
          <dt>IP</dt>
          <dd>{node.ip_address ?? "Sin IP"}</dd>
        </div>
      </dl>

      {openAlerts.length > 0 && (
        <p className={styles.alerts}>
          <span aria-hidden="true">⚠</span> {openAlerts.length} alerta
          {openAlerts.length === 1 ? "" : "s"} abierta{openAlerts.length === 1 ? "" : "s"}
        </p>
      )}
    </article>
  );
}

export default NodeCard;
