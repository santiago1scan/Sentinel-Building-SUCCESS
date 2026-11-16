import { Outlet, useLocation } from "react-router";
import MainLayout from "../shared/ui/templates/MainLayout";

const pageInfo = {
  "/panel": {
    title: "Panel principal",
    subtitle: "Monitoreo y coordinación de emergencias",
  },
  "/edificios": {
    title: "Edificios",
    subtitle: "Administración de edificios registrados",
  },
  "/zonas": {
    title: "Zonas",
    subtitle: "Organización de pisos y zonas monitoreadas",
  },
  "/nodos": {
    title: "Nodos sensores",
    subtitle: "Registro, asignación y estado de dispositivos",
  },
  "/eventos": {
    title: "Eventos",
    subtitle: "Consulta y seguimiento de alertas",
  },
  "/historial": {
    title: "Historial",
    subtitle: "Consulta de eventos registrados anteriormente",
  },
};

/** Estructura de las pantallas del panel: barra lateral y encabezado, con la página en Outlet. */
function PanelLayout() {
  const { pathname } = useLocation();
  const info = pageInfo[pathname] ?? pageInfo["/panel"];

  return (
    <MainLayout title={info.title} subtitle={info.subtitle}>
      <Outlet />
    </MainLayout>
  );
}

export default PanelLayout;
