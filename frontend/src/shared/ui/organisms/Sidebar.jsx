import { NavLink } from "react-router";
import styles from "./Sidebar.module.css";

const menuItems = [
  { to: "/panel", name: "Panel principal", icon: "⌂" },
  { to: "/edificios", name: "Edificios", icon: "▦" },
  { to: "/zonas", name: "Zonas", icon: "▱" },
  { to: "/nodos", name: "Nodos sensores", icon: "◉" },
  { to: "/eventos", name: "Eventos", icon: "⚠" },
  { to: "/historial", name: "Historial", icon: "◷" },
];

function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <h2>⌂ Sentinel Building</h2>
        <span>Monitoreo y coordinación de emergencias</span>
      </div>

      <nav className={styles.nav} aria-label="Principal">
        {menuItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/panel"}
            className={({ isActive }) =>
              `${styles.link} ${isActive ? styles.active : ""}`
            }
          >
            <span className={styles.icon} aria-hidden="true">{item.icon}</span>
            {item.name}
          </NavLink>
        ))}
      </nav>

      <div className={styles.profile}>
        <strong>Administrador</strong>
        <span>admin@sentinel.local</span>
      </div>
    </aside>
  );
}

export default Sidebar;
