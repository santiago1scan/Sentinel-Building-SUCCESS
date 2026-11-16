import { useState } from "react";
import { useLocation, useNavigate } from "react-router";
import PublicHeader from "../../shared/ui/organisms/PublicHeader";
import { authService } from "../../features/login/services/authService";
import styles from "./LoginPage.module.css";

function errorMessage(error) {
  if (error?.code === "auth/popup-closed-by-user") {
    return "Cerraste la ventana de Google antes de terminar.";
  }
  if (error?.code === "auth/network-request-failed") {
    return "Sin conexión. Revisa tu red e intenta de nuevo.";
  }
  if (error?.message?.startsWith("Tu cuenta")) {
    return error.message;
  }
  return "No pudimos iniciar sesión. Intenta de nuevo.";
}

/** Formulario de inicio de sesión con Google para administradores. */
function LoginPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const destination = location.state?.from ?? "/panel";

  async function handleSignIn() {
    setIsLoading(true);
    setError("");

    try {
      await authService.signInWithGoogle();
      navigate(destination, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setIsLoading(false);
    }
  }

  return (
    <div className={styles.page}>
      <PublicHeader action={{ to: "/", label: "Volver al inicio" }} />

      <main className={styles.main}>
        <form
          className={styles.form}
          aria-labelledby="login-title"
          onSubmit={(event) => {
            event.preventDefault();
            handleSignIn();
          }}
        >


          <header className={styles.heading}>
            <h1 id="login-title" className={styles.title}>Iniciar sesión</h1>
            <p className={styles.subtitle}>Accede al panel de Sentinel Building.</p>
          </header>

          {error && (
            <p role="alert" className={styles.error}>
              {error}
            </p>
          )}

          <button type="submit" className={styles.provider} disabled={isLoading}>
            <span className={styles.providerIcon} aria-hidden="true">G</span>
            {isLoading ? "Conectando…" : "Continuar con Google"}
          </button>

          <p className={styles.note}>
            Acceso solo para administradores autorizados. Si necesitas una cuenta,
            solicítala a quien administra el sistema.
          </p>
        </form>
      </main>
    </div>
  );
}

export default LoginPage;
