import { Link } from "react-router";
import PublicHeader from "../../shared/ui/organisms/PublicHeader";
import styles from "./HomePage.module.css";

const points = [
  "Sensores agrupados por edificio, piso y zona.",
  "Alertas con seguimiento hasta que alguien las atiende.",
  "Cada nodo se aprueba antes de conectarse a la red.",
];

/** Pantalla pública de presentación del proyecto. */
function HomePage() {
  return (
    <div className={styles.page}>
      <PublicHeader action={{ to: "/login", label: "Iniciar sesión" }} />

      <main className={styles.hero}>
        <p className={styles.kicker}>Monitoreo de edificios</p>
        <h1 className={styles.title}>Sabe qué pasa en cada piso, en tiempo real.</h1>
        <p className={styles.lead}>
          Sentinel Building conecta los sensores de cada edificio a un solo panel.
          Detecta condiciones fuera de rango, lleva cada alerta hasta que alguien la
          atiende y deja registro de quién lo hizo.
        </p>

        <ul className={styles.points}>
          {points.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>

        <Link to="/login" className={styles.cta}>
          Iniciar sesión
        </Link>
      </main>
    </div>
  );
}

export default HomePage;
