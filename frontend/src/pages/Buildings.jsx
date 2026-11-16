
import { useState } from "react";

function Buildings() {
  const [buildings, setBuildings] = useState([
    {
      id: 1,
      code: "SB-001",
      name: "Edificio principal",
      address: "Campus central",
      zones: 8,
      status: "Activo",
    },
  ]);

  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    code: "",
    name: "",
    address: "",
  });

  const filteredBuildings = buildings.filter((building) =>
    `${building.code} ${building.name} ${building.address}`
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

  function handleSubmit(e) {
    e.preventDefault();

    const code = form.code.trim();
    const name = form.name.trim();
    const address = form.address.trim();

    if (!code || !name || !address) {
      setError("Todos los campos son obligatorios.");
      return;
    }

    const duplicateCode = buildings.some(
      (building) =>
        building.code.toLowerCase() === code.toLowerCase()
    );

    if (duplicateCode) {
      setError("Ya existe un edificio con ese código.");
      return;
    }

    const duplicateName = buildings.some(
      (building) =>
        building.name.toLowerCase() === name.toLowerCase()
    );

    if (duplicateName) {
      setError("Ya existe un edificio con ese nombre.");
      return;
    }

    const newBuilding = {
      id: Date.now(),
      code,
      name,
      address,
      zones: 0,
      status: "Activo",
    };

    setBuildings((previous) => [...previous, newBuilding]);

    setForm({
      code: "",
      name: "",
      address: "",
    });

    setError("");
    setShowModal(false);
  }

  function openModal() {
    setError("");
    setShowModal(true);
  }

  function closeModal() {
    setError("");
    setShowModal(false);
  }

  return (
    <div className="buildings-page">
      <div className="card">

        <div className="card-heading">
          <h2>Edificios registrados</h2>

          <button
            className="btn primary"
            onClick={openModal}
          >
            + Nuevo edificio
          </button>
        </div>

        <input
          className="search-input"
          type="text"
          placeholder="Buscar edificio..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Dirección</th>
              <th>Zonas</th>
              <th>Estado</th>
            </tr>
          </thead>

          <tbody>
            {filteredBuildings.map((building) => (
              <tr key={building.id}>
                <td>{building.code}</td>
                <td>{building.name}</td>
                <td>{building.address}</td>
                <td>{building.zones}</td>
                <td>
                  <span className="building-status">
                    {building.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredBuildings.length === 0 && (
          <div className="empty-state">
            No se encontraron edificios.
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-card">

            <div className="card-heading">
              <h2>Registrar edificio</h2>

              <button
                className="close-button"
                onClick={closeModal}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit}>

              <label>
                Código del edificio
                <input
                  name="code"
                  value={form.code}
                  onChange={handleChange}
                  placeholder="Ej. SB-002"
                  required
                />
              </label>

              <label>
                Nombre del edificio
                <input
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Nombre del edificio"
                  required
                />
              </label>

              <label>
                Dirección
                <input
                  name="address"
                  value={form.address}
                  onChange={handleChange}
                  placeholder="Dirección o ubicación"
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
                  Guardar edificio
                </button>
              </div>

            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Buildings;
