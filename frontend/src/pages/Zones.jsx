
import { useState } from "react";

function Zones() {
  const [zones, setZones] = useState([
    {
      id: 1,
      name: "Laboratorio",
      building: "Edificio principal",
      floor: 2,
      nodes: 3,
      status: "Monitoreada",
    },
    {
      id: 2,
      name: "Entrada principal",
      building: "Edificio principal",
      floor: 1,
      nodes: 2,
      status: "Monitoreada",
    },
    {
      id: 3,
      name: "Archivo",
      building: "Edificio principal",
      floor: 3,
      nodes: 1,
      status: "Monitoreada",
    },
  ]);

  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    name: "",
    building: "Edificio principal",
    floor: "",
  });

  const filteredZones = zones.filter((zone) =>
    `${zone.name} ${zone.building} ${zone.floor}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  function handleChange(e) {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });

    setError("");
  }

  function openModal() {
    setError("");
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setError("");
    setForm({
      name: "",
      building: "Edificio principal",
      floor: "",
    });
  }

  function handleSubmit(e) {
    e.preventDefault();

    const name = form.name.trim();

    if (!name || !form.floor.trim()) {
      setError("Completa todos los campos obligatorios.");
      return;
    }

    const exists = zones.some(
      (zone) =>
        zone.name.trim().toLowerCase() === name.toLowerCase() &&
        zone.building.toLowerCase() === form.building.toLowerCase()
    );

    if (exists) {
      setError("Ya existe una zona con ese nombre en este edificio.");
      return;
    }

    const newZone = {
      id: Date.now(),
      name,
      building: form.building,
      floor: Number(form.floor),
      nodes: 0,
      status: "Monitoreada",
    };

    setZones((previousZones) => [...previousZones, newZone]);

    closeModal();
  }

  return (
    <div className="zones-page">
      <div className="card">
        <div className="card-heading">
          <h2>Zonas y pisos</h2>

          <button
            className="btn primary"
            onClick={openModal}
          >
            + Nueva zona
          </button>
        </div>

        <input
          className="search-input"
          type="text"
          placeholder="Buscar zona..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <table>
          <thead>
            <tr>
              <th>Zona</th>
              <th>Edificio</th>
              <th>Piso</th>
              <th>Nodos</th>
              <th>Estado</th>
            </tr>
          </thead>

          <tbody>
            {filteredZones.map((zone) => (
              <tr key={zone.id}>
                <td>{zone.name}</td>
                <td>{zone.building}</td>
                <td>{zone.floor}</td>
                <td>{zone.nodes}</td>
                <td>
                  <span className="building-status">
                    {zone.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredZones.length === 0 && (
          <div className="empty-state">
            No se encontraron zonas.
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="card-heading">
              <h2>Registrar nueva zona</h2>

              <button
                className="close-button"
                onClick={closeModal}
                type="button"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <label>
                Nombre de la zona
                <input
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Ej. Laboratorio"
                  required
                />
              </label>

              <label>
                Edificio
                <select
                  name="building"
                  value={form.building}
                  onChange={handleChange}
                  required
                >
                  <option value="Edificio principal">
                    Edificio principal
                  </option>
                </select>
              </label>

              <label>
                Número de piso
                <input
                  type="number"
                  name="floor"
                  value={form.floor}
                  onChange={handleChange}
                  placeholder="Ej. 2"
                  min="0"
                  step="1"
                  required
                />
              </label>

              {error && (
                <div className="form-error" role="alert">
                  {error}
                </div>
              )}

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn secondary"
                  onClick={closeModal}
                >
                  Cancelar
                </button>

                <button
                  type="submit"
                  className="btn primary"
                >
                  Guardar zona
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Zones;
