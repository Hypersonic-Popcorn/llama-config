import { useState } from "react";
import api from "@/api/client";
import { useApi } from "@/hooks/useApi";
import { useDarkMode } from "@/hooks/useDarkMode";

export default function TopBar({ title, isStale, style, onRestartSuccess }) {
  const [message, setMessage] = useState("");
  const { darkMode, setDarkMode } = useDarkMode();
  const { loading, error, execute } = useApi();

  const handleStart = async () => {
    setMessage("Starting...");
    await execute(api.post("/docker/start"));
    setMessage("Started.");
  };

  const handleStop = async () => {
    setMessage("Stopping...");
    await execute(api.post("/docker/stop"));
    setMessage("Stopped.");
  };

  const handleRestart = async () => {
    setMessage("Restarting...");
    await execute(api.post("/docker/restart"));
    setMessage("Restarted.");
    onRestartSuccess();
  };

  return (
    <header className={`topbar${isStale ? " stale" : ""}`} style={style}>
      <div className="topbar-title">{title}</div>
      <div className="topbar-actions">
        {isStale && (
          <span className="topbar-status topbar-status--stale">
            Stale config
          </span>
        )}
        {loading && (
          <span className="topbar-status topbar-status--loading">
            {message || "Loading..."}
          </span>
        )}
        {error && (
          <span className="topbar-status topbar-status--error">
            {error.message}
          </span>
        )}
        {!loading && message && (
          <span className="topbar-status topbar-status--success">
            {message}
          </span>
        )}
        <button type="button" onClick={handleStart} disabled={loading} title="Start container" className="btn btn-icon" aria-label="Start">▶</button>
        <button type="button" onClick={handleStop} disabled={loading} title="Stop container" className="btn btn-icon" aria-label="Stop">⏹</button>
        <button
          type="button"
          onClick={handleRestart}
          disabled={loading}
          className={`btn ${isStale ? "btn-stale" : "btn-primary"}`}
          title={isStale ? "Restart (stale config)" : "Restart container"}
          aria-label="Restart"
        >
          ↻
        </button>
        <button
          type="button"
          onClick={() => setDarkMode(!darkMode)}
          className="btn btn-icon"
          title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          aria-label="Toggle dark mode"
        >
          {darkMode ? "🌙" : "☀️"}
        </button>
      </div>
    </header>
  );
}
