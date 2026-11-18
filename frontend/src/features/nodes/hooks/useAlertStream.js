import { useCallback, useEffect, useState } from "react";
import { alertsService } from "../../../shared/services/alertsService";
import { applyAlert, isVisible } from "../alertState";

const RETRY_MS = 5000;

/**
 * Alertas visibles de todos los nodos, en vivo desde el stream de escucha: primero el estado actual y luego
 * los cambios. Si el stream se cae, se reconecta y recibe el estado de nuevo; el estado nuevo reemplaza la
 * lista, así que una alerta atendida mientras no había conexión no se queda como fantasma.
 *
 * Devuelve `alerts` (por alert_id), `ready` (ya llegó el estado inicial), `streamDown` y `applyUpdate(alert)`
 * para reflejar enseguida una alerta que acabamos de atender.
 */
export function useAlertStream() {
  const [alerts, setAlerts] = useState({});
  const [ready, setReady] = useState(false);
  const [streamDown, setStreamDown] = useState(false);

  useEffect(() => {
    let active = true;
    let stopStream = () => {};
    let retryTimer = null;

    function connect() {
      // El stream manda primero todo el estado y luego alerts_ready: mientras llega se arma una lista nueva.
      let isReady = false;
      const batch = {};

      stopStream();
      stopStream = alertsService.subscribeToAlerts({
        onAlert: (alert) => {
          if (!active) return;
          if (!isReady) {
            if (isVisible(alert)) batch[alert.alert_id] = alert;
            else delete batch[alert.alert_id];
            return;
          }
          setStreamDown(false);
          setAlerts((prev) => applyAlert(prev, alert));
        },
        onReady: () => {
          if (!active) return;
          isReady = true;
          setAlerts({ ...batch });
          setReady(true);
          setStreamDown(false);
        },
        onError: () => {
          if (!active) return;
          setStreamDown(true);
          stopStream();
          clearTimeout(retryTimer);
          retryTimer = setTimeout(() => {
            if (active) connect();
          }, RETRY_MS);
        },
      });
    }

    connect();

    return () => {
      active = false;
      stopStream();
      clearTimeout(retryTimer);
    };
  }, []);

  const applyUpdate = useCallback((alert) => setAlerts((prev) => applyAlert(prev, alert)), []);

  return { alerts, ready, streamDown, applyUpdate };
}
