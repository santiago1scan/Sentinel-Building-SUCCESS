import { formatDuration } from "../../nodeMetrics";
import styles from "./ConnectivityHistory.module.css";

const formatDate = (value) => new Date(value).toLocaleString("es");

/** Sesiones de conexión del nodo, de la más reciente a la más antigua. `now` (ms) mide las sesiones abiertas. */
function ConnectivityHistory({ logs, now }) {
  if (logs.length === 0) {
    return <p className={styles.empty}>Sin registros de conexión.</p>;
  }

  const rows = [...logs].sort((a, b) => new Date(b.started_at) - new Date(a.started_at)).slice(0, 15);

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Inicio</th>
          <th>Fin</th>
          <th>Duración</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((log) => {
          const end = log.ended_at ? new Date(log.ended_at).getTime() : now;
          return (
            <tr key={log.connectivity_id}>
              <td>{formatDate(log.started_at)}</td>
              <td>{log.ended_at ? formatDate(log.ended_at) : "En curso"}</td>
              <td>{formatDuration(end - new Date(log.started_at).getTime())}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default ConnectivityHistory;
