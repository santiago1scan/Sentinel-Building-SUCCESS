import styles from "./NodeInfo.module.css";

/** Información de un nodo: nombre, código e IP. Sirve en cualquier pantalla que muestre nodos. */
function NodeInfo({ node }) {
  return (
    <article className={styles.node}>
      <h4 className={styles.name}>{node.name}</h4>
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
