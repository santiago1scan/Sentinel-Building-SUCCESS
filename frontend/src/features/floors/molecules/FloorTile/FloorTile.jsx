import { levelLabel } from "../../levels";
import styles from "./FloorTile.module.css";

/**
 * Tarjeta de un piso con sus zonas. Sin `floor` sirve para las zonas que no tienen piso (`title`).
 */
function FloorTile({ floor, title, zones }) {
  const heading = floor ? floor.name : title;
  const levelText = floor ? levelLabel(floor.level) : null;

  return (
    <article className={styles.tile} data-kind={floor?.level === -1 ? "basement" : "floor"}>
      <header className={styles.head}>
        <h3 className={styles.title}>{heading}</h3>
        {levelText && levelText !== heading && <span className={styles.level}>{levelText}</span>}
      </header>

      {zones.length === 0 ? (
        <p className={styles.empty}>Sin zonas</p>
      ) : (
        <ul className={styles.zones} aria-label={`Zonas de ${heading}`}>
          {zones.map((zone) => (
            <li key={zone.zone_id} className={styles.zone}>{zone.name}</li>
          ))}
        </ul>
      )}
    </article>
  );
}

export default FloorTile;
