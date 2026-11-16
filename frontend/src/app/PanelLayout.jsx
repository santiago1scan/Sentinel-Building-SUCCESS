import { Outlet, useLocation } from "react-router";
import MainLayout from "../shared/ui/templates/MainLayout";

const pageInfo = {
  "/panel": {
    title: "Panel principal",
    subtitle: "Monitoreo y coordinación de emergencias",
  },
  "/panel/builders/create": {
    title: "Nuevo edificio",
    subtitle: "Alta de un edificio para el monitoreo",
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

/** Ruta de un edificio concreto: /panel/builders/:id (el nombre va en la página, no en el encabezado). */
function buildingInfo(pathname) {
  if (/^\/panel\/builders\/\d+$/.test(pathname)) {
    return { title: "Edificio", subtitle: "Pisos y zonas del edificio" };
  }
  return undefined;
}

/** Estructura de las pantallas del panel: barra lateral y encabezado, con la página en Outlet. */
function PanelLayout() {
  const { pathname } = useLocation();
  const info = pageInfo[pathname] ?? buildingInfo(pathname) ?? pageInfo["/panel"];

  return (
    <MainLayout title={info.title} subtitle={info.subtitle}>
      <Outlet />
    </MainLayout>
  );
}

export default PanelLayout;
