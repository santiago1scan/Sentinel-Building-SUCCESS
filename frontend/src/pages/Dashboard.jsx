
const events = [
  {
    name: "Temperatura alta",
    zone: "Piso 2 - Laboratorio",
    level: "Crítico",
    time: "08:42",
    status: "Activo",
  },
  {
    name: "Movimiento detectado",
    zone: "Piso 1 - Entrada",
    level: "Medio",
    time: "08:35",
    status: "En revisión",
  },
  {
    name: "Humo detectado",
    zone: "Piso 3 - Archivo",
    level: "Alto",
    time: "08:21",
    status: "Activo",
  },
];

function Dashboard() {
  return (
    <div className="dashboard">

      {/* Indicadores principales */}
      <section className="stats-grid">

        <div className="card stat-card">
          <div className="stat-icon red">⚠</div>
          <div>
            <small>Eventos activos</small>
            <strong>3</strong>
          </div>
        </div>

        <div className="card stat-card">
          <div className="stat-icon green">⌁</div>
          <div>
            <small>Nodos conectados</small>
            <strong>18 / 20</strong>
          </div>
        </div>

        <div className="card stat-card">
          <div className="stat-icon blue">▱</div>
          <div>
            <small>Zonas monitoreadas</small>
            <strong>8</strong>
          </div>
        </div>

        <div className="card stat-card">
          <div className="stat-icon amber">⟳</div>
          <div>
            <small>Eventos por sincronizar</small>
            <strong>12</strong>
          </div>
        </div>

      </section>

      {/* Eventos recientes y conexiones */}
      <section className="dashboard-columns">

        <div className="card">
          <div className="card-heading">
            <h2>Eventos recientes</h2>
            <button className="btn secondary">
              Ver todos →
            </button>
          </div>

          <table>
            <thead>
              <tr>
                <th>Evento</th>
                <th>Zona</th>
                <th>Nivel</th>
                <th>Hora</th>
                <th>Estado</th>
              </tr>
            </thead>

            <tbody>
              {events.map((event, index) => (
                <tr key={index}>
                  <td>{event.name}</td>
                  <td>{event.zone}</td>
                  <td>{event.level}</td>
                  <td>{event.time}</td>
                  <td>{event.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-heading">
            <h2>Estado de conexión</h2>
          </div>

          <div className="connection-grid">
            <div className="connection-node">
              <strong>▤</strong>
              Servidor central
              <span className="connected">● Conectado</span>
            </div>

            <div className="connection-node">
              <strong>◉</strong>
              Broker MQTT
              <span className="connected">● Conectado</span>
            </div>

            <div className="connection-node">
              <strong>⌁</strong>
              Nodo SB-001
              <span className="connected">● Conectado</span>
            </div>

            <div className="connection-node disconnected">
              <strong>⌁</strong>
              Nodo SB-002
              <span>● Desconectado</span>
            </div>
          </div>
        </div>

      </section>

      {/* Estado de zonas */}
      <section className="card zones-card">
        <h2>Estado por zonas</h2>

        {[
          { name: "Piso 1", value: 100 },
          { name: "Piso 2", value: 78 },
          { name: "Piso 3", value: 100 },
        ].map((zone) => (
          <div className="zone-progress" key={zone.name}>
            <strong>{zone.name}</strong>

            <div className="progress-track">
              <div
                className={`progress-fill ${
                  zone.value < 100 ? "warning" : ""
                }`}
                style={{ width: `${zone.value}%` }}
              />
            </div>

            <span>{zone.value}%</span>
          </div>
        ))}
      </section>

      <div className="dashboard-notice">
        Los datos locales se sincronizarán automáticamente cuando
        se restablezca la conexión.
      </div>

    </div>
  );
}

export default Dashboard;
