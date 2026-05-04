import { HashRouter, Routes, Route, useLocation } from "react-router-dom";
import Sidebar from "@/components/Sidebar.jsx";
import TopBar from "@/components/TopBar.jsx";
import ConfigPage from "@/pages/ConfigPage.jsx";
import ModelsPage from "@/pages/ModelsPage.jsx";
import DockerPage from "@/pages/DockerPage.jsx";
import LogsPage from "@/pages/LogsPage.jsx";
import { useStaleConfig } from "@/hooks/useStaleConfig.js";
import { DarkModeProvider } from "@/hooks/useDarkMode.jsx";
import "@/index.css";

const PAGE_TITLES = {
  "/": "llama-config",
  "/config": "Config",
  "/models": "Models",
  "/docker": "Docker",
  "/logs": "Logs",
};

function Layout() {
  const location = useLocation();
  const { isStale, markFresh } = useStaleConfig();

  return (
    <div className="app-layout">
      <TopBar
        title={PAGE_TITLES[location.pathname] || "llama-config"}
        isStale={isStale}
        onConfigSave={() => window.location.hash = "#/config"}
        onRestartSuccess={markFresh}
      />
      <div className="app-body">
        <Sidebar title="llama-config" />
        <div className="app-content">
          <Routes>
            <Route path="/" element={
              <div className="welcome-page">
                <h2>Welcome</h2>
                <p>Select a page from the sidebar.</p>
              </div>
            } />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="/models" element={<ModelsPage />} />
            <Route path="/docker" element={<DockerPage />} />
            <Route path="/logs" element={<LogsPage />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <DarkModeProvider>
      <HashRouter>
        <Layout />
      </HashRouter>
    </DarkModeProvider>
  );
}
