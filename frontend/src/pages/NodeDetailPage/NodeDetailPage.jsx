import { useMemo } from "react";
import { Link, useParams } from "react-router";
import { useNodeDetail } from "../../features/nodes/hooks/useNodeDetail";
import { useNodeAlerts } from "../../features/nodes/hooks/useNodeAlerts";
import { buildCatalog, groupAlerts } from "../../features/nodes/alertGroups";
import NodeSummary from "../../features/nodes/organisms/NodeSummary/NodeSummary";
import ConnectivityHistory from "../../features/nodes/organisms/ConnectivityHistory/ConnectivityHistory";
import SensorMetrics from "../../features/sensors/organisms/SensorMetrics/SensorMetrics";
import SensorList from "../../features/sensors/organisms/SensorList/SensorList";
import NodeAlerts from "../../shared/ui/molecules/nodes/NodeAlerts";
import styles from "./NodeDetailPage.module.css";

/**
 * Un nodo con toda su información. La página solo compone los contenedores de los features. Si el nodo
 * tiene alertas, muestra la misma alerta por categoría que /panel y sube las gráficas afectadas. Al atenderla
 * deja de verse en rojo (la fila queda listada, en neutro, mientras la condición continúe).
 */
function NodeDetailPage() {
  const { nodeId } = useParams();
  const detail = useNodeDetail(nodeId);
  const { alerts, streamDown, handling, actionError, handleGroup } = useNodeAlerts(nodeId);

  const ready = detail.status === "ready";
  const alertGroups = useMemo(
    () => groupAlerts(alerts, ready ? buildCatalog(detail.sensors, detail.sensorTypes) : buildCatalog()),
    [alerts, ready, detail.sensors, detail.sensorTypes],
  );

  // Solo lo pendiente pinta rojo: una alerta atendida sigue listada, pero neutra.
  const pending = useMemo(() => alerts.filter((alert) => !alert.handled_by_user_id), [alerts]);

  if (detail.status === "loading") return <p role="status">Cargando nodo…</p>;
  if (detail.status === "notfound") return <p role="alert" className={styles.error}>No encontramos este nodo.</p>;
  if (detail.status === "error") {
    return <p role="alert" className={styles.error}>No pudimos cargar el nodo. Intenta de nuevo.</p>;
  }

  const pendingGroups = alertGroups.filter((group) => !group.attended);
  const severity = pendingGroups.length === 0
    ? "attended"
    : pendingGroups.some((group) => group.severity === "alert") ? "alert" : "warning";

  return (
    <div className={styles.page}>
      <Link to={-1} className={styles.back}>
        ← Volver
      </Link>

      <NodeSummary
        node={detail.node}
        sensorCount={detail.sensors.length}
        readingCount={detail.readings.length}
        connectivity={detail.connectivity}
      />

      {streamDown && (
        <p role="status" className={styles.notice}>
          Sin actualizaciones de alertas en vivo. Reintentando la conexión…
        </p>
      )}
      {actionError && (
        <p role="alert" className={styles.notice}>
          {actionError}
        </p>
      )}
      {alertGroups.length > 0 && (
        <section className={styles.alerts} data-status={severity} aria-labelledby="node-alerts-title">
          <h3 id="node-alerts-title" className={styles.alertsTitle}>
            Alertas del nodo
          </h3>
          <NodeAlerts groups={alertGroups} handling={handling} onHandle={handleGroup} />
        </section>
      )}

      <SensorMetrics
        readings={detail.readings}
        sensors={detail.sensors}
        sensorTypes={detail.sensorTypes}
        alerts={pending}
      />
      <SensorList sensors={detail.sensors} sensorTypes={detail.sensorTypes} />
      <ConnectivityHistory logs={detail.logs} now={detail.now} />
    </div>
  );
}

export default NodeDetailPage;
