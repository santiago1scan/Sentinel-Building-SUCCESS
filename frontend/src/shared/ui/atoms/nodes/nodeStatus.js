/**
 * Estados visuales de un nodo. Cada estado lleva ícono y etiqueta además de color,
 * y `token` apunta a las variables --status-<token>, --status-<token>-bg y --status-<token>-text.
 *
 * `rank` ordena de más a menos urgente: lo que requiere atención aparece primero.
 */
export const NODE_STATUS = {
  alert: { label: "Alerta", icon: "⚠", token: "alert", rank: 0 },
  warning: { label: "Revisar", icon: "▲", token: "warning", rank: 1 },
  connected: { label: "Conectado", icon: "●", token: "connected", rank: 2 },
  off: { label: "Sin conexión", icon: "○", token: "off", rank: 3 },
};

/**
 * Deriva el estado de un nodo.
 * - Alerta fuera de rango abierta → "alert".
 * - Cualquier otra alerta abierta (técnica) → "warning".
 * - Sin alertas y con conexión activa → "connected".
 * - En otro caso → "off".
 *
 * @param {{ isConnected: boolean, openAlerts?: Array<{ alert_type: string }> }} input
 */
export function deriveNodeStatus({ isConnected, openAlerts = [] }) {
  if (openAlerts.some((alert) => alert.alert_type === "out_of_range")) return "alert";
  if (openAlerts.length > 0) return "warning";
  return isConnected ? "connected" : "off";
}
