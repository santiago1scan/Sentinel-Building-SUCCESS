
function Header({ title, subtitle }) {
  return (
    <header className="header">
      <div className="header-title">
        <h1>{title || "Panel principal"}</h1>
        <p>{subtitle || "Monitoreo y coordinación de emergencias"}</p>
      </div>

      <div className="system-pill">
        <span className="status-dot"></span>
        Sistema operativo
      </div>
    </header>
  );
}

export default Header;
