import { useEffect, useMemo, useState } from "react";
import { nodesService } from "../../../shared/services/nodesService";
import { sensorTypesService } from "../../../shared/services/readingsService";
import { ApiError } from "../../../shared/services/httpClient";
import { summarizeConnectivity } from "../nodeMetrics";

/**
 * Carga todo lo de un nodo (datos, sensores, conexión, lecturas y tipos de sensor) y lo deja listo
 * para mostrar. `status`: loading | ready | notfound | error.
 */
export function useNodeDetail(nodeId) {
  const [state, setState] = useState({ status: "loading" });
  const [now] = useState(() => Date.now());

  useEffect(() => {
    let active = true;
    Promise.all([
      nodesService.getById(nodeId),
      nodesService.listSensors(nodeId),
      nodesService.listConnectivityLogs(nodeId),
      nodesService.listReceivedReadings(nodeId),
      sensorTypesService.list(),
    ])
      .then(([node, sensors, logs, readings, sensorTypes]) => {
        if (active) setState({ status: "ready", nodeId, node, sensors, logs, readings, sensorTypes });
      })
      .catch((error) => {
        if (active) setState({ status: error instanceof ApiError && error.status === 404 ? "notfound" : "error" });
      });
    return () => {
      active = false;
    };
  }, [nodeId]);

  return useMemo(() => {
    // Mientras llega el nodo nuevo tras cambiar de ruta, no se muestran los datos del anterior.
    if (state.status === "ready" && state.nodeId !== nodeId) return { status: "loading" };
    if (state.status !== "ready") return { status: state.status };
    return {
      ...state,
      now,
      connectivity: summarizeConnectivity(state.logs, now),
    };
  }, [state, nodeId, now]);
}
