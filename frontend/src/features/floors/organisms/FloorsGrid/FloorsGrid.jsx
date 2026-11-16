import FloorSection from "../../organisms/FloorSection/FloorSection";
import { levelLabel } from "../../levels";
import styles from "./FloorsGrid.module.css";

/**
 * Pisos del edificio en una grilla. Cada piso es una FloorSection con sus zonas y los nodos de cada zona.
 * Las zonas sin piso van en una sección aparte. Los pisos van del sótano hacia arriba.
 */
function FloorsGrid({ floors, zones, nodesByZone }) {
  const ordered = [...floors].sort((a, b) => a.level - b.level);
  const withoutFloor = zones.filter((zone) => zone.floor_id == null);

  if (ordered.length === 0 && withoutFloor.length === 0) {
    return <p className={styles.empty}>Este edificio aún no tiene pisos.</p>;
  }

  return (
    <ul className={styles.grid} aria-label="Pisos del edificio">
      {ordered.map((floor) => (
        <li key={floor.floor_id}>
          <FloorSection
            title={floor.name}
            levelText={levelLabel(floor.level)}
            zones={zones.filter((zone) => zone.floor_id === floor.floor_id)}
            nodesByZone={nodesByZone}
          />
        </li>
      ))}
      {withoutFloor.length > 0 && (
        <li>
          <FloorSection title="Sin piso" zones={withoutFloor} nodesByZone={nodesByZone} />
        </li>
      )}
    </ul>
  );
}

export default FloorsGrid;
