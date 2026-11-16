import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
} from "firebase/auth";

import { auth } from "../../../shared/lib/firebase";
import { setAuthTokenProvider } from "../../../shared/services/authToken";
import { httpClient, ApiError } from "../../../shared/services/httpClient";

/**
 * Autenticación del panel con Firebase (correo y contraseña).
 *
 * Flujo:
 * 1. connectAuthToken() se llama una vez al arrancar: el interceptor usa el usuario actual de Firebase.
 * 2. signInWithGoogle() inicia sesión y comprueba en la API que el correo sea administrador (403 = sin permisos).
 * 3. signOut() cierra la sesión.
 */

/** Conecta el token de Firebase con el interceptor de autenticación. */
export function connectAuthToken() {
  setAuthTokenProvider(() => auth.currentUser?.getIdToken() ?? null);
}

const googleProvider = new GoogleAuthProvider();

export const authService = {
  /**
   * Inicia sesión con Google (ventana emergente). Si la cuenta no es administradora en la API,
   * cierra la sesión y lanza un error con mensaje para el usuario.
   */
  async signInWithGoogle() {
    const credential = await signInWithPopup(auth, googleProvider);

    const isAdmin = await this.hasAdminAccess();
    if (!isAdmin) {
      await firebaseSignOut(auth);
      throw new Error("Tu cuenta no tiene permisos de administrador en el panel.");
    }

    return credential.user;
  },

  signOut() {
    return firebaseSignOut(auth);
  },

  /** Suscribe a cambios de sesión. Devuelve la función para cancelar la suscripción. */
  onSessionChange(callback) {
    return onAuthStateChanged(auth, callback);
  },

  /** Devuelve true si el token actual tiene acceso al panel; false si el backend responde 403. */
  async hasAdminAccess() {
    try {
      // Cualquier ruta protegida sirve como prueba; limit=1 minimiza la respuesta.
      await httpClient.get("/nodes", { params: { limit: 1 } });
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 403) {
        return false;
      }
      throw error;
    }
  },

  /** Perfil de usuario de la aplicación (tabla app_users) para un correo. */
  getAppUserByEmail(email) {
    return httpClient.get(`/app-users/email/${encodeURIComponent(email)}`);
  },
};
