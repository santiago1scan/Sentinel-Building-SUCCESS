import { useEffect, useState } from "react";
import AlertCard from "../../../../shared/ui/molecules/AlertCard/AlertCard";
import Button from "../../../../shared/ui/atoms/buttons/Button";
import { registrationsService } from "../../../nodes/services/registrationsService";
import styles from "./PendingRegistrations.module.css";

/**
 * Solicitudes de registro de nodo pendientes, en vivo, como alertas. Solo se muestran las que piden
 * una zona de este edificio (`zones`); se aprueban en esa zona o se rechazan. `onApproved` avisa
 * para recargar los nodos.
 */
function PendingRegistrations({ zones, onApproved }) {
  const [pending, setPending] = useState([]);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    return registrationsService.subscribePending({
      onPending: setPending,
      onError: () => setError("Se perdió la conexión con las solicitudes."),
    });
  }, []);

  const run = async (id, action) => {
    setBusyId(id);
    setError("");
    try {
      await action();
    } catch {
      setError("No pudimos completar la acción. Intenta de nuevo.");
    } finally {
      setBusyId(null);
    }
  };

  const approve = (item) => {
    return run(item.registration_id, async () => {
      await registrationsService.approve(item.registration_id, item.zone_id);
      setPending((list) => list.filter((p) => p.registration_id !== item.registration_id));
      onApproved?.();
    });
  };

  const reject = (item) =>
    run(item.registration_id, async () => {
      await registrationsService.reject(item.registration_id);
      setPending((list) => list.filter((p) => p.registration_id !== item.registration_id));
    });

  const zoneIds = new Set(zones.map((zone) => zone.zone_id));
  const requests = pending.filter((item) => zoneIds.has(item.zone_id));

  const zoneName = (id) => {
    const zone = zones.find((z) => z.zone_id === id);
    return zone ? `${zone.name} (ID ${id})` : `ID ${id}`;
  };

  if (requests.length === 0 && !error) return null;

  return (
    <section className={styles.list} aria-label="Solicitudes de registro de nodo">
      {error && <AlertCard variant="error" title={error} />}
      {requests.map((item) => {
        const busy = busyId === item.registration_id;
        return (
          <AlertCard
            key={item.registration_id}
            variant="warning"
            title={`Solicitud de registro: ${item.name}`}
            actions={
              <>
                <Button variant="active" disabled={busy} onClick={() => approve(item)}>
                  Aprobar
                </Button>
                <Button variant="ghost" disabled={busy} onClick={() => reject(item)}>
                  Rechazar
                </Button>
              </>
            }
          >
            Código {item.code} · edificio {item.building_code} · zona {zoneName(item.zone_id)}
          </AlertCard>
        );
      })}
    </section>
  );
}

export default PendingRegistrations;
