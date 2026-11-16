import { useState } from "react";
import TextInput from "../../../../shared/ui/atoms/inputs/TextInput";
import Button from "../../../../shared/ui/atoms/buttons/Button";
import styles from "./BuildingForm.module.css";

const SAVE_ERROR = "No pudimos guardar el edificio. Intenta de nuevo.";

/**
 * Formulario para crear un edificio. No conoce la API: recibe `onSubmit(payload)`,
 * que devuelve una promesa, y muestra el error si la promesa falla.
 */
function BuildingForm({ onSubmit, onCancel, children }) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("El nombre del edificio es obligatorio.");
      return;
    }

    setError("");
    setSaving(true);
    try {
      await onSubmit({ name: trimmedName, address: address.trim() || null });
    } catch (err) {
      // Un error con userMessage trae su propio texto; el resto muestra el mensaje genérico.
      setError(err?.userMessage ?? SAVE_ERROR);
      setSaving(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-labelledby="building-form-title" noValidate>
      <header className={styles.header}>
        <h2 id="building-form-title" className={styles.title}>Datos del edificio</h2>
        <p className={styles.subtitle}>
          Registra el nombre y la dirección. Después podrás agregar sus zonas y nodos.
        </p>
      </header>

      {error && (
        <p role="alert" className={styles.error}>
          <span aria-hidden="true">⚠</span> {error}
        </p>
      )}

      <div className={styles.fields}>
        <TextInput
          id="building-name"
          label="Nombre"
          value={name}
          onChange={setName}
          placeholder="Ej. Torre Norte"
          aria-required="true"
          aria-invalid={Boolean(error) && !name.trim()}
          autoComplete="off"
        />

        <TextInput
          id="building-address"
          label="Dirección (opcional)"
          value={address}
          onChange={setAddress}
          placeholder="Ej. Calle 5 # 10-20"
          autoComplete="off"
        />
      </div>

      {children}

      <footer className={styles.footer}>
        <Button variant="ghost" onClick={onCancel} disabled={saving}>
          Cancelar
        </Button>
        <Button type="submit" variant="active" disabled={saving}>
          {saving ? "Guardando…" : "Guardar edificio"}
        </Button>
      </footer>
    </form>
  );
}

export default BuildingForm;
