import { useState } from "react";
import { floorsService } from "../../services/floorsService";
import Button from "../../../../shared/ui/atoms/buttons/Button";
import FloorBox from "../../molecules/FloorBox/FloorBox";
import FloorCountStepper from "../../molecules/FloorCountStepper/FloorCountStepper";
import BasementQuestion from "../../molecules/BasementQuestion/BasementQuestion";
import {
  createDrafts, floorsOf, hasBasement, levelOf, setFloorCount, setBasement, removeFloor, patchFloor,
  moveFloor, DEFAULT_FLOORS, MIN_FLOORS, MAX_FLOORS,
} from "./floorDrafts";
import styles from "./FloorsForm.module.css";

const SAVE_ERROR = "No pudimos guardar los pisos. Intenta de nuevo.";

/**
 * Pisos de un edificio. Primero se arman como borradores: cuántos pisos, si tiene sótano, el orden
 * arrastrando y el nombre de cada uno. "Guardar pisos" los crea en el backend con su nivel según
 * la posición. Lo guardado queda fijo.
 */
function FloorsForm({ buildingId, buildingName, onSaved }) {
  const [drafts, setDrafts] = useState(() => createDrafts(DEFAULT_FLOORS));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  const locked = drafts.some((d) => d.saved);
  const pending = drafts.filter((d) => !d.saved);
  const floorCount = floorsOf(drafts).length;

  function update(next) {
    setDrafts(next);
    setMessage({ type: "", text: "" });
  }

  async function handleSave() {
    if (pending.length === 0) return;

    setSaving(true);
    setMessage({ type: "", text: "" });
    let current = drafts;
    const savedFloors = [];
    try {
      // En orden de la lista: así los niveles guardados nunca quedan con huecos.
      for (const draft of pending) {
        const level = levelOf(current, draft.key);
        const floor = await floorsService.create({
          building_id: buildingId,
          level,
          name: draft.name.trim() || null,
        });
        savedFloors.push({ floor_id: floor.floor_id, level: floor.level ?? level, name: floor.name ?? draft.name.trim() });
        current = current.map((d) => (d.key === draft.key ? { ...d, saved: true } : d));
        setDrafts(current);
      }
      setMessage({ type: "success", text: "Pisos guardados." });
      onSaved?.(savedFloors);
    } catch {
      setMessage({ type: "error", text: SAVE_ERROR });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        handleSave();
      }}
      aria-labelledby="floors-title"
      noValidate
    >
      <header className={styles.header}>
        <h2 id="floors-title" className={styles.title}>Pisos de {buildingName}</h2>
        <p className={styles.subtitle}>
          Cuenta los pisos y marca si hay sótano. Arrastra los pisos para ordenarlos: el nivel se toma
          de su posición. Se puede reordenar hasta que se guarde el primero.
        </p>
      </header>

      <FloorCountStepper
        label="Número de pisos"
        value={floorCount}
        min={MIN_FLOORS}
        max={MAX_FLOORS}
        disabled={locked || saving}
        onChange={(count) => update(setFloorCount(drafts, count))}
      />

      <BasementQuestion
        value={hasBasement(drafts)}
        disabled={locked || saving}
        onChange={(on) => update(setBasement(drafts, on))}
      />

      <ul className={styles.list} aria-label="Pisos del edificio">
        {drafts.map((draft) => (
          <li key={draft.key}>
            <FloorBox
              draft={draft}
              level={levelOf(drafts, draft.key)}
              draggable={draft.kind === "floor" && !locked && !saving}
              disabled={draft.saved || saving}
              onChange={(patch) => update(patchFloor(drafts, draft.key, patch))}
              onRemove={() => update(removeFloor(drafts, draft.key))}
              onDropFloor={(fromKey) => update(moveFloor(drafts, fromKey, draft.key))}
            />
          </li>
        ))}
      </ul>

      {message.text && (
        <p role={message.type === "error" ? "alert" : "status"} className={styles[message.type]}>
          {message.text}
        </p>
      )}

      <footer className={styles.footer}>
        <Button type="submit" variant="active" disabled={saving || pending.length === 0}>
          {saving ? "Guardando…" : drafts.length > 0 && pending.length === 0 ? "Todo guardado" : "Guardar pisos"}
        </Button>
      </footer>
    </form>
  );
}

export default FloorsForm;
