import { BASE_URL, runRequestInterceptors } from "./httpClient";

/**
 * Suscribe a un endpoint Server-Sent Events (text/event-stream).
 *
 * Usa fetch en lugar de EventSource para enviar el token en el header
 * Authorization, como pide REGISTRO_DE_NODOS.md. EventSource no permite headers
 * y obligaría a poner el token en la URL.
 *
 * @param {string} path
 * @param {object} handlers
 * @param {(eventName: string, data: any) => void} handlers.onEvent
 * @param {(error: Error) => void} [handlers.onError]
 * @returns {() => void} Función para cerrar la conexión
 */
export function subscribeToStream(path, { onEvent, onError } = {}) {
  const controller = new AbortController();

  (async () => {
    try {
      // Pasa por los mismos interceptores que el cliente HTTP (token de Firebase, lista blanca)
      const context = await runRequestInterceptors({
        method: "GET",
        path,
        headers: { Accept: "text/event-stream" },
      });

      const response = await fetch(new URL(path, BASE_URL), {
        headers: context.headers,
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Stream HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Cada evento SSE termina con una línea vacía
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const chunk of chunks) {
          const parsed = parseSseChunk(chunk);
          if (parsed) {
            onEvent?.(parsed.event, parsed.data);
          }
        }
      }
    } catch (error) {
      if (error.name !== "AbortError") {
        onError?.(error);
      }
    }
  })();

  return () => controller.abort();
}

function parseSseChunk(chunk) {
  let event = "message";
  const dataLines = [];

  for (const line of chunk.split("\n")) {
    // Los comentarios (ej. ": keepalive") se ignoran
    if (line.startsWith(":") || line === "") continue;

    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (dataLines.length === 0) return null;

  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return { event, data: dataLines.join("\n") };
  }
}
