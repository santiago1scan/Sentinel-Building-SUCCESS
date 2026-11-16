
import { useEffect, useState } from "react";

const menuItems = [
  { id: "dashboard", name: "Panel principal", icon: "⌂" },
  { id: "buildings", name: "Edificios", icon: "▦" },
  { id: "zones", name: "Zonas", icon: "▱" },
  { id: "nodes", name: "Nodos sensores", icon: "◉" },
  { id: "events", name: "Eventos", icon: "⚠" },
  { id: "simulator", name: "Simulador", icon: "▷" },
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
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h2>⌂ Sentinel Building</h2>
        <span>Monitoreo y coordinación de emergencias</span>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <button
            key={item.id}
            className={`sidebar-link ${
              activePage === item.id ? "active" : ""
            }`}
            onClick={() => navigate(item.id)}
          >
            <span className="sidebar-icon">{item.icon}</span>
            {item.name}
          </button>
        ))}
      </nav>

      <div className="sidebar-profile">
        <strong>Administrador</strong>
        <span>admin@sentinel.local</span>
      </div>
    </aside>
  );
}

export default Sidebar;
