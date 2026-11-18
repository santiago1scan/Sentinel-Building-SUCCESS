import NodeStatusBadge from "../../atoms/nodes/NodeStatusBadge";
import styles from "./NodeInfo.module.css";

/**
 * Información de un nodo: nombre, código e IP. Sirve en cualquier pantalla que muestre nodos.
 * Si `status` es "alert" (alerta fuera de rango) o "warning" (solo avisos técnicos), la tarjeta cambia de
 * color y lo dice con texto, no solo con el color.
 */
function NodeInfo({ node, status = null }) {
  return (
    <article className={styles.node} data-status={status ?? undefined}>
      <header className={styles.header}>
        <h4 className={styles.name}>{node.name}</h4>
        {status && <NodeStatusBadge status={status} />}
      </header>
      <dl className={styles.details}>
        <div>
          <dt>Código</dt>
          <dd>{node.code}</dd>
        </div>
        <div>
          <dt>IP</dt>
          <dd>{node.ip_address ?? "Sin IP"}</dd>
        </div>
      </dl>
    </article>
  );
}

export default NodeInfo;
