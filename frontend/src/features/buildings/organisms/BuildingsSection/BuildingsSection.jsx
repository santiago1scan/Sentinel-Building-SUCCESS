import { useEffect, useState } from "react";
import { buildingsService } from "../../../../shared/services/buildingsService";
import BuildingCard from "../../../../shared/ui/molecules/buildings/BuildingCard";
import Button from "../../../../shared/ui/atoms/buttons/Button";
import { useNavigate } from "react-router";
import styles from "./BuildingsSection.module.css";

/** Sección de edificios del panel: lista de tarjetas cargada desde consulta. */
function BuildingsSection() {
  const navigate = useNavigate();
  const [state, setState] = useState({ status: "loading", items: [] });

  useEffect(() => {
    let active = true;
    buildingsService
      .list()
      .then((items) => {
        if (active) setState({ status: "ready", items });
      })
      .catch(() => {
        if (active) setState({ status: "error", items: [] });
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className={styles.section} aria-labelledby="buildings-title">
      <header className={styles.header}>
        <h2 id="buildings-title" className={styles.title}>Edificios</h2>
        <Button variant="active" onClick={() => navigate("/panel/builders/create")}>
          Agregar edificio
        </Button>
      </header>

      {state.status === "loading" && <p role="status">Cargando edificios…</p>}

      {state.status === "error" && (
        <p role="alert" className={styles.error}>No pudimos cargar los edificios.</p>
      )}

      {state.status === "ready" && state.items.length === 0 && (
        <p className={styles.empty}>Aún no hay edificios registrados.</p>
      )}

      {state.status === "ready" && state.items.length > 0 && (
        <ul className={styles.grid}>
          {state.items.map((building) => (
            <li key={building.building_id}>
              <BuildingCard
                building={building}
                onOpen={(item) => navigate(`/panel/builders/${item.building_id}`)}
              >
              </BuildingCard>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default BuildingsSection;
