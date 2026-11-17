import LineChart from "../../../../shared/ui/molecules/charts/LineChart";
import styles from "./MetricChartCard.module.css";

const formatDate = (ms) => new Date(ms).toLocaleString("es");

/**
 * Tarjeta de una métrica de un sensor: título, último valor, gráfica y la misma
 * información en tabla (vista alternativa para quien no ve la gráfica).
 */
function MetricChartCard({ group }) {
  const unit = group.type?.default_unit ?? "";
  const sensorName = group.sensor?.code ?? `Sensor #${group.sensorId}`;
  const title = `${sensorName}${group.metricId != null ? ` · métrica #${group.metricId}` : ""}`;

  // El rango normal es del tipo de sensor: solo se dibuja si el sensor tiene una única métrica.
  const band =
    group.type && group.type.normal_minimum != null && group.type.normal_maximum != null && group.singleMetric
      ? { min: Number(group.type.normal_minimum), max: Number(group.type.normal_maximum) }
      : null;

  const rows = group.series
    .flatMap((s) => s.points.map((p) => ({ ...p, label: s.label })))
    .sort((a, b) => b.x - a.x)
    .slice(0, 20);

  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <div>
          <h3 className={styles.title}>{title}</h3>
          <p className={styles.subtitle}>
            {group.type?.name ?? "Tipo desconocido"} · {group.count} lecturas
          </p>
        </div>
        {group.last && (
          <p className={styles.last}>
            {Number.isInteger(group.last.y) ? group.last.y : group.last.y.toFixed(2)} {unit}
            <span>último valor</span>
          </p>
        )}
      </header>

      <LineChart series={group.series} unit={unit} band={band} title={`Lecturas de ${title}`} />

      <details className={styles.table}>
        <summary>Ver datos</summary>
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Tipo</th>
              <th>Valor {unit && `(${unit})`}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.label}-${row.x}`}>
                <td>{formatDate(row.x)}</td>
                <td>{row.label}</td>
                <td>{row.y}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </article>
  );
}

export default MetricChartCard;
