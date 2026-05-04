import { useEffect, useState } from "react";
import api from "@/api/client";
import { useApi } from "@/hooks/useApi";
import ConfigPreviewModal from "@/components/ConfigPreviewModal";

export default function ModelsPage() {
  const [models, setModels] = useState([]);
  const [config, setConfig] = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({});
  const [previewOpen, setPreviewOpen] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [previewConfig, setPreviewConfig] = useState(null);
  const [error, setError] = useState(null);
  const { execute } = useApi();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [modelsRes, configRes] = await Promise.all([api.get("/models"), api.get("/config")]);
        setModels(modelsRes.data || []);
        setConfig(configRes.data || {});
      } catch {
        setError("‼️ Backend unavailable");
      }
    };
    fetchData();
  }, []);

  const selectModel = (model) => {
    setSelected(model);
    if (config?.models?.[model.name]) {
      setForm({ ...config.models[model.name] });
    } else {
      setForm({});
    }
  };

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleAddConfig = () => {
    setConfig((prev) => ({
      ...prev,
      models: { ...(prev?.models || {}), [selected.name]: { ...form } },
    }));
    setForm({});
  };

  const openPreview = async () => {
    const previewConfig = {
      ...(config || {}),
      models: {
        ...(config?.models || {}),
        [selected.name]: form,
      },
    };
    setPreviewConfig(previewConfig);
    setPreviewOpen(true);
    try {
      const res = await execute(api.post("/config/validate", previewConfig));
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

  if (error) return (
    <div className="page">
      <div className="error-banner">{error}</div>
    </div>
  );

  return (
    <div className="models-layout">
      <div className="model-list">
        {models.map((m) => {
          const isConfigured = config?.models?.[m.name];
          const isSelected = selected?.name === m.name;
          return (
            <div
              key={m.name}
              onClick={() => selectModel(m)}
              className={`model-item${isSelected ? " selected" : ""}`}
            >
              <span className={`model-dot${isSelected ? " selected" : isConfigured ? " configured" : ""}`} />
              {m.name}
            </div>
          );
        })}
      </div>

      {selected && (
        <div className="model-detail">
          <h3>{selected.name}</h3>
          <div className="meta-row">
            <div><strong>Size:</strong> {selected.size}</div>
            <div><strong>Quant:</strong> {selected.quant}</div>
          </div>

          <h4>llama-server options</h4>
          <div className="form-list">
            {Object.keys(form || {}).map((key) => (
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
            <button type="button" onClick={handleAddConfig}>Add to Config</button>
            <button type="button" onClick={openPreview} disabled={Object.keys(form).length === 0}>Validate & Preview</button>
          </div>

          {previewOpen && (
            <ConfigPreviewModal
              config={config}
              newConfig={previewConfig}
              validationResult={validationResult}
              onClose={() => setPreviewOpen(false)}
              title={`Preview — ${selected.name}`}
            />
          )}
        </div>
      )}

      {!selected && <div className="model-detail model-empty">Select a model</div>}
    </div>
  );
}


