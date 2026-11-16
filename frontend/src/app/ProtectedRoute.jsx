import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router";
import { authService } from "../features/login/services/authService";

/**
 * Muestra la ruta solo con sesión iniciada. Si no hay sesión, redirige a /login
 * y recuerda la ruta original para volver a ella después de entrar.
 */
function ProtectedRoute({ children }) {
  const [status, setStatus] = useState("loading");
  const location = useLocation();

  useEffect(() => {
    return authService.onSessionChange((user) => {
      setStatus(user ? "signed-in" : "signed-out");
    });
  }, []);

  if (status === "loading") {
    return <p role="status">Verificando sesión…</p>;
  }

  if (status === "signed-out") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}

export default ProtectedRoute;
