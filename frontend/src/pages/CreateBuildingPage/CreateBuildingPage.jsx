import { useState } from "react";
import { useNavigate } from "react-router";
import { MdApartment } from "react-icons/md";
import { buildingsService } from "../../shared/services/buildingsService";
import BuildingForm from "../../features/buildings/organisms/BuildingForm/BuildingForm";
import FloorsForm from "../../features/floors/organisms/FloorsForm/FloorsForm";
import FloorsReadOnly from "../../features/floors/organisms/FloorsReadOnly/FloorsReadOnly";
import ZoneForm from "../../features/zones/organisms/ZoneForm/ZoneForm";
import { levelLabel } from "../../features/floors/levels";
import Button from "../../shared/ui/atoms/buttons/Button";
import StatusMessage from "../../shared/ui/molecules/StatusMessage/StatusMessage";
import styles from "./CreateBuildingPage.module.css";

/**
 * Crear un edificio. Guarda en el backend. Al terminar, la columna 1 muestra el mensaje de éxito
 * y la columna 2 pasa de icono a agregar pisos del edificio recién creado. Al guardar los pisos,
 * la columna 1 pasa a mostrar esos pisos en solo lectura y la columna 2 pide elegir un piso para crear zonas.
 */
function CreateBuildingPage() {
  const navigate = useNavigate();
  const [created, setCreated] = useState(null); // { id, name }
  const [savedFloors, setSavedFloors] = useState(null); // pisos guardados, para la columna 1 en solo lectura
  const [selectedFloor, setSelectedFloor] = useState(null); // piso elegido para crear zonas

  async function handleCreate(payload) {
    const building = await buildingsService.create(payload);
    setCreated({ id: building.building_id, name: payload.name });
  }

  return (
    <div className={styles.page}>
      <div className={styles.form}>
        {savedFloors ? (
          <FloorsReadOnly
            buildingName={created.name}
            floors={savedFloors}
            selectedId={selectedFloor?.floor_id ?? null}
            onSelect={setSelectedFloor}
          />
        ) : created ? (
          <StatusMessage status="success" title="Edificio creado exitosamente">
            <p>“{created.name}” ya está registrado en el panel.</p>
            <Button variant="active" onClick={() => navigate("/panel", { replace: true })}>
              Volver al panel
            </Button>
          </StatusMessage>
        ) : (
          <BuildingForm onSubmit={handleCreate} onCancel={() => navigate("/panel")} />
        )}
      </div>

      <div className={styles.visual}>
        {savedFloors && selectedFloor ? (
          <ZoneForm
            key={selectedFloor.floor_id}
            buildingId={created.id}
            floor={selectedFloor}
            floorLabel={levelLabel(selectedFloor.level)}
            onSaveProgress={() => navigate("/panel", { replace: true })}
          />
        ) : savedFloors ? (
          <StatusMessage status="success" title="Selecciona un piso para crear zonas" />
        ) : created ? (
          <FloorsForm
            buildingId={created.id}
            buildingName={created.name}
            onSaved={setSavedFloors}
          />
        ) : (
          <MdApartment className={styles.icon} aria-hidden="true" />
        )}
      </div>
    </div>
  );
}

export default CreateBuildingPage;
