import styles from "./BuildingCard.module.css";

/**
 * Tarjeta de un edificio. Muestra nombre y dirección. Los conteos (zonas, nodos) son opcionales:
 * solo aparecen si la pantalla los pasa. `children` permite agregar acciones sin acoplar la tarjeta.
 * Si recibe `onOpen`, toda la tarjeta es clicable (y con teclado); las acciones de `children` no abren
 * la tarjeta.
 */
function BuildingCard({ building, zoneCount, nodeCount, children, onOpen }) {
  const hasCounts = zoneCount !== undefined || nodeCount !== undefined;
  const clickable = typeof onOpen === "function";

  function handleKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(building);
    }
  }

  return (
    <article
      className={clickable ? `${styles.card} ${styles.clickable}` : styles.card}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={clickable ? () => onOpen(building) : undefined}
      onKeyDown={clickable ? handleKeyDown : undefined}
    >
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

      {children && (
        // Las acciones no deben abrir la tarjeta: se corta la propagación de clic y de teclado.
        <div
          className={styles.actions}
          onClick={(event) => event.stopPropagation()}
          onKeyDown={(event) => event.stopPropagation()}
        >
          {children}
        </div>
      )}
    </article>
  );
}

export default BuildingCard;
