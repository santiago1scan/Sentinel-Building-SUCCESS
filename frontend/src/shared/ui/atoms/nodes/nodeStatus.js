/**
 * Estados visuales de un nodo. Cada estado lleva ícono y etiqueta además de color,
 * y `token` apunta a las variables --status-<token>, --status-<token>-bg y --status-<token>-text.
 *
 * `rank` ordena de más a menos urgente: lo que requiere atención aparece primero.
 */
export const NODE_STATUS = {
  alert: { label: "Alerta", icon: "⚠", token: "alert", rank: 0 },
  warning: { label: "Revisar", icon: "▲", token: "warning", rank: 1 },
  // Tiene alertas, pero ya las atendió alguien: la condición puede seguir, pero ya no pide acción.
  attended: { label: "Atendida", icon: "✓", token: "attended", rank: 2 },
  connected: { label: "Conectado", icon: "●", token: "connected", rank: 3 },
  off: { label: "Sin conexión", icon: "○", token: "off", rank: 4 },
};

/**
 * Deriva el estado de un nodo.
 * Solo cuentan las alertas SIN atender: una alerta atendida deja de pintar rojo aunque la condición siga.
 * - Alerta fuera de rango sin atender → "alert".
 * - Cualquier otra alerta sin atender (técnica) → "warning".
 * - Tiene alertas y todas están atendidas → "attended".
 * - Sin alertas y con conexión activa → "connected".
 * - En otro caso → "off".
 *
 * @param {{ isConnected: boolean, openAlerts?: Array<{ alert_type: string, handled_by_user_id?: number|null }> }} input
 */
export function deriveNodeStatus({ isConnected, openAlerts = [] }) {
  const pending = openAlerts.filter((alert) => !alert.handled_by_user_id);
  if (pending.some((alert) => alert.alert_type === "out_of_range")) return "alert";
  if (pending.length > 0) return "warning";
  if (openAlerts.length > 0) return "attended";
  return isConnected ? "connected" : "off";
}
