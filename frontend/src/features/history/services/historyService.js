import { httpClient } from "../../../shared/services/httpClient";

/**
 * Historial de variables por sensor (GET /history).
 * Devuelve filas agregadas por media hora.
 */
export const historyService = {
  /**
   * @param {object} query
   * @param {number} query.sensorId
   * @param {string} query.metricCode  Ej. "temperature_c"
   * @param {string|Date} query.from   Con zona horaria
   * @param {string|Date} query.to     Con zona horaria
   */
  getHalfHourHistory({ sensorId, metricCode, from, to }) {
    return httpClient.get("/history", {
      params: {
        sensor_id: sensorId,
        metric_code: metricCode,
        from: toIsoString(from),
        to: toIsoString(to),
      },
    });
  },
};

function toIsoString(value) {
  return value instanceof Date ? value.toISOString() : value;
}
