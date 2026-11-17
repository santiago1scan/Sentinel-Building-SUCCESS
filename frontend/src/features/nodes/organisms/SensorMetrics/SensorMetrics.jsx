import MetricChartCard from "../../molecules/MetricChartCard/MetricChartCard";
import styles from "./SensorMetrics.module.css";

/** Una gráfica por sensor y métrica del nodo. `groups` sale de groupReadings. */
function SensorMetrics({ groups }) {
  if (groups.length === 0) {
    return <p className={styles.empty}>Este nodo aún no ha recibido lecturas.</p>;
  }

  return (
    <div className={styles.grid}>
      {groups.map((group) => (
        <MetricChartCard key={group.key} group={group} />
      ))}
    </div>
  );
}

export default SensorMetrics;
