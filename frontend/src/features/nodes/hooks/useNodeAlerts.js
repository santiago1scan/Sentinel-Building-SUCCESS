import { useCallback, useMemo, useState } from "react";
import { alertsService } from "../../../shared/services/alertsService";
import { useAlertStream } from "./useAlertStream";

/**
 * Alertas visibles de UN nodo, en vivo (ver useAlertStream).
 *
 * `handleGroup(group)` atiende todas las alertas pendientes de una categoría (el grupo de groupAlerts).
 */
export function useNodeAlerts(nodeId) {
  const { alerts: all, streamDown, applyUpdate } = useAlertStream();
  const [handling, setHandling] = useState({});
  const [actionError, setActionError] = useState("");

  const alerts = useMemo(
    () => Object.values(all).filter((alert) => String(alert.node_id) === String(nodeId)),
    [all, nodeId],
  );

  const handleGroup = useCallback(async (group) => {
    setActionError("");
    setHandling((prev) => ({ ...prev, [group.key]: true }));
    const results = await Promise.allSettled(group.unhandled.map((alert) => alertsService.handle(alert.alert_id)));
    // Lo que sí se pudo atender se refleja ya; si algo falló, la categoría sigue pendiente.
    results.forEach((result) => {
      if (result.status === "fulfilled") applyUpdate(result.value);
    });
    if (results.some((result) => result.status === "rejected")) {
      setActionError("No pudimos marcar la alerta como atendida. Intenta de nuevo.");
    }
    setHandling((prev) => {
      const next = { ...prev };
      delete next[group.key];
      return next;
    });
  }, [applyUpdate]);

  return { alerts, streamDown, handling, actionError, handleGroup };
}
