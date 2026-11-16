const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8089";

/**
 * Error devuelto por la API. Coincide con el formato estándar del backend:
 * { status, error, message, path, request_id }
 */
export class ApiError extends Error {
  constructor(status, body) {
    super(body?.message ?? `Error HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.error = body?.error ?? "HTTPException";
    this.requestId = body?.request_id ?? null;
  }
}

/* ------------------------------------------------------------------ */
/* Interceptores de solicitud                                           */
/* ------------------------------------------------------------------ */

/**
 * Cada interceptor recibe { method, path, headers } y devuelve el contexto
 * modificado (o lanza un error para cancelar la solicitud).
 * Se ejecutan en orden de registro.
 */
const requestInterceptors = [];

/** Registra un interceptor. Devuelve la función para quitarlo. */
export function addRequestInterceptor(interceptor) {
  requestInterceptors.push(interceptor);
  return () => {
    const index = requestInterceptors.indexOf(interceptor);
    if (index !== -1) requestInterceptors.splice(index, 1);
  };
}

/**
 * Aplica todos los interceptores. También lo usa eventStream, para que las
 * conexiones SSE pasen por la misma capa de seguridad.
 */
export async function runRequestInterceptors(context) {
  let current = context;
  for (const interceptor of requestInterceptors) {
    current = (await interceptor(current)) ?? current;
  }
  return current;
}

/* ------------------------------------------------------------------ */

function buildUrl(path, params) {
  const url = new URL(path, BASE_URL);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }

  return url.toString();
}

/**
 * Cliente HTTP base. Todas las solicitudes pasan por los interceptores
 * registrados (por ejemplo, la inyección del token de Firebase).
 *
 * @param {string} path      Ruta relativa, ej. "/nodes"
 * @param {object} options
 * @param {string} [options.method="GET"]
 * @param {object} [options.params]   Query params; se omiten los vacíos
 * @param {object} [options.body]     Se envía como JSON
 * @param {AbortSignal} [options.signal]
 */
export async function request(path, { method = "GET", params, body, signal } = {}) {
  const baseHeaders = { Accept: "application/json" };
  if (body !== undefined) {
    baseHeaders["Content-Type"] = "application/json";
  }

  const context = await runRequestInterceptors({
    method,
    path,
    headers: baseHeaders,
  });

  const response = await fetch(buildUrl(path, params), {
    method: context.method,
    headers: context.headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  // 204 No Content (DELETE) no trae cuerpo
  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }

  return data;
}

export const httpClient = {
  get: (path, options) => request(path, { ...options, method: "GET" }),
  post: (path, body, options) => request(path, { ...options, method: "POST", body }),
  patch: (path, body, options) => request(path, { ...options, method: "PATCH", body }),
  delete: (path, options) => request(path, { ...options, method: "DELETE" }),
};

export { BASE_URL };
