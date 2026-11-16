import ZoneBox from "../../molecules/ZoneBox/ZoneBox";
import styles from "./FloorSection.module.css";

/**
 * Un piso: su nombre en h2 y, debajo, una grilla con una caja por zona. Cada zona muestra los nodos
 * que tiene. `title` es el nombre del piso; `levelText` ("Piso 1", "Sótano") va debajo si es distinto.
 */
function FloorSection({ title, levelText, zones, nodesByZone }) {
  return (
    <section className={styles.floor} aria-label={title}>
      <header className={styles.header}>
        <h2 className={styles.title}>{title}</h2>
        {levelText && levelText !== title && <span className={styles.level}>{levelText}</span>}
      </header>

      {zones.length === 0 ? (
        <p className={styles.empty}>Sin zonas</p>
      ) : (
        <div className={styles.zones}>
          {zones.map((zone) => (
            <ZoneBox key={zone.zone_id} zone={zone} nodes={nodesByZone[zone.zone_id] ?? []} />
          ))}
        </div>
      )}
    </section>
  );
}

export default FloorSection;
