import { Link, useParams } from "react-router";
import { useNodeDetail } from "../../features/nodes/hooks/useNodeDetail";
import NodeSummary from "../../features/nodes/organisms/NodeSummary/NodeSummary";
import ConnectivityHistory from "../../features/nodes/organisms/ConnectivityHistory/ConnectivityHistory";
import SensorMetrics from "../../features/sensors/organisms/SensorMetrics/SensorMetrics";
import SensorList from "../../features/sensors/organisms/SensorList/SensorList";
import styles from "./NodeDetailPage.module.css";

/** Un nodo con toda su información. La página solo compone los contenedores de los features. */
function NodeDetailPage() {
  const { nodeId } = useParams();
  const detail = useNodeDetail(nodeId);

  if (detail.status === "loading") return <p role="status">Cargando nodo…</p>;
  if (detail.status === "notfound") return <p role="alert" className={styles.error}>No encontramos este nodo.</p>;
  if (detail.status === "error") {
    return <p role="alert" className={styles.error}>No pudimos cargar el nodo. Intenta de nuevo.</p>;
  }

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
      <SensorMetrics readings={detail.readings} sensors={detail.sensors} sensorTypes={detail.sensorTypes} />
      <SensorList sensors={detail.sensors} sensorTypes={detail.sensorTypes} />
      <ConnectivityHistory logs={detail.logs} now={detail.now} />
    </div>
  );
}

export default NodeDetailPage;
