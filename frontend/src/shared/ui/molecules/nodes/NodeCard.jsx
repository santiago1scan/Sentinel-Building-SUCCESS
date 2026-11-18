import NodeStatusBadge from "../../atoms/nodes/NodeStatusBadge";
import NodeAlerts from "./NodeAlerts";
import styles from "./NodeCard.module.css";

/**
 * Tarjeta de un nodo sensor. Su color de fondo y de borde sale del estado, para identificarlo de un
 * vistazo. Muestra UNA alerta por categoría (temperatura, movimiento, energía…) y, debajo, qué sensores
 * están fuera de rango o fallando; se atiende la categoría completa. `alertGroups` sale de groupAlerts.
 */
function NodeCard({ node, status, alertGroups = [], handling = {}, onHandle = () => {} }) {
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

      <NodeAlerts
        groups={alertGroups}
        handling={handling}
        onHandle={onHandle}
        nodeHref={`/panel/nodes/${node.node_id}`}
      />
    </article>
  );
}

export default NodeCard;
