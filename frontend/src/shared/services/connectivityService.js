import { httpClient } from "./httpClient";

/**
 * Registros de conectividad (/connectivity-logs). Un registro sin ended_at
 * significa que el nodo está conectado en ese momento.
 */
export const connectivityService = {
  listActiveByNode(nodeId) {
    return httpClient.get(`/connectivity-logs/node/${nodeId}/active`);
  },
};
