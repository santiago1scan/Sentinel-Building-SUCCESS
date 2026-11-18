import StatTile from "../../molecules/StatTile/StatTile";
import { formatDuration } from "../../nodeMetrics";
import styles from "./NodeSummary.module.css";

/** Encabezado del nodo y sus datos resumidos: conexión, sensores, lecturas y fecha de registro. */
function NodeSummary({ node, sensorCount, readingCount, connectivity }) {
  return (
    <>
      <header className={styles.header}>
        <h2 className={styles.name}>{node.name}</h2>
        <p className={styles.sub}>
          ID {node.node_id} · {node.code} · Zona #{node.zone_id}
        </p>
      </header>

      <dl className={styles.stats}>
        <StatTile
          label="Conexión"
          value={connectivity.connected ? "Conectado" : "Desconectado"}
          hint={
            connectivity.connected
              ? `Desde ${new Date(connectivity.connectedSince).toLocaleString("es")}`
              : "Sin sesión abierta"
          }
        />
        <StatTile
          label="Tiempo conectado"
          value={formatDuration(connectivity.connectedMs)}
          hint={`${connectivity.sessions} sesiones`}
        />
        <StatTile label="Sensores" value={sensorCount} />
        <StatTile label="Lecturas recibidas" value={readingCount} />
        <StatTile label="Registrado" value={new Date(node.registered_at).toLocaleDateString("es")} />
      </dl>
    </>
  );
}

export default NodeSummary;
