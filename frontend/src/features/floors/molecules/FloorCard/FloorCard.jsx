import { levelLabel } from "../../levels";
import styles from "./FloorCard.module.css";

/**
 * Tarjeta de un piso guardado. Solo lectura: no se arrastra ni se edita. Si recibe `onSelect`,
 * se puede elegir (clic o Enter/Espacio) y `selected` marca el piso elegido.
 */
function FloorCard({ floor, selected = false, onSelect }) {
  const interactive = typeof onSelect === "function";

  function handleKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(floor);
    }
  }

  return (
    <article
      className={styles.card}
      data-kind={floor.level === -1 ? "basement" : "floor"}
      data-selected={selected ? "true" : "false"}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-pressed={interactive ? selected : undefined}
      onClick={interactive ? () => onSelect(floor) : undefined}
      onKeyDown={interactive ? handleKeyDown : undefined}
    >
      <header className={styles.head}>
        <h3 className={styles.level}>{levelLabel(floor.level)}</h3>
        <span className={styles.badge}>Guardado</span>
      </header>
      <p className={floor.name ? styles.name : styles.noName}>{floor.name || "Sin nombre"}</p>
    </article>
  );
}

export default FloorCard;
