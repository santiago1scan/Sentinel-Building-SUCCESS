/**
 * Qué alertas se muestran. Misma regla que consulta y escucha: visible mientras no haya terminado O
 * mientras nadie la haya atendido. Los eventos del stream ya traen `visible`; se calcula también aquí para
 * mantener la misma regla.
 */
export function isVisible(alert) {
  return alert.visible ?? !(alert.ended_at && alert.handled_by_user_id);
}

/** Aplica un estado de alerta a la lista: se muestra si es visible, si no se quita (nunca se borra del backend). */
export function applyAlert(alerts, alert) {
  const next = { ...alerts };
  if (isVisible(alert)) next[alert.alert_id] = alert;
  else delete next[alert.alert_id];
  return next;
}
