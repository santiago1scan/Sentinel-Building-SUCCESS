import { useEffect, useMemo, useState } from "react";
import { nodesService } from "../../shared/services/nodesService";
import { alertsService } from "../../shared/services/alertsService";
import { sensorsService, sensorTypesService } from "../../shared/services/readingsService";
import { buildCatalog, groupAlerts } from "../../features/nodes/alertGroups";
import { applyAlert, isVisible } from "../../features/nodes/alertState";
import TextInput from "../../shared/ui/atoms/inputs/TextInput";
import SelectInput from "../../shared/ui/atoms/selects/SelectInput";
import NodeCard from "../../shared/ui/molecules/nodes/NodeCard";
import { NODE_STATUS, deriveNodeStatus } from "../../shared/ui/atoms/nodes/nodeStatus";
import styles from "./NodesPage.module.css";

/** Solo se muestran los nodos con alertas: estos estados (los de «atendida» ya no piden acción). */
const ALERT_STATUSES = ["alert", "warning", "attended"];
const RETRY_MS = 5000;

const STATUS_FILTER_OPTIONS = [
  { value: "all", label: "Todos los estados" },
  ...ALERT_STATUSES.map((key) => ({ value: key, label: NODE_STATUS[key].label })),
];

/**
 * Nodos con alertas abiertas.
 * Las alertas vienen solo del stream SSE de escucha: primero el estado actual, luego los cambios en
 * vivo. Los nodos vienen de consulta. Si el stream se cae, se reconecta y recibe el estado de nuevo.
 */
function NodesPage() {
  const [loadState, setLoadState] = useState({ status: "loading", error: "" });
  const [nodes, setNodes] = useState([]);
  // Sensores y tipos con sus variables: ponen nombre a lo que está fuera de rango. Si no cargan,
  // las alertas se agrupan igual y se muestran con los ids.
  const [catalog, setCatalog] = useState(() => buildCatalog());
  const [alerts, setAlerts] = useState({});
  const [streamDown, setStreamDown] = useState(false);
  const [alertsReady, setAlertsReady] = useState(false);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [reloadKey, setReloadKey] = useState(0);
  const [handling, setHandling] = useState({});
  const [actionError, setActionError] = useState("");

  useEffect(() => {
    let active = true;
    let stopStream = () => {};
    let retryTimer = null;

    function scheduleRetry() {
      clearTimeout(retryTimer);
      retryTimer = setTimeout(() => {
        if (active) connect();
      }, RETRY_MS);
    }

    function connect() {
      // El stream manda primero todo el estado (alert...) y luego alerts_ready. Mientras llega,
      // se arma una lista nueva; al terminar reemplaza la anterior, así que una alerta que se
      // atendió o terminó mientras no había conexión no se queda como fantasma.
      let ready = false;
      const batch = {};

      stopStream();
      stopStream = alertsService.subscribeToAlerts({
        onAlert: (alert) => {
          if (!active) return;
          if (!ready) {
            if (isVisible(alert)) batch[alert.alert_id] = alert;
            else delete batch[alert.alert_id];
            return;
          }
          setStreamDown(false);
          setAlerts((prev) => applyAlert(prev, alert));
        },
        onReady: () => {
          if (!active) return;
          ready = true;
          setAlerts({ ...batch });
          setStreamDown(false);
          setAlertsReady(true);
        },
        onError: () => {
          if (!active) return;
          setStreamDown(true);
          stopStream();
          scheduleRetry();
        },
      });

      Promise.all([
        nodesService.list(),
        sensorsService.list({ limit: 1000 }).catch(() => []),
        sensorTypesService.list().catch(() => []),
      ])
        .then(([nodeList, sensorList, typeList]) => {
          if (!active) return;
          setNodes(nodeList);
          setCatalog(buildCatalog(sensorList, typeList));
          setLoadState({ status: "ready", error: "" });
        })
        .catch(() => {
          if (!active) return;
          setLoadState({ status: "error", error: "No pudimos cargar los nodos." });
          scheduleRetry();
        });
    }

    connect();

    return () => {
      active = false;
      stopStream();
      clearTimeout(retryTimer);
    };
  }, [reloadKey]);

  /** Atiende todas las alertas pendientes de la categoría: una sola acción para todo el grupo. */
  async function handleGroup(group) {
    setActionError("");
    setHandling((prev) => ({ ...prev, [group.key]: true }));
    const results = await Promise.allSettled(group.unhandled.map((alert) => alertsService.handle(alert.alert_id)));
    // Lo que sí se pudo atender se refleja ya; si algo falló, la categoría sigue pendiente.
    setAlerts((prev) => results.reduce(
      (next, result) => (result.status === "fulfilled" ? applyAlert(next, result.value) : next), prev));
    if (results.some((result) => result.status === "rejected")) {
      setActionError("No pudimos marcar la alerta como atendida. Intenta de nuevo.");
    }
    setHandling((prev) => {
      const next = { ...prev };
      delete next[group.key];
      return next;
    });
  }

  function reload() {
    setLoadState({ status: "loading", error: "" });
    setAlertsReady(false);
    setReloadKey((key) => key + 1);
  }

  /** Un grupo por nodo que tiene alertas abiertas. */
  const groups = useMemo(() => {
    const nodeById = new Map(nodes.map((node) => [node.node_id, node]));
    const byNode = new Map();
    Object.values(alerts).forEach((alert) => {
      if (alert.node_id == null) return;
      const list = byNode.get(alert.node_id) ?? [];
      list.push(alert);
      byNode.set(alert.node_id, list);
    });

    return [...byNode.entries()].map(([nodeId, openAlerts]) => ({
      node: nodeById.get(nodeId) ?? {
        node_id: nodeId,
        code: "—",
        name: `Nodo ${nodeId}`,
        zone_id: null,
        ip_address: null,
      },
      openAlerts,
      // Una alerta viva por nodo y categoría hasta que se atienda.
      alertGroups: groupAlerts(openAlerts, catalog),
      status: deriveNodeStatus({ isConnected: false, openAlerts }),
    }));
  }, [alerts, nodes, catalog]);

  const counts = useMemo(() => {
    const result = Object.fromEntries(ALERT_STATUSES.map((key) => [key, 0]));
    groups.forEach((group) => {
      result[group.status] += 1;
    });
    return result;
  }, [groups]);

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    return groups
      .filter((group) => statusFilter === "all" || group.status === statusFilter)
      .filter(
        (group) =>
          !term ||
          group.node.name.toLowerCase().includes(term) ||
          group.node.code.toLowerCase().includes(term),
      )
      .sort(
        (a, b) =>
          NODE_STATUS[a.status].rank - NODE_STATUS[b.status].rank ||
          a.node.name.localeCompare(b.node.name),
      );
  }, [groups, query, statusFilter]);

  if (loadState.status === "loading" || !alertsReady) {
    return (
      <p role="status">
        {streamDown ? "Sin conexión con las alertas en vivo. Reintentando…" : "Cargando nodos…"}
      </p>
    );
  }

  if (loadState.status === "error") {
    return (
      <section className={styles.error} role="alert">
        <p>{loadState.error}</p>
        <button type="button" className={styles.retry} onClick={reload}>
          Reintentar
        </button>
      </section>
    );
  }

  return (
    <div className={styles.page}>
      {streamDown && (
        <p role="status" className={styles.notice}>
          Sin actualizaciones en vivo. Reintentando la conexión…
        </p>
      )}

      <ul className={styles.summary} aria-label="Resumen por estado">
        {ALERT_STATUSES.map((key) => (
          <li key={key} className={styles.summaryItem} data-status={key}>
            <span className={styles.summaryIcon} aria-hidden="true">{NODE_STATUS[key].icon}</span>
            <span className={styles.summaryCount}>{counts[key]}</span>
            <span>{NODE_STATUS[key].label}</span>
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

      {actionError && (
        <p role="alert" className={styles.notice}>
          {actionError}
        </p>
      )}

      {visible.length === 0 ? (
        <p className={styles.empty}>
          {groups.length === 0
            ? "No hay nodos con alertas abiertas."
            : "Ningún nodo coincide con la búsqueda o el filtro."}
        </p>
      ) : (
        <ul className={styles.grid}>
          {visible.map(({ node, status, alertGroups }) => (
            <li key={node.node_id}>
              <NodeCard
                node={node}
                status={status}
                alertGroups={alertGroups}
                handling={handling}
                onHandle={handleGroup}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default NodesPage;
