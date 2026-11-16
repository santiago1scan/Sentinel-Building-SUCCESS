import { httpClient } from "./httpClient";

/**
 * Lecturas de sensores, más los recursos de sensores y tipos de sensor
 * que están relacionados con ellas. Vive en shared por decisión del proyecto.
 */

export const readingsService = {
  list({ limit = 100, offset = 0 } = {}) {
    return httpClient.get("/readings", { params: { limit, offset } });
  },

  getById(readingId) {
    return httpClient.get(`/readings/${readingId}`);
  },

  listBySensor(sensorId) {
    return httpClient.get(`/readings/sensor/${sensorId}`);
  },

  listByReceivingNode(receivingNodeId) {
    return httpClient.get(`/readings/receiving-node/${receivingNodeId}`);
  },

  listBySequence(sequenceNumber) {
    return httpClient.get(`/readings/sequence/${sequenceNumber}`);
  },
};

export const sensorsService = {
  list({ limit = 100, offset = 0 } = {}) {
    return httpClient.get("/sensors", { params: { limit, offset } });
  },

  getById(sensorId) {
    return httpClient.get(`/sensors/${sensorId}`);
  },

  getByCode(code) {
    return httpClient.get(`/sensors/code/${code}`);
  },

  listByPrimaryNode(primaryNodeId) {
    return httpClient.get(`/sensors/primary-node/${primaryNodeId}`);
  },

  listBySensorType(sensorTypeId) {
    return httpClient.get(`/sensors/sensor-type/${sensorTypeId}`);
  },
};

export const sensorTypesService = {
  list({ limit = 100, offset = 0 } = {}) {
    return httpClient.get("/sensor-types", { params: { limit, offset } });
  },

  getById(sensorTypeId) {
    return httpClient.get(`/sensor-types/${sensorTypeId}`);
  },
};
