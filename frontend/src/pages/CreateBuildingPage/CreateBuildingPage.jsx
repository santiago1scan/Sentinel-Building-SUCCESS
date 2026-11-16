import { useState } from "react";
import { useNavigate } from "react-router";
import { MdApartment } from "react-icons/md";
import { buildingsService } from "../../shared/services/buildingsService";
import BuildingForm from "../../features/buildings/organisms/BuildingForm/BuildingForm";
import FloorsForm from "../../features/buildings/organisms/FloorsForm/FloorsForm";
import Button from "../../shared/ui/atoms/buttons/Button";
import StatusMessage from "../../shared/ui/molecules/StatusMessage/StatusMessage";
import styles from "./CreateBuildingPage.module.css";

/**
 * Crear un edificio. Guarda en el backend. Al terminar, la columna 1 muestra el mensaje de éxito
 * y la columna 2 pasa de icono a agregar pisos del edificio recién creado.
 */
function CreateBuildingPage() {
  const navigate = useNavigate();
  const [created, setCreated] = useState(null); // { id, name }

  async function handleCreate(payload) {
    const building = await buildingsService.create(payload);
    setCreated({ id: building.building_id, name: payload.name });
  }

  return (
    <div className={styles.page}>
      <div className={styles.form}>
        {created ? (
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
        {created ? (
          <FloorsForm buildingId={created.id} buildingName={created.name} />
        ) : (
          <MdApartment className={styles.icon} aria-hidden="true" />
        )}
      </div>
    </div>
  );
}

export default CreateBuildingPage;
