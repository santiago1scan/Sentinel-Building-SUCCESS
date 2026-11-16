import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import ProtectedRoute from "./app/ProtectedRoute";
import PanelLayout from "./app/PanelLayout";
import LoginPage from "./pages/LoginPage/LoginPage";
import HomePage from "./pages/HomePage/HomePage";
import PanelPage from "./pages/PanelPage/PanelPage";
import CreateBuildingPage from "./pages/CreateBuildingPage/CreateBuildingPage";

/** Marcador para las secciones que aún no tienen pantalla. */
function ModuleInProgress({ name }) {
  return (
    <section className="card">
      <h2>{name}</h2>
      <p>Este módulo está en desarrollo.</p>
    </section>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />

        <Route
          element={
            <ProtectedRoute>
              <PanelLayout />
            </ProtectedRoute>
          }
        >
          <Route path="panel" element={<PanelPage />} />
          <Route path="panel/builders/create" element={<CreateBuildingPage />} />
          <Route path="edificios" element={<ModuleInProgress name="Edificios" />} />
          <Route path="zonas" element={<ModuleInProgress name="Zonas" />} />
          <Route path="nodos" element={<ModuleInProgress name="Nodos sensores" />} />
          <Route path="eventos" element={<ModuleInProgress name="Eventos" />} />
          <Route path="historial" element={<ModuleInProgress name="Historial" />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
