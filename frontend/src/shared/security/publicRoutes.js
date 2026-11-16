/**
 * Lista blanca: rutas que se llaman SIN token de Firebase.
 *
 * Todo lo que no esté aquí exige token (modelo "denegar por defecto").
 * Las rutas deben coincidir exactamente con el método y la ruta sin query string.
 *
 * Rutas que NO van aquí a propósito:
 * - POST /registrations y GET /registrations/{id}: los usa el bridge (nodo) con
 *   X-Poll-Secret, no el panel.
 * - GET /registrations/stream: requiere token del administrador.
 */
export const PUBLIC_ROUTES = [
  { method: "GET", path: "/" },
  { method: "GET", path: "/health" },
];

export function isPublicRoute(method, path) {
  return PUBLIC_ROUTES.some(
    (route) => route.method === method.toUpperCase() && route.path === path,
  );
}
