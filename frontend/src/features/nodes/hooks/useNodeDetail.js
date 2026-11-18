import { useEffect, useMemo, useState } from "react";
import { nodesService } from "../../../shared/services/nodesService";
import { sensorTypesService } from "../../../shared/services/readingsService";
import { ApiError } from "../../../shared/services/httpClient";
import { summarizeConnectivity } from "../nodeMetrics";

/** Cada cuánto se vuelve a pedir lo del nodo. Los bridges envían un resumen cada 30 s en la simulación. */
export const REFRESH_MS = 15_000;

/**
 * Carga todo lo de un nodo (datos, sensores, conexión, lecturas y tipos de sensor) y lo deja listo
 * para mostrar. `status`: loading | ready | notfound | error.
 *
 * Una vez cargado se actualiza solo cada REFRESH_MS, en silencio (sin volver a "cargando" ni
 * parpadear). No pregunta mientras la pestaña está oculta y, al volver a verla, actualiza de
 * inmediato. Si un refresco falla conserva lo que ya mostraba; solo la primera carga muestra error.
 */
export function useNodeDetail(nodeId) {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    let active = true;
    let timer = null;

    // Devuelve true si cargó. `silent` = refresco: un fallo no reemplaza lo que ya se ve.
    async function load(silent) {
      try {
        const [node, sensors, logs, readings, sensorTypes] = await Promise.all([
          nodesService.getById(nodeId),
          nodesService.listSensors(nodeId),
          nodesService.listConnectivityLogs(nodeId),
          nodesService.listReceivedReadings(nodeId),
          sensorTypesService.list(),
        ]);
        if (active) setState({ status: "ready", nodeId, node, sensors, logs, readings, sensorTypes, now: Date.now() });
        return true;
      } catch (error) {
        if (active && !silent) {
          setState({ status: error instanceof ApiError && error.status === 404 ? "notfound" : "error" });
        }
        return false;
      }
    }

    function scheduleRefresh() {
      timer = setTimeout(async () => {
        if (!document.hidden) await load(true);
        if (active) scheduleRefresh();
      }, REFRESH_MS);
    }

    function onVisibilityChange() {
      if (!document.hidden && active) load(true);
    }

    load(false).then((loaded) => {
      if (active && loaded) scheduleRefresh();
    });
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      active = false;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [nodeId]);

  return useMemo(() => {
    // Mientras llega el nodo nuevo tras cambiar de ruta, no se muestran los datos del anterior.
    if (state.status === "ready" && state.nodeId !== nodeId) return { status: "loading" };
    if (state.status !== "ready") return { status: state.status };
    return {
      ...state,
      connectivity: summarizeConnectivity(state.logs, state.now),
    };
  }, [state, nodeId]);
}
