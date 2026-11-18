import LineChart from "../../../../shared/ui/molecules/charts/LineChart";
import styles from "./MetricChartCard.module.css";

const formatDate = (ms) => new Date(ms).toLocaleString("es");

/**
 * Tarjeta de una métrica de un sensor: título, último valor, gráfica y la misma
 * información en tabla (vista alternativa para quien no ve la gráfica).
 */
function MetricChartCard({ group }) {
  const metric = group.metric ?? null;
  const unit = metric?.unit ?? group.type?.default_unit ?? "";
  const sensorName = group.sensor?.code ?? `Sensor #${group.sensorId}`;
  // Nombre legible de la variable; si el catálogo no la describe, su código y, en último caso, el número.
  const metricLabel = metric?.name || metric?.metric_code || (group.metricId != null ? `métrica #${group.metricId}` : null);
  const title = metricLabel ? `${metricLabel} · ${sensorName}` : sensorName;

  // El rango normal es de la métrica. Un tipo de sensor con una única métrica puede usar el rango del tipo.
  const range =
    metric && metric.normal_minimum != null && metric.normal_maximum != null
      ? metric
      : group.type && group.singleMetric
        ? group.type
        : null;
  const band =
    range && range.normal_minimum != null && range.normal_maximum != null
      ? { min: Number(range.normal_minimum), max: Number(range.normal_maximum) }
      : null;

  const rows = group.series
    .flatMap((s) => s.points.map((p) => ({ ...p, label: s.label })))
    .sort((a, b) => b.x - a.x)
    .slice(0, 20);

  return (
    <article className={styles.card} data-alert={group.alert ? group.alert.tone : undefined}>
      <header className={styles.header}>
        <div>
          {group.alert && (
            <p className={styles.alertBadge}>
              <span aria-hidden="true">⚠</span> {group.alert.label}
            </p>
          )}
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
