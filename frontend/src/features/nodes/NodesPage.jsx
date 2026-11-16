import { useEffect, useMemo, useState } from "react";
import { nodesService } from "../../shared/services/nodesService";
import { alertsService } from "../../shared/services/alertsService";
import { connectivityService } from "../../shared/services/connectivityService";
import TextInput from "../../shared/ui/atoms/TextInput";
import SelectInput from "../../shared/ui/atoms/SelectInput";
import NodeCard from "./components/NodeCard";
import { NODE_STATUS, deriveNodeStatus } from "./nodeStatus";
import styles from "./NodesPage.module.css";

const STATUS_FILTER_OPTIONS = [
  { value: "all", label: "Todos los estados" },
  ...Object.entries(NODE_STATUS).map(([value, info]) => ({ value, label: info.label })),
];

/** Une nodos, alertas abiertas y conectividad activa en una lista lista para mostrar. */
async function loadNodeStatuses() {
  const nodes = await nodesService.list();
  const [openAlerts, activeLogs] = await Promise.all([
    alertsService.listOpen(),
    Promise.all(nodes.map((node) => connectivityService.listActiveByNode(node.node_id))),
  ]);

  return nodes.map((node, index) => {
    const alerts = openAlerts.filter((alert) => alert.node_id === node.node_id);
    const status = deriveNodeStatus({
      isConnected: activeLogs[index].length > 0,
      openAlerts: alerts,
    });
    return { node, status, openAlerts: alerts };
  });
}

/** Pantalla de nodos sensores: resumen, filtros y tarjetas ordenadas por urgencia. */
function NodesPage() {
  const [state, setState] = useState({ status: "loading", items: [], error: "" });
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    loadNodeStatuses()
      .then((items) => {
        if (!cancelled) setState({ status: "ready", items, error: "" });
      })
      .catch(() => {
        if (!cancelled) {
          setState({ status: "error", items: [], error: "No pudimos cargar los nodos." });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  function reload() {
    setState({ status: "loading", items: [], error: "" });
    setReloadKey((key) => key + 1);
  }

  const counts = useMemo(() => {
    const result = Object.fromEntries(Object.keys(NODE_STATUS).map((key) => [key, 0]));
    state.items.forEach((item) => {
      result[item.status] += 1;
    });
    return result;
  }, [state.items]);

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    return state.items
      .filter((item) => statusFilter === "all" || item.status === statusFilter)
      .filter(
        (item) =>
          !term ||
          item.node.name.toLowerCase().includes(term) ||
          item.node.code.toLowerCase().includes(term),
      )
      .sort(
        (a, b) =>
          NODE_STATUS[a.status].rank - NODE_STATUS[b.status].rank ||
          a.node.name.localeCompare(b.node.name),
      );
  }, [state.items, query, statusFilter]);

  if (state.status === "loading") {
    return <p role="status">Cargando nodos…</p>;
  }

  if (state.status === "error") {
    return (
      <section className={styles.error} role="alert">
        <p>{state.error}</p>
        <button type="button" className={styles.retry} onClick={reload}>
          Reintentar
        </button>
      </section>
    );
  }

  return (
    <div className={styles.page}>
      <ul className={styles.summary} aria-label="Resumen por estado">
        {Object.entries(NODE_STATUS).map(([key, info]) => (
          <li key={key} className={styles.summaryItem} data-status={key}>
            <span className={styles.summaryIcon} aria-hidden="true">{info.icon}</span>
            <span className={styles.summaryCount}>{counts[key]}</span>
            <span>{info.label}</span>
          </li>
        ))}
      </ul>

      <div className={styles.toolbar}>
        <TextInput
          id="nodes-search"
          label="Buscar por nombre o código"
          value={query}
          onChange={setQuery}
          placeholder="Ej. sensor-piso-2"
          type="search"
        />
        <SelectInput
          id="nodes-status"
          label="Estado"
          value={statusFilter}
          onChange={setStatusFilter}
          options={STATUS_FILTER_OPTIONS}
        />
      </div>

      {visible.length === 0 ? (
        <p className={styles.empty}>
          {state.items.length === 0
            ? "Aún no hay nodos registrados."
            : "Ningún nodo coincide con la búsqueda o el filtro."}
        </p>
      ) : (
        <ul className={styles.grid}>
          {visible.map(({ node, status, openAlerts }) => (
            <li key={node.node_id}>
              <NodeCard node={node} status={status} openAlerts={openAlerts} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default NodesPage;
