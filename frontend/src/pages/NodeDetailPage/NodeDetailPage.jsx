import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { nodesService } from "../../shared/services/nodesService";
import { sensorTypesService } from "../../shared/services/readingsService";
import { ApiError } from "../../shared/services/httpClient";
import StatTile from "../../features/nodes/molecules/StatTile/StatTile";
import SensorMetrics from "../../features/nodes/organisms/SensorMetrics/SensorMetrics";
import ConnectivityHistory from "../../features/nodes/organisms/ConnectivityHistory/ConnectivityHistory";
import { formatDuration, groupReadings, summarizeConnectivity } from "../../features/nodes/nodeMetrics";
import styles from "./NodeDetailPage.module.css";

/** Un nodo con toda su información: datos generales, sensores, conectividad y gráficas de métricas. */
function NodeDetailPage() {
  const { nodeId } = useParams();
  const [state, setState] = useState({ status: "loading" });
  const [now] = useState(() => Date.now());

  useEffect(() => {
    let active = true;
    Promise.all([
      nodesService.getById(nodeId),
      nodesService.listSensors(nodeId),
      nodesService.listConnectivityLogs(nodeId),
      nodesService.listReceivedReadings(nodeId),
      sensorTypesService.list(),
    ])
      .then(([node, sensors, logs, readings, sensorTypes]) => {
        if (active) setState({ status: "ready", nodeId, node, sensors, logs, readings, sensorTypes });
      })
      .catch((error) => {
        if (active) setState({ status: error instanceof ApiError && error.status === 404 ? "notfound" : "error" });
      });
    return () => {
      active = false;
    };
  }, [nodeId]);

  const derived = useMemo(() => {
    if (state.status !== "ready" || state.nodeId !== nodeId) return null;
    return {
      groups: groupReadings(state.readings, state.sensors, state.sensorTypes),
      connectivity: summarizeConnectivity(state.logs, now),
    };
  }, [state, nodeId, now]);

  if (state.status === "loading" || (state.status === "ready" && state.nodeId !== nodeId)) return <p role="status">Cargando nodo…</p>;
  if (state.status === "notfound") return <p role="alert" className={styles.error}>No encontramos este nodo.</p>;
  if (state.status === "error") {
    return <p role="alert" className={styles.error}>No pudimos cargar el nodo. Intenta de nuevo.</p>;
  }

  const { node, sensors, readings } = state;
  const { groups, connectivity } = derived;
  const typeName = (id) => state.sensorTypes.find((t) => t.sensor_type_id === id)?.name ?? `Tipo #${id}`;

  return (
    <div className={styles.page}>
      <Link to={-1} className={styles.back}>
        ← Volver
      </Link>

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
        <StatTile label="Tiempo conectado" value={formatDuration(connectivity.connectedMs)} hint={`${connectivity.sessions} sesiones`} />
        <StatTile label="Sensores" value={sensors.length} />
        <StatTile label="Lecturas recibidas" value={readings.length} />
        <StatTile label="IP" value={node.ip_address ?? "Sin IP"} />
        <StatTile
          label="Almacenamiento local"
          value={node.local_storage_mb != null ? `${node.local_storage_mb} MB` : "—"}
        />
        <StatTile label="Registrado" value={new Date(node.registered_at).toLocaleDateString("es")} />
      </dl>

      <section className={styles.section} aria-labelledby="metrics-title">
        <h3 id="metrics-title" className={styles.sectionTitle}>
          Métricas
        </h3>
        <SensorMetrics groups={groups} />
      </section>

      <section className={styles.section} aria-labelledby="sensors-title">
        <h3 id="sensors-title" className={styles.sectionTitle}>
          Sensores
        </h3>
        {sensors.length === 0 ? (
          <p className={styles.empty}>Este nodo no tiene sensores.</p>
        ) : (
          <ul className={styles.sensors}>
            {sensors.map((sensor) => (
              <li key={sensor.sensor_id} className={styles.sensor}>
                <strong>{sensor.code}</strong>
                <span>ID {sensor.sensor_id} · {typeName(sensor.sensor_type_id)}</span>
                <span>
                  {sensor.connection_type ?? "Sin conexión"}
                  {sensor.connection_address ? ` · ${sensor.connection_address}` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.section} aria-labelledby="conn-title">
        <h3 id="conn-title" className={styles.sectionTitle}>
          Historial de conexión
        </h3>
        <ConnectivityHistory logs={state.logs} now={now} />
      </section>
    </div>
  );
}

export default NodeDetailPage;
