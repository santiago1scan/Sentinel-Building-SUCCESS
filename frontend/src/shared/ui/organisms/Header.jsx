import styles from "./Header.module.css";

function Header({ title, subtitle }) {
  return (
    <header className={styles.header}>
      <div className={styles.title}>
        <h1>{title || "Panel principal"}</h1>
        <p>{subtitle || "Monitoreo y coordinación de emergencias"}</p>
      </div>

      <div className={styles.pill}>
        <span className={styles.dot}></span>
        Sistema operativo
      </div>
    </header>
  );
}

export default Header;
