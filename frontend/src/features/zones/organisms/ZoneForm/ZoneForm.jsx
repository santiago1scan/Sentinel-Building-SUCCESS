import { useEffect, useState } from "react";
import { zonesService } from "../../../../shared/services/zonesService";
import TextInput from "../../../../shared/ui/atoms/inputs/TextInput";
import Button from "../../../../shared/ui/atoms/buttons/Button";
import styles from "./ZoneForm.module.css";

const SAVE_ERROR = "No pudimos crear la zona. Intenta de nuevo.";

/**
 * Crear zonas dentro de un piso. Cada zona se guarda en el backend con el piso elegido. Las zonas
 * creadas en esta sesión se listan debajo.
 */
/**
 * `floor` trae el nombre y el nivel del piso elegido. El nombre va en grande; la etiqueta del nivel
 * ("Piso 1", "Sótano") va debajo solo si es distinta del nombre.
 */
function ZoneForm({ buildingId, floor, floorLabel, onSaveProgress }) {
  const [name, setName] = useState("");
  const [zones, setZones] = useState([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // Al abrir el piso se cargan las zonas que ya están guardadas en él (de esta sesión o de antes).
  // El backend no filtra por piso: se piden las del edificio y se quedan las de este piso.
  useEffect(() => {
    let active = true;
    zonesService
      .listByBuilding(buildingId)
      .then((all) => {
        if (active) setZones(all.filter((zone) => zone.floor_id === floor.floor_id));
      })
      .catch(() => {
        if (active) setError("No pudimos cargar las zonas de este piso.");
      });
    return () => {
      active = false;
    };
  }, [buildingId, floor.floor_id]);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Escribe el nombre de la zona.");
      return;
    }

    setError("");
    setSaving(true);
    try {
      const zone = await zonesService.create({
        building_id: buildingId,
        name: trimmed,
        floor_id: floor.floor_id,
      });
      setZones((prev) => [...prev, zone]);
      setName("");
    } catch {
      setError(SAVE_ERROR);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-labelledby="zone-form-title" noValidate>
      <div className={styles.body}>
      <header className={styles.header}>
        <h2 id="zone-form-title" className={styles.title}>{floor.name}</h2>
        {floor.name !== floorLabel && <p className={styles.level}>{floorLabel}</p>}
        <p className={styles.subtitle}>Escribe el nombre de cada zona y pulsa Agregar zona.</p>
      </header>

      {error && (
        <p role="alert" className={styles.error}>
          <span aria-hidden="true">⚠</span> {error}
        </p>
      )}

      <div className={styles.fields}>
        <TextInput
          id="zone-name"
          label="Nombre de la zona"
          value={name}
          onChange={setName}
          placeholder="Ej. Recepción"
          autoComplete="off"
          disabled={saving}
        />
      </div>

      <div className={styles.actions}>
        <Button type="submit" variant="active" disabled={saving}>
          {saving ? "Agregando…" : "Agregar zona"}
        </Button>
      </div>

      {zones.length === 0 ? (
        <p className={styles.empty}>Aún no hay zonas en este piso.</p>
      ) : (
        <ul className={styles.list} aria-label="Zonas creadas">
          {zones.map((zone) => (
            <li key={zone.zone_id} className={styles.item}>
              {zone.name}
            </li>
          ))}
        </ul>
      )}
      </div>

      <footer className={styles.footer}>
        <Button type="button" variant="ghost" onClick={onSaveProgress} disabled={saving}>
          Guardar progreso
        </Button>
      </footer>
    </form>
  );
}

export default ZoneForm;
