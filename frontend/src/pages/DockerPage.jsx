import { useEffect, useState } from "react";
import api from "@/api/client";
import { useStaleConfig } from "@/hooks/useStaleConfig";

const ERROR_PATTERN = /ERROR|Exception|Traceback/;
const MAX_ERROR_LINES = 100;

export default function DockerPage() {
  const [status, setStatus] = useState(null);
  const [fetchError, setFetchError] = useState(null);
  const [errorLines, setErrorLines] = useState([]);
  const { isStale } = useStaleConfig();

  const fetchData = async () => {
    try {
      const statusRes = await api.get("/docker/status");
      const currentStatus = statusRes.data;
      setStatus(currentStatus);

      if (currentStatus === "STOPPED") {
        const logsRes = await api.get("/docker/logs");
        const logs = logsRes.data?.logs || [];
        const errors = logs
          .filter((line) => ERROR_PATTERN.test(line))
          .slice(-MAX_ERROR_LINES);
        setErrorLines(errors);
      } else {
        setErrorLines([]);
      }

      setFetchError(null);
    } catch {
      setFetchError("‼️ Backend unavailable — docker status unavailable");
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const message = status === "RUNNING"
    ? (isStale ? "Running with stale config" : "Running with current config")
    : "Stopped";

  const statusClass = status === "RUNNING"
    ? (isStale ? "status-stale" : "status-running")
    : errorLines.length > 0
      ? "status-error"
      : "status-stopped";

  return (
    <div className="page">
      {fetchError && (
        <div className="error-banner">{fetchError}</div>
      )}
      <div className="status-row">
        <strong>Container Status:</strong>{" "}
        <span className={statusClass}>{message}</span>
      </div>

      <button
        type="button"
        onClick={fetchData}
        className="btn"
        style={{ marginTop: "16px" }}
      >
        Refresh
      </button>

      {errorLines.length > 0 && (
        <div className="error-lines">
          <strong>Error Lines</strong>
          <pre className="error-output">
            {errorLines.join("\n")}
          </pre>
        </div>
      )}
    </div>
  );
}
