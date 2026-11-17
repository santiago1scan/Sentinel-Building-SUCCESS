import styles from "./SensorList.module.css";

/** Sensores de un nodo: código, ID, tipo y conexión. `sensorTypes` rotula el tipo de cada uno. */
function SensorList({ sensors, sensorTypes }) {
  const typeName = (id) => sensorTypes.find((type) => type.sensor_type_id === id)?.name ?? `Tipo #${id}`;

  return (
    <section className={styles.section} aria-labelledby="sensors-title">
      <h3 id="sensors-title" className={styles.title}>
        Sensores
      </h3>
      {sensors.length === 0 ? (
        <p className={styles.empty}>Este nodo no tiene sensores.</p>
      ) : (
        <ul className={styles.list}>
          {sensors.map((sensor) => (
            <li key={sensor.sensor_id} className={styles.sensor}>
              <strong>{sensor.code}</strong>
              <span>
                ID {sensor.sensor_id} · {typeName(sensor.sensor_type_id)}
              </span>
              <span>
                {sensor.connection_type ?? "Sin conexión"}
                {sensor.connection_address ? ` · ${sensor.connection_address}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default SensorList;
