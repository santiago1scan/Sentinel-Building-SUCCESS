import { httpClient } from "./httpClient";

/** Servicio de zonas (/zones). Lo usan dashboard, zonas y nodos. */
export const zonesService = {
  list({ limit = 100, offset = 0 } = {}) {
    return httpClient.get("/zones", { params: { limit, offset } });
  },

  getById(zoneId) {
    return httpClient.get(`/zones/${zoneId}`);
  },

  listByBuilding(buildingId) {
    return httpClient.get(`/zones/building/${buildingId}`);
  },

  /** Payload: { building_id, name, floor } */
  create(payload) {
    return httpClient.post("/zones", payload);
  },

  update(zoneId, payload) {
    return httpClient.patch(`/zones/${zoneId}`, payload);
  },

  remove(zoneId) {
    return httpClient.delete(`/zones/${zoneId}`);
  },
};
