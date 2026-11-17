/** Funciones puras que preparan los datos de conectividad de un nodo. */

/** Resumen de conectividad: sesiones, si hay una abierta y el tiempo conectado acumulado. */
export function summarizeConnectivity(logs, now = Date.now()) {
  let connectedMs = 0;
  let open = null;
  for (const log of logs) {
    const start = new Date(log.started_at).getTime();
    const end = log.ended_at ? new Date(log.ended_at).getTime() : now;
    if (Number.isNaN(start)) continue;
    connectedMs += Math.max(0, end - start);
    if (!log.ended_at && (!open || start > open)) open = start;
  }
  return { sessions: logs.length, connected: open !== null, connectedSince: open, connectedMs };
}

/** "2 h 05 min", "15 min", "40 s". */
export function formatDuration(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds} s`;
  const minutes = Math.floor(totalSeconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours} h ${String(minutes % 60).padStart(2, "0")} min`;
  return `${Math.floor(hours / 24)} d ${hours % 24} h`;
}
