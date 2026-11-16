
import { useEffect, useState } from "react";
import styles from "./Sidebar.module.css";

const menuItems = [
  { id: "dashboard", name: "Panel principal", icon: "⌂" },
  { id: "buildings", name: "Edificios", icon: "▦" },
  { id: "zones", name: "Zonas", icon: "▱" },
  { id: "nodes", name: "Nodos sensores", icon: "◉" },
  { id: "events", name: "Eventos", icon: "⚠" },
  { id: "history", name: "Historial", icon: "◷" },
];

function Sidebar() {
  const [activePage, setActivePage] = useState("dashboard");

  useEffect(() => {
    function handleNavigation(event) {
      setActivePage(event.detail);
    }

    window.addEventListener("navigate", handleNavigation);

    return () => {
      window.removeEventListener("navigate", handleNavigation);
    };
  }, []);

  function navigate(id) {
    setActivePage(id);
    window.dispatchEvent(
      new CustomEvent("navigate", { detail: id })
    );
  }

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <h2>⌂ Sentinel Building</h2>
        <span>Monitoreo y coordinación de emergencias</span>
      </div>

      <nav className={styles.nav}>
        {menuItems.map((item) => (
          <button
            key={item.id}
            className={`${styles.link} ${
              activePage === item.id ? styles.active : ""
            }`}
            onClick={() => navigate(item.id)}
          >
            <span className={styles.icon}>{item.icon}</span>
            {item.name}
          </button>
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
