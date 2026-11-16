import { useState } from "react";
import { zonesService } from "../../../../shared/services/zonesService";
import TextInput from "../../../../shared/ui/atoms/inputs/TextInput";
import Button from "../../../../shared/ui/atoms/buttons/Button";
import styles from "./FloorsForm.module.css";

const SAVE_ERROR = "No pudimos agregar el piso. Intenta de nuevo.";

/**
 * Agrega pisos a un edificio. Cada piso es una zona con su número de piso. Guarda en el backend
 * al agregarlo y lista los pisos agregados en esta sesión.
 */
function FloorsForm({ buildingId, buildingName }) {
  const [floor, setFloor] = useState("");
  const [name, setName] = useState("");
  const [added, setAdded] = useState([]); // { zone_id, floor, name }
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleAdd(event) {
    event.preventDefault();
    const number = Number(floor);
    if (floor.trim() === "" || !Number.isInteger(number)) {
      setError("Escribe un número de piso entero, por ejemplo 0, 1 o 2.");
      return;
    }
    if (added.some((item) => item.floor === number)) {
      setError(`El piso ${number} ya está agregado.`);
      return;
    }

    setError("");
    setSaving(true);
    try {
      const zone = await zonesService.create({
        building_id: buildingId,
        name: name.trim() || `Piso ${number}`,
        floor: number,
      });
      setAdded((prev) =>
        [...prev, { zone_id: zone.zone_id, floor: number, name: zone.name }].sort((a, b) => a.floor - b.floor),
      );
      setFloor("");
      setName("");
    } catch {
      setError(SAVE_ERROR);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={handleAdd} aria-labelledby="floors-title" noValidate>
      <header className={styles.header}>
        <h2 id="floors-title" className={styles.title}>Pisos de {buildingName}</h2>
        <p className={styles.subtitle}>Agrega los pisos del edificio. Cada piso se guarda al agregarlo.</p>
      </header>

      {error && (
        <p role="alert" className={styles.error}>
          <span aria-hidden="true">⚠</span> {error}
        </p>
      )}

      <div className={styles.fields}>
        <TextInput
          id="floor-number"
          label="Número de piso"
          type="number"
          value={floor}
          onChange={setFloor}
          placeholder="Ej. 2"
        />
        <TextInput
          id="floor-name"
          label="Nombre (opcional)"
          value={name}
          onChange={setName}
          placeholder="Ej. Oficinas"
          autoComplete="off"
        />
      </div>

      <div className={styles.actions}>
        <Button type="submit" variant="active" disabled={saving}>
          {saving ? "Agregando…" : "Agregar piso"}
        </Button>
      </div>

      {added.length === 0 ? (
        <p className={styles.empty}>Aún no has agregado pisos. Puedes hacerlo después desde el panel.</p>
      ) : (
        <ul className={styles.list} aria-label="Pisos agregados">
          {added.map((item) => (
            <li key={item.zone_id} className={styles.item}>
              <span className={styles.floorNumber}>Piso {item.floor}</span>
              <span className={styles.floorName}>{item.name}</span>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}

export default FloorsForm;
