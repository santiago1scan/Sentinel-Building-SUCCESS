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
const TYPE_LABEL = {
  out_of_range: "Fuera de rango",
  technical: "Aviso técnico",
};

function NodeCard({ node, status, openAlerts = [], handling = {}, onHandle = () => {} }) {
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
          <dd>{node.zone_id == null ? "—" : `#${node.zone_id}`}</dd>
        </div>
        <div>
          <dt>IP</dt>
          <dd>{node.ip_address ?? "Sin IP"}</dd>
        </div>
      </dl>

      {openAlerts.length > 0 && (
        <ul className={styles.alertList} aria-label="Alertas del nodo">
          {openAlerts.map((alert) => {
            const attended = Boolean(alert.handled_by_user_id);
            const busy = Boolean(handling[alert.alert_id]);
            return (
              <li key={alert.alert_id} className={styles.alertItem}>
                <span>
                  <span aria-hidden="true">⚠</span>{" "}
                  {TYPE_LABEL[alert.alert_type] ?? alert.alert_type}
                  <span className={styles.code}> · {alert.alert_code}</span>
                </span>
                {attended ? (
                  <span className={styles.attended}>✓ Atendida</span>
                ) : (
                  <button
                    type="button"
                    className={styles.handleButton}
                    disabled={busy}
                    onClick={() => onHandle(alert.alert_id)}
                  >
                    {busy ? "Guardando…" : "Marcar atendida"}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </article>
  );
}

export default NodeCard;
