import { httpClient } from "../../../shared/services/httpClient";

/**
 * Servicio de pisos (/floors). Un piso pertenece a un edificio y tiene un número de nivel:
 * -1 sótano, 0 planta baja, 1 primero...
 */
export const floorsService = {
  listByBuilding(buildingId) {
    return httpClient.get(`/floors/building/${buildingId}`);
  },

  /** Payload: { building_id, level, name? }. Sin nombre, el backend lo genera. */
  create(payload) {
    return httpClient.post("/floors", payload);
  },
};
