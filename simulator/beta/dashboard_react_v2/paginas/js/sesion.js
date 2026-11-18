// Sesión de Firebase compartida por las páginas (inicio, login y perfil).
//
// Lee la configuración pública del servidor y carga el SDK. Devuelve null si Firebase no está
// configurado; lanza un Error si no se puede leer la configuración o cargar el SDK.
const SDK = "https://www.gstatic.com/firebasejs/10.12.2";

export async function iniciarFirebase() {
  const respuesta = await fetch("/auth/config");
  if (!respuesta.ok) throw new Error("No se pudo leer la configuración de Firebase.");
  const cfg = await respuesta.json();
  if (!cfg.configurado) return null;

  const [{ initializeApp }, autenticacion] = await Promise.all([
    import(`${SDK}/firebase-app.js`),
    import(`${SDK}/firebase-auth.js`),
  ]);
  // `auth` más las funciones del SDK (onAuthStateChanged, signOut, signInWithPopup, GoogleAuthProvider…).
  return { auth: autenticacion.getAuth(initializeApp(cfg)), ...autenticacion };
}

export function nombreDe(user) {
  return user.displayName || (user.email || "").split("@")[0] || "Usuario";
}

export function inicialDe(user) {
  return (nombreDe(user).trim().charAt(0) || "?").toUpperCase();
}
