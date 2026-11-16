import { useState } from "react";
import SelectInput from "../../../../shared/ui/atoms/selects/SelectInput";
import Button from "../../../../shared/ui/atoms/buttons/Button";
import styles from "./AddNodeForm.module.css";

const SAVE_ERROR = "No pudimos agregar el nodo. Intenta de nuevo.";

/**
 * Asigna una solicitud de registro pendiente a una zona del edificio. No llama a la API: recibe
 * `onSubmit({ registrationId, zoneId })`, que devuelve una promesa.
 */
function AddNodeForm({ buildingName, zones, pendingRegistrations, onSubmit, onCancel }) {
  const [registrationId, setRegistrationId] = useState("");
  const [zoneId, setZoneId] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const hasZones = zones.length > 0;
  const hasRequests = pendingRegistrations.length > 0;
  const canSubmit = hasZones && hasRequests && registrationId !== "" && zoneId !== "" && !saving;

  const requestOptions = [
    { value: "", label: "Selecciona una solicitud" },
    ...pendingRegistrations.map((item) => ({
      value: item.registration_id,
      label: `${item.name} · ${item.code}`,
    })),
  ];

  const zoneOptions = [
    { value: "", label: "Selecciona una zona" },
    ...zones.map((zone) => ({
      value: String(zone.zone_id),
      label: zone.floor == null ? zone.name : `${zone.name} · piso ${zone.floor}`,
    })),
  ];

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setError("");
    setSaving(true);
    try {
      await onSubmit({ registrationId, zoneId: Number(zoneId) });
    } catch {
      setError(SAVE_ERROR);
      setSaving(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-labelledby="add-node-title" noValidate>
      <header className={styles.header}>
        <h2 id="add-node-title" className={styles.title}>Agregar nodo</h2>
        <p className={styles.subtitle}>
          Asigna una solicitud de registro pendiente a una zona de {buildingName}.
        </p>
      </header>

      {error && (
        <p role="alert" className={styles.error}>
          <span aria-hidden="true">⚠</span> {error}
        </p>
      )}

      {!hasZones && (
        <p className={styles.notice}>
          Este edificio aún no tiene zonas. Agrega una zona antes de asignarle un nodo.
        </p>
      )}

      {!hasRequests && (
        <p className={styles.notice}>
          No hay solicitudes de registro pendientes. El nodo debe iniciar su registro primero.
        </p>
      )}

      <div className={styles.fields}>
        <SelectInput
          id="node-registration"
          label="Solicitud de registro"
          value={registrationId}
          onChange={setRegistrationId}
          options={requestOptions}
          disabled={!hasRequests}
        />

        <SelectInput
          id="node-zone"
          label="Zona"
          value={zoneId}
          onChange={setZoneId}
          options={zoneOptions}
          disabled={!hasZones}
        />
      </div>

      <footer className={styles.footer}>
        <Button variant="ghost" onClick={onCancel} disabled={saving}>
          Cancelar
        </Button>
        <Button type="submit" variant="active" disabled={!canSubmit}>
          {saving ? "Agregando…" : "Agregar nodo"}
        </Button>
      </footer>
    </form>
  );
}

export default AddNodeForm;
