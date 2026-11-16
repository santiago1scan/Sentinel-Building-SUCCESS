
import { useState } from "react";

function Nodes() {
  const [nodes, setNodes] = useState([
    {
      id: 1,
      code: "NODE-001",
      name: "Nodo sala de servidores",
      building: "Edificio principal",
      zone: "Laboratorio",
      connection: "Conectado",
      status: "Aprobado",
    },
    {
      id: 2,
      code: "NODE-002",
      name: "Nodo entrada",
      building: "Edificio principal",
      zone: "Entrada principal",
      connection: "Desconectado",
      status: "Aprobado",
    },
  ]);

  const [pending, setPending] = useState([
    {
      id: 101,
      code: "NODE-003",
      name: "Nodo pasillo norte",
      requestedAt: "08:45",
    },
    {
      id: 102,
      code: "NODE-004",
      name: "Nodo laboratorio",
      requestedAt: "08:50",
    },
  ]);

  const [selectedZones, setSelectedZones] = useState({});
  const [errors, setErrors] = useState({});

  const zones = [
    "Laboratorio",
    "Entrada principal",
    "Archivo",
  ];

  function handleZoneChange(requestId, zone) {
    setSelectedZones((previous) => ({
      ...previous,
      [requestId]: zone,
    }));

    setErrors((previous) => ({
      ...previous,
      [requestId]: "",
    }));
  }

  function approveRequest(request) {
    const selectedZone = selectedZones[request.id];

    // Validar que se haya seleccionado una zona
    if (!selectedZone) {
      setErrors((previous) => ({
        ...previous,
        [request.id]: "Debes seleccionar una zona antes de aprobar.",
      }));
      return;
    }

    // Validar que el identificador no esté registrado
    const duplicateCode = nodes.some(
      (node) =>
        node.code.trim().toLowerCase() ===
        request.code.trim().toLowerCase()
    );

    if (duplicateCode) {
      setErrors((previous) => ({
        ...previous,
        [request.id]: "Ya existe un nodo registrado con este identificador.",
      }));
      return;
    }

    // Crear el nodo y asociarlo a la zona seleccionada
    const newNode = {
      id: Date.now(),
      code: request.code,
      name: request.name,
      building: "Edificio principal",
      zone: selectedZone,
      connection: "Pendiente de conexión",
      status: "Aprobado",
    };

    setNodes((previous) => [...previous, newNode]);

    setPending((previous) =>
      previous.filter((item) => item.id !== request.id)
    );

    setSelectedZones((previous) => {
      const updated = { ...previous };
      delete updated[request.id];
      return updated;
    });

    setErrors((previous) => {
      const updated = { ...previous };
      delete updated[request.id];
      return updated;
    });
  }

  function rejectRequest(requestId) {
    const confirmed = window.confirm(
      "¿Estás seguro de rechazar esta solicitud?"
    );

    if (!confirmed) return;

    setPending((previous) =>
      previous.filter((item) => item.id !== requestId)
    );

    setSelectedZones((previous) => {
      const updated = { ...previous };
      delete updated[requestId];
      return updated;
    });

    setErrors((previous) => {
      const updated = { ...previous };
      delete updated[requestId];
      return updated;
    });
  }

  return (
    <div className="nodes-page">

      {/* NODOS REGISTRADOS */}

      <div className="card">
        <div className="card-heading">
          <h2>Nodos sensores registrados</h2>
          <span className="nodes-counter">
            {nodes.length} nodos
          </span>
        </div>

        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Edificio</th>
              <th>Zona</th>
              <th>Conexión</th>
              <th>Registro</th>
            </tr>
          </thead>

          <tbody>
            {nodes.map((node) => (
              <tr key={node.id}>
                <td>{node.code}</td>
                <td>{node.name}</td>
                <td>{node.building}</td>
                <td>{node.zone}</td>
                <td>
                  <span
                    className={`node-status ${
                      node.connection === "Conectado"
                        ? "online"
                        : node.connection === "Desconectado"
                        ? "offline"
                        : "waiting"
                    }`}
                  >
                    {node.connection}
                  </span>
                </td>
                <td>
                  <span className="building-status">
                    {node.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* SOLICITUDES PENDIENTES */}

      <div className="card pending-card">
        <div className="card-heading">
          <h2>Solicitudes pendientes</h2>
          <span className="pending-counter">
            {pending.length} pendientes
          </span>
        </div>

        {pending.length === 0 ? (
          <div className="empty-state">
            No hay solicitudes pendientes de aprobación.
          </div>
        ) : (
          pending.map((request) => (
            <div className="pending-request" key={request.id}>

              <div className="request-info">
                <strong>
                  {request.code} · {request.name}
                </strong>

                <span>
                  Edificio principal · Solicitud recibida:{" "}
                  {request.requestedAt}
                </span>

                <span className="request-label">
                  Pendiente de aprobación
                </span>
              </div>

              <div className="request-actions">

                <select
                  value={selectedZones[request.id] || ""}
                  onChange={(e) =>
                    handleZoneChange(request.id, e.target.value)
                  }
                >
                  <option value="">Seleccionar zona</option>

                  {zones.map((zone) => (
                    <option key={zone} value={zone}>
                      {zone}
                    </option>
                  ))}
                </select>

                <button
                  className="btn primary"
                  onClick={() => approveRequest(request)}
                >
                  Aprobar
                </button>

                <button
                  className="btn danger"
                  onClick={() => rejectRequest(request.id)}
                >
                  Rechazar
                </button>

              </div>

              {errors[request.id] && (
                <div className="form-error" role="alert">
                  {errors[request.id]}
                </div>
              )}

            </div>
          ))
        )}
      </div>

    </div>
  );
}

export default Nodes;
