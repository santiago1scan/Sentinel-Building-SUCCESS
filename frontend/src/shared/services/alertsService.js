import { httpClient } from "./httpClient";
import { ESCUCHA_URL, subscribeToStream } from "./eventStream";

/** Servicio de alertas (/alerts). Lo usan dashboard y eventos. */
export const alertsService = {
  list({ limit = 100, offset = 0 } = {}) {
    return httpClient.get("/alerts", { params: { limit, offset } });
  },

  listOpen() {
    return httpClient.get("/alerts/open");
  },

  listUnhandled() {
    return httpClient.get("/alerts/unhandled");
  },

  getById(alertId) {
    return httpClient.get(`/alerts/${alertId}`);
  },

  getByEventUuid(eventUuid) {
    return httpClient.get(`/alerts/event-uuid/${eventUuid}`);
  },

  getByReading(readingId) {
    return httpClient.get(`/alerts/reading/${readingId}`);
  },

  getByHandledUser(userId) {
    return httpClient.get(`/alerts/handled-by/${userId}`);
  },

  /**
   * Marca la alerta como atendida en monolito-escucha, para que el stream lo vea.
   * No borra la alerta. Devuelve el estado completo (mismo formato que el evento `alert`).
   */
  handle(alertId) {
    return httpClient.post(`/alerts/${alertId}/handle`, undefined, { baseUrl: ESCUCHA_URL });
  },

  update(alertId, payload) {
    return httpClient.patch(`/alerts/${alertId}`, payload);
  },

  /**
   * Stream en vivo desde monolito-escucha (con token de Firebase).
   * Eventos: `alert` (estado completo; `visible: false` = terminó y fue atendida, la fila sigue en la
   * base de datos), y `alerts_ready` (se envió todo el estado actual al conectarse).
   * Devuelve la función para cerrar la conexión.
   */
  subscribeToAlerts({ onAlert, onReady, onError }) {
    return subscribeToStream("/alerts/stream", {
      baseUrl: ESCUCHA_URL,
      onEvent: (eventName, data) => {
        if (eventName === "alert") onAlert(data);
        else if (eventName === "alerts_ready") onReady?.();
      },
      onError,
    });
  },
};
