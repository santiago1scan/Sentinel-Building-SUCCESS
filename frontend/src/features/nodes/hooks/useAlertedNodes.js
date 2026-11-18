import { useMemo } from "react";
import { deriveNodeStatus } from "../../../shared/ui/atoms/nodes/nodeStatus";
import { useAlertStream } from "./useAlertStream";

/**
 * Estado de alerta de cada nodo, en vivo: `{ [node_id]: "alert" | "warning" }` solo para los nodos que
 * tienen alertas SIN atender (fuera de rango → "alert"; solo avisos técnicos → "warning"). Una alerta ya
 * atendida no pinta el nodo aunque la condición siga.
 */
export function useAlertedNodes() {
  const { alerts, streamDown } = useAlertStream();

  const statusByNode = useMemo(() => {
    const byNode = new Map();
    for (const alert of Object.values(alerts)) {
      if (alert.node_id == null || alert.handled_by_user_id) continue;
      byNode.set(alert.node_id, [...(byNode.get(alert.node_id) ?? []), alert]);
    }
    const result = {};
    for (const [nodeId, openAlerts] of byNode) {
      result[nodeId] = deriveNodeStatus({ isConnected: false, openAlerts });
    }
    return result;
  }, [alerts]);

  return { statusByNode, streamDown };
}
