import { httpClient } from "./httpClient";

/**
 * Servicio de nodos sensores (/nodes). Lo usan dashboard y nodos.
 *
 * No hay alta directa: los nodos se crean solo al aprobar una solicitud de registro
 * (registrationsService.approve), según REGISTRO_DE_NODOS.md.
 */
export const nodesService = {
  list({ limit = 100, offset = 0 } = {}) {
    return httpClient.get("/nodes", { params: { limit, offset } });
  },

  getById(nodeId) {
    return httpClient.get(`/nodes/${nodeId}`);
  },

  getByCode(code) {
    return httpClient.get(`/nodes/code/${code}`);
  },

  listByZone(zoneId) {
    return httpClient.get(`/nodes/zone/${zoneId}`);
  },

  listSensors(nodeId) {
    return httpClient.get(`/nodes/${nodeId}/sensors`);
  },

  listConnectivityLogs(nodeId) {
    return httpClient.get(`/nodes/${nodeId}/connectivity-logs`);
  },

  listReceivedReadings(nodeId) {
    return httpClient.get(`/nodes/${nodeId}/received-readings`);
  },

  update(nodeId, payload) {
    return httpClient.patch(`/nodes/${nodeId}`, payload);
  },

  remove(nodeId) {
    return httpClient.delete(`/nodes/${nodeId}`);
  },

  revoke(nodeId) {
    return httpClient.post(`/nodes/${nodeId}/revoke`);
  },
};
