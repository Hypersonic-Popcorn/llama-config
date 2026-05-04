import { useEffect, useState } from "react";
import api from "@/api/client";

export default function DockerPage() {
  const [status, setStatus] = useState(null);
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await api.get("/docker/status");
        setStatus(res.data || "...");
        setFetchError(null);
      } catch {
        setFetchError("‼️ Backend unavailable — docker status unavailable");
      }
    };
    fetchStatus();
  }, []);

  const statusClass = status === "RUNNING" ? "status-running" : status === "STOPPED" ? "status-stopped" : "status-unknown";

  return (
    <div className="page">
      {fetchError && (
        <div className="error-banner">{fetchError}</div>
      )}
      <div className="status-row">
        <strong>Container Status:</strong>{" "}
        <span className={statusClass}>{status || "..."}</span>
      </div>
    </div>
  );
}
