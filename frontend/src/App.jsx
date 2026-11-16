
import { useEffect, useState } from "react";

import MainLayout from "./layouts/MainLayout";
import Dashboard from "./pages/Dashboard";
import Buildings from "./pages/Buildings";
import Zones from "./pages/Zones";
import Nodes from "./pages/Nodes";

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

  function renderPage() {
    switch (currentPage) {
      case "dashboard":
        return <Dashboard />;

      case "buildings":
        return <Buildings />;

      case "zones":
        return <Zones />;

      case "nodes":
        return <Nodes />;

      default:
        return (
          <div className="card">
            <h2>{pages[currentPage]?.title}</h2>
            <p>Este módulo está en desarrollo.</p>
          </div>
        );
    }
  }

  return (
    <MainLayout
      title={pages[currentPage].title}
      subtitle={pages[currentPage].subtitle}
    >
      {renderPage()}
    </MainLayout>
  );
}

export default App;
