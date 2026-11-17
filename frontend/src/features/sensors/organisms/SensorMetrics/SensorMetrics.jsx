import { useMemo } from "react";
import MetricChartCard from "../../molecules/MetricChartCard/MetricChartCard";
import { groupReadings } from "../../sensorMetrics";
import styles from "./SensorMetrics.module.css";

/** Sección "Métricas": una gráfica por sensor y métrica a partir de sus lecturas. */
function SensorMetrics({ readings, sensors, sensorTypes }) {
  const groups = useMemo(() => groupReadings(readings, sensors, sensorTypes), [readings, sensors, sensorTypes]);

  return (
    <section className={styles.section} aria-labelledby="metrics-title">
      <h3 id="metrics-title" className={styles.title}>
        Métricas
      </h3>
      {groups.length === 0 ? (
        <p className={styles.empty}>Este nodo aún no ha recibido lecturas.</p>
      ) : (
        <div className={styles.grid}>
          {groups.map((group) => (
            <MetricChartCard key={group.key} group={group} />
          ))}
        </div>
      )}
    </section>
  );
}

export default SensorMetrics;
