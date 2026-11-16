import { httpClient } from "./httpClient";

/**
 * Servicio de edificios (/buildings).
 * Vive en shared porque la pantalla de zonas necesita la lista para seleccionar edificio.
 */
export const buildingsService = {
  list({ limit = 100, offset = 0 } = {}) {
    return httpClient.get("/buildings", { params: { limit, offset } });
  },

  getById(buildingId) {
    return httpClient.get(`/buildings/${buildingId}`);
  },

  /** Payload: { name, address } */
  create(payload) {
    return httpClient.post("/buildings", payload);
  },

  update(buildingId, payload) {
    return httpClient.patch(`/buildings/${buildingId}`, payload);
  },

  remove(buildingId) {
    return httpClient.delete(`/buildings/${buildingId}`);
  },

  listZones(buildingId) {
    return httpClient.get(`/buildings/${buildingId}/zones`);
  },
};
