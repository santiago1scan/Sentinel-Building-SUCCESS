import Button from "../../../../shared/ui/atoms/buttons/Button";
import ZoneRow from "../../molecules/ZoneRow/ZoneRow";
import styles from "./BuildingSetupEditor.module.css";

let keySeq = 0;
const nextKey = () => `zone-draft-${++keySeq}`;

function createZoneDraft() {
  return { key: nextKey(), name: "", floor: "" };
}

/**
 * Editor opcional de zonas para crear un edificio. Es presentacional: recibe las zonas
 * y avisa cada cambio con `onChange`. Los nodos no van aquí: tienen su propia sección.
 */
function BuildingSetupEditor({ zones, onChange }) {
  const patchZone = (key, patch) =>
    onChange(zones.map((zone) => (zone.key === key ? { ...zone, ...patch } : zone)));

  return (
    <section className={styles.section} aria-labelledby="zones-title">
      <header className={styles.header}>
        <h3 id="zones-title" className={styles.title}>
          Zonas <span className={styles.optional}>(opcional)</span>
        </h3>
        <p className={styles.hint}>Las zonas organizan los pisos del edificio. Puedes agregarlas después.</p>
      </header>

      {zones.map((zone) => (
        <ZoneRow
          key={zone.key}
          zone={zone}
          onChange={(patch) => patchZone(zone.key, patch)}
          onRemove={() => onChange(zones.filter((z) => z.key !== zone.key))}
        />
      ))}

      <div>
        <Button variant="ghost" onClick={() => onChange([...zones, createZoneDraft()])}>
          + Agregar zona
        </Button>
      </div>
    </section>
  );
}

export default BuildingSetupEditor;
