import NodeInfo from "../../../../shared/ui/molecules/nodes/NodeInfo";
import styles from "./ZoneBox.module.css";

/** Una zona del piso: su nombre y los nodos que están en ella. */
function ZoneBox({ zone, nodes }) {
  return (
    <section className={styles.zone} aria-label={`Zona ${zone.name}`}>
      <h3 className={styles.name}>{zone.name}</h3>

      {nodes.length === 0 ? (
        <p className={styles.empty}>Sin nodos</p>
      ) : (
        <ul className={styles.nodes}>
          {nodes.map((node) => (
            <li key={node.node_id}>
              <NodeInfo node={node} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default ZoneBox;
