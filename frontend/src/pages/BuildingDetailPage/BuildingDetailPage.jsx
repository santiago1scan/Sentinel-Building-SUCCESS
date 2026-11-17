import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { buildingsService } from "../../shared/services/buildingsService";
import { zonesService } from "../../shared/services/zonesService";
import { floorsService } from "../../features/floors/services/floorsService";
import { nodesService } from "../../shared/services/nodesService";
import { ApiError } from "../../shared/services/httpClient";
import PendingRegistrations from "../../features/buildings/organisms/PendingRegistrations/PendingRegistrations";
import FloorsGrid from "../../features/floors/organisms/FloorsGrid/FloorsGrid";
import styles from "./BuildingDetailPage.module.css";

/** Visualiza un edificio: nombre y dirección en grande, y sus pisos con sus zonas en una grilla. */
function BuildingDetailPage() {
  const { buildingId } = useParams();
  const [state, setState] = useState({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    Promise.all([
      buildingsService.getById(buildingId),
      floorsService.listByBuilding(buildingId),
      zonesService.listByBuilding(buildingId),
      nodesService.list(),
    ])
      .then(([building, floors, zones, nodes]) => {
        if (active) setState({ status: "ready", building, floors, zones, nodes });
      })
      .catch((error) => {
        if (active) {
          const notFound = error instanceof ApiError && error.status === 404;
          setState({ status: notFound ? "notfound" : "error" });
        }
      });
    return () => {
      active = false;
    };
  }, [buildingId, reloadKey]);

  if (state.status === "loading") {
    return <p role="status">Cargando edificio…</p>;
  }

  if (state.status === "notfound") {
    return <p role="alert" className={styles.error}>No encontramos este edificio.</p>;
  }

  if (state.status === "error") {
    return <p role="alert" className={styles.error}>No pudimos cargar el edificio. Intenta de nuevo.</p>;
  }

  const { building, floors, zones, nodes } = state;

  // Nodos agrupados por zona: cada zona muestra los suyos.
  const nodesByZone = {};
  for (const node of nodes) {
    (nodesByZone[node.zone_id] ??= []).push(node);
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h2 className={styles.name}>{building.name}</h2>
        <p className={styles.id}>ID: {building.building_id ?? buildingId}</p>
        <p className={styles.address}>{building.address || "Sin dirección"}</p>
      </header>

      <PendingRegistrations zones={zones} onApproved={() => setReloadKey((k) => k + 1)} />

      <FloorsGrid floors={floors} zones={zones} nodesByZone={nodesByZone} />
    </div>
  );
}

export default BuildingDetailPage;
