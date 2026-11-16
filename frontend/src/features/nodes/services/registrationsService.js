import { httpClient } from "../../../shared/services/httpClient";
import { subscribeToStream } from "../../../shared/services/eventStream";

/**
 * Solicitudes de registro de nodos (pantalla Nodos).
 * El bridge (el nodo) usa POST /registrations y GET /registrations/{id}; no se usan desde el panel.
 */
export const registrationsService = {
  listPending() {
    return httpClient.get("/registrations/pending");
  },

  /** Aprueba la solicitud en una zona. zoneId debe ser el ID numérico de la zona. */
  approve(registrationId, zoneId) {
    return httpClient.post(`/registrations/${registrationId}/approve`, {
      zone_id: zoneId,
    });
  },

  reject(registrationId) {
    return httpClient.post(`/registrations/${registrationId}/reject`);
  },

  /**
   * Recibe la lista de pendientes en vivo (evento "pending").
   * Devuelve la función para cerrar la conexión.
   */
  subscribePending({ onPending, onError }) {
    return subscribeToStream("/registrations/stream", {
      onEvent: (eventName, data) => {
        if (eventName === "pending") onPending(data);
      },
      onError,
    });
  },
};
