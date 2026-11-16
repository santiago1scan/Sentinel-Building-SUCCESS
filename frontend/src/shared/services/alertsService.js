import { httpClient } from "./httpClient";

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

  /** El backend toma el usuario que atiende desde el token; no requiere body. */
  handle(alertId) {
    return httpClient.post(`/alerts/${alertId}/handle`);
  },

  update(alertId, payload) {
    return httpClient.patch(`/alerts/${alertId}`, payload);
  },
};
