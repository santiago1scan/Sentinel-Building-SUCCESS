import styles from "./BuildingCard.module.css";

/**
 * Tarjeta de un edificio. Muestra nombre y dirección. Los conteos (zonas, nodos) son opcionales:
 * solo aparecen si la pantalla los pasa. `children` permite agregar acciones sin acoplar la tarjeta.
 */
function BuildingCard({ building, zoneCount, nodeCount, children }) {
  const hasCounts = zoneCount !== undefined || nodeCount !== undefined;

  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <h3 className={styles.name}>{building.name}</h3>
      </header>

      <p className={styles.address}>{building.address || "Sin dirección"}</p>

      {hasCounts && (
        <dl className={styles.counts}>
          {zoneCount !== undefined && (
            <div>
              <dt>Zonas</dt>
              <dd>{zoneCount}</dd>
            </div>
          )}
          {nodeCount !== undefined && (
            <div>
              <dt>Nodos</dt>
              <dd>{nodeCount}</dd>
            </div>
          )}
        </dl>
      )}

      {children && <div className={styles.actions}>{children}</div>}
    </article>
  );
}

export default BuildingCard;
