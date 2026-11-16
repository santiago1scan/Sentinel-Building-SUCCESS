import { ApiError, addRequestInterceptor } from "../services/httpClient";
import { getAuthToken } from "../services/authToken";
import { isPublicRoute } from "./publicRoutes";

/**
 * Interceptor de autenticación.
 *
 * - Rutas de la lista blanca: se envían sin token.
 * - Resto de rutas: se agrega "Authorization: Bearer <ID token de Firebase>".
 * - Si no hay sesión, la solicitud se cancela aquí con 401 y no sale a la red.
 *   Esto evita enviar peticiones sin credenciales.
 */
export async function authRequestInterceptor(context) {
  if (isPublicRoute(context.method, context.path)) {
    return context;
  }

  const token = await getAuthToken();

  if (!token) {
    throw new ApiError(401, {
      error: "UnauthorizedError",
      message: "No hay una sesión activa.",
    });
  }

  return {
    ...context,
    headers: { ...context.headers, Authorization: `Bearer ${token}` },
  };
}

/**
 * Registra el interceptor de autenticación. Llamar una vez al iniciar la app.
 * Devuelve la función para quitarlo.
 */
export function registerAuthInterceptor() {
  return addRequestInterceptor(authRequestInterceptor);
}
