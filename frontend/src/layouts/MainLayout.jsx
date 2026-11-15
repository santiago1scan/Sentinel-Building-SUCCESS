
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

function MainLayout({ children, title, subtitle }) {
  return (
    <div className="app-container">
      <Sidebar />

      <main className="main-content">
        <Header title={title} subtitle={subtitle} />

        <div className="page-content">
          {children}
        </div>
      </main>
    </div>
  );
}

export default MainLayout;
