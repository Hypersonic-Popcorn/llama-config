import { useEffect, useState } from "react";
import api from "@/api/client";

export default function LogsPage() {
  const [containerLogs, setContainerLogs] = useState("");
  const [isAutoRefresh, setIsAutoRefresh] = useState(false);
  const [delay, setDelay] = useState(5000);
  const [error, setError] = useState(null);

  const fetchLogs = async () => {
    try {
      const res = await api.get("/docker/logs");
      setContainerLogs(res.data?.logs?.join("\n") || "");
      setError(null);
    } catch {
      setError("‼️ Backend unavailable");
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get("/docker/logs");
        setContainerLogs(res.data?.logs?.join("\n") || "");
        setError(null);
      } catch {
        setError("‼️ Backend unavailable");
      }
    })();
  }, []);

  useEffect(() => {
    let intervalId = null;
    if (isAutoRefresh) {
      intervalId = setInterval(fetchLogs, delay);
      return () => clearInterval(intervalId);
    }
  }, [isAutoRefresh, delay]);

  return (
    <div className="page">
      {error && (
        <div className="error-banner">{error}</div>
      )}
      <div className="controls-row">
        <label>
          <input
            type="checkbox"
            checked={isAutoRefresh}
            onChange={(e) => setIsAutoRefresh(e.target.checked)}
          />
          Auto-refresh
        </label>

        <label>
          Delay (ms):
          <select value={delay} onChange={(e) => setDelay(Number(e.target.value))}>
            <option value={5000}>5s</option>
            <option value={10000}>10s</option>
            <option value={30000}>30s</option>
            <option value={60000}>60s</option>
          </select>
        </label>

        <button type="button" onClick={fetchLogs}>Refresh</button>
      </div>

      <div className="log-panel">
          <strong>Container Logs</strong>
          <pre className="log-output">
            {containerLogs || "(no logs)"}
          </pre>
        </div>
    </div>
  );
}
