import { useEffect, useState } from "react";
import api from "@/api/client";
import { useApi } from "@/hooks/useApi";
import ConfigPreviewModal from "@/components/ConfigPreviewModal";

export default function ConfigPage() {
  const [config, setConfig] = useState(null);
  const [form, setForm] = useState({});
  const [previewOpen, setPreviewOpen] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [error, setError] = useState(null);
  const { loading: apiLoading, error: apiError, execute } = useApi();

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await api.get("/config");
        setConfig(res.data);
        setForm(res.data);
      } catch {
        setError("‼️ Backend unavailable");
      }
    };
    fetchConfig();
  }, []);

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const openPreview = async () => {
    setPreviewOpen(true);
    try {
      const res = await execute(api.post("/config/validate", form));
      setValidationResult(res.data);
    } catch (err) {
      const errData = err.response?.data;
      if (errData && 'valid' in errData) {
        setValidationResult(errData);
      } else {
        setValidationResult({ error: errData || "Validation failed" });
      }
    }
  };

  const handleApply = async () => {
    try {
      const res = await api.post("/config", form);
      if (res.data?.valid) {
        setConfig(form);
        setPreviewOpen(false);
      } else {
        setValidationResult(res.data);
      }
    } catch (err) {
      setValidationResult({ error: err.response?.data || "Apply failed" });
    }
  };

  if (!config && !error) return <div className="page">Loading config...</div>;
  if (error) return (
    <div className="page">
      <div className="error-banner">{error}</div>
    </div>
  );

  return (
    <div className="page">
      <div className="form-list">
        {Object.keys(config).map((key) => (
          <label key={key} className="form-field">
            <strong>{key}</strong>
            <input
              value={form[key] ?? ""}
              onChange={(e) => handleChange(key, e.target.value)}
            />
          </label>
        ))}
      </div>

      <div className="form-actions">
        <button type="button" onClick={openPreview}>Validate & Preview</button>
      </div>

      {apiLoading && <div className="loading-text">Loading...</div>}
      {apiError && <div className="error-text">Error: {apiError.message}</div>}

      {previewOpen && (
        <ConfigPreviewModal
          config={config}
          newConfig={form}
          validationResult={validationResult}
          onClose={() => setPreviewOpen(false)}
          onApply={handleApply}
        />
      )}
    </div>
  );
}
