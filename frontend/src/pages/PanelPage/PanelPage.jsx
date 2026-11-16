import BuildingsSection from "../../features/buildings/organisms/BuildingsSection/BuildingsSection";
import NodesPage from "../NodesPage/NodesPage";
import styles from "./PanelPage.module.css";

/** Panel principal: primero las construcciones y debajo los nodos con alertas. */
function PanelPage() {
  return (
    <div className={styles.page}>
      <NodesPage />
      <BuildingsSection />
    </div>
  );
}

export default PanelPage;
