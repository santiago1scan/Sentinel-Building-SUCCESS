/**
 * Puente entre el cliente HTTP y Firebase Auth.
 *
 * El proveedor real se registra una vez al iniciar sesión, por ejemplo:
 *   setAuthTokenProvider(() => auth.currentUser?.getIdToken() ?? null)
 *
 * Así httpClient no depende directamente del SDK de Firebase.
 */

let tokenProvider = null;

export function setAuthTokenProvider(provider) {
  tokenProvider = provider;
}

export async function getAuthToken() {
  if (!tokenProvider) return null;
  return tokenProvider();
}
