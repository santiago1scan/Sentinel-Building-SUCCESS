
import { useEffect, useState } from "react";

import MainLayout from "./shared/ui/templates/MainLayout";

const pages = {
  dashboard: {
    title: "Panel principal",
    subtitle: "Monitoreo y coordinación de emergencias",
  },
  buildings: {
    title: "Edificios",
    subtitle: "Administración de edificios registrados",
  },
  zones: {
    title: "Zonas",
    subtitle: "Organización de pisos y zonas monitoreadas",
  },
  nodes: {
    title: "Nodos sensores",
    subtitle: "Registro, asignación y estado de dispositivos",
  },
  events: {
    title: "Eventos",
    subtitle: "Consulta y seguimiento de alertas",
  },
  simulator: {
    title: "Simulador",
    subtitle: "Pruebas controladas de escenarios",
  },
  history: {
    title: "Historial",
    subtitle: "Consulta de eventos registrados anteriormente",
  },
};

function App() {
  const [currentPage, setCurrentPage] = useState("dashboard");

  useEffect(() => {
    function handleNavigation(event) {
      setCurrentPage(event.detail);
    }

    window.addEventListener("navigate", handleNavigation);

    return () => {
      window.removeEventListener("navigate", handleNavigation);
    };
  }, []);

  // Las páginas se implementarán en features/. Por ahora todas muestran un marcador.
  function renderPage() {
    return (
      <div className="card">
        <h2>{pages[currentPage]?.title}</h2>
        <p>Este módulo está en desarrollo.</p>
      </div>
    );
  }

  return (
    <MainLayout
      title={pages[currentPage]?.title}
      subtitle={pages[currentPage]?.subtitle}
    >
      {renderPage()}
    </MainLayout>
  );
}

export default App;
