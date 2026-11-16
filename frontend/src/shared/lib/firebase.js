import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

/**
 * Configuración de Firebase para el cliente web.
 * Valores en frontend/.env (ver .env.example). Son identificadores públicos del proyecto;
 * la seguridad real la aplica el backend validando el ID token.
 */
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const missingKeys = Object.entries(firebaseConfig)
  .filter(([, value]) => !value)
  .map(([key]) => key);

if (missingKeys.length > 0) {
  throw new Error(
    `Faltan variables de Firebase en frontend/.env: ${missingKeys.join(", ")}. ` +
      "Copia los valores de Firebase console > Configuración del proyecto > Tus apps.",
  );
}

export const firebaseApp = initializeApp(firebaseConfig);
export const auth = getAuth(firebaseApp);
