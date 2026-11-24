import { Link } from "react-router";
import styles from "./NodeAlerts.module.css";

/**
 * UNA alerta por categoría (temperatura, movimiento, energía…) con los sensores que están fuera de rango o
 * fallando. Se atiende la categoría completa. `groups` sale de groupAlerts. La usan la tarjeta del nodo en
 * /panel y la página de detalle del nodo. Con `nodeHref`, hacer clic en la alerta lleva a esa dirección (el
 * detalle del nodo); el botón de atender sigue funcionando por separado.
 */
/** Gravedad que calcula el backend: no dice qué pasó (vela, incendio), solo qué tan grave se ve. */
const GRAVITY_LABEL = { emergencia: "Emergencia", leve: "Leve" };

function NodeAlerts({ groups = [], handling = {}, onHandle = () => {}, nodeHref = null }) {
  if (groups.length === 0) return null;
  return (
    <ul className={styles.alertList} aria-label="Alertas del nodo">
      {groups.map((group) => {
        const busy = Boolean(handling[group.key]);
        return (
          <li key={group.key} className={styles.alertGroup} data-severity={group.severity}
            data-attended={group.attended ? "" : undefined}
            data-link={nodeHref ? "" : undefined}
          >
            <div className={styles.groupHead}>
              <span>
                <span aria-hidden="true">⚠</span>{" "}
                {nodeHref ? (
                  <Link
                    to={nodeHref}
                    className={styles.groupLink}
                    aria-label={`Ver ${group.title.toLowerCase()} en el detalle del nodo`}
                  >
                    {group.title}
                  </Link>
                ) : (
                  group.title
                )}
                {group.gravity && (
                  <span className={styles.gravity} data-gravity={group.gravity}>
                    {GRAVITY_LABEL[group.gravity]}
                  </span>
                )}
                <span className={styles.groupState}>
                  {group.live ? "Activa" : "Terminó · sin atender"}
                </span>
              </span>
              {group.attended ? (
                <span className={styles.attended}>✓ Atendida</span>
              ) : (
                <button
                  type="button"
                  className={styles.handleButton}
                  disabled={busy}
                  onClick={() => onHandle(group)}
                >
                  {busy ? "Guardando…" : "Marcar atendida"}
                </button>
              )}
            </div>

            <ul className={styles.sensorList} aria-label={`Sensores en ${group.label.toLowerCase()}`}>
              {group.sensors.map((sensor) => (
                <li key={sensor.sensorId ?? "node"} className={styles.sensorRow}>
                  <span className={styles.sensorCode}>{sensor.code}</span>
                  {sensor.tags.map((tag) => (
                    <span key={tag.text} className={styles.tag} data-tone={tag.tone}>{tag.text}</span>
                  ))}
                </li>
              ))}
            </ul>
          </li>
        );
      })}
    </ul>
  );
}

export default NodeAlerts;
