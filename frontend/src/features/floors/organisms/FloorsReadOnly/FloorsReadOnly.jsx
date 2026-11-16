import FloorCard from "../../molecules/FloorCard/FloorCard";
import styles from "./FloorsReadOnly.module.css";

/** Pisos ya guardados de un edificio, en solo lectura. Van del sótano hacia arriba. */
function FloorsReadOnly({ buildingName, floors, selectedId = null, onSelect }) {
  const ordered = [...floors].sort((a, b) => a.level - b.level);

  return (
    <section className={styles.section} aria-labelledby="floors-readonly-title">
      <header className={styles.header}>
        <h2 id="floors-readonly-title" className={styles.title}>Pisos de {buildingName}</h2>
        <p className={styles.subtitle}>
          {ordered.length === 1 ? "1 piso guardado." : `${ordered.length} pisos guardados.`}
        </p>
      </header>

      <ul className={styles.list} aria-label="Pisos guardados">
        {ordered.map((floor) => (
          <li key={floor.floor_id}>
            <FloorCard
              floor={floor}
              selected={floor.floor_id === selectedId}
              onSelect={onSelect}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

export default FloorsReadOnly;
