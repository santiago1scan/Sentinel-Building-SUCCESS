
import Sidebar from "../organisms/Sidebar";
import Header from "../organisms/Header";
import styles from "./MainLayout.module.css";

function MainLayout({ children, title, subtitle }) {
  return (
    <div className={styles.appContainer}>
      <Sidebar />

      <main className={styles.mainContent}>
        <Header title={title} subtitle={subtitle} />

        <div className={styles.pageContent}>
          {children}
        </div>
      </main>
    </div>
  );
}

export default MainLayout;
