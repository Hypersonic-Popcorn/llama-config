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
        setError("Backend unavailable");
      }
    };
    fetchData();
  }, []);

  const selectModel = (model) => {
    setSelected(model);
    setForm({ ...(config?.models?.[model.name] || {}) });
  };

  const handleToggle = (model) => {
    setConfig((prev) => {
      const models = { ...(prev?.models || {}) };
      if (models[model.name]) {
        delete models[model.name];
      } else {
        models[model.name] = {};
      }
      return { ...prev, models };
    });
  };

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const openPreview = async () => {
    const newConfig = {
      ...(config || {}),
      models: { ...(config?.models || {}) },
    };
    if (form && Object.keys(form).length > 0 && selected) {
      const existing = newConfig.models[selected.name];
      if (existing) {
        Object.assign(existing, form);
      } else {
        newConfig.models[selected.name] = { ...form };
      }
    }
    setPreviewConfig(newConfig);
    setPreviewOpen(true);
    try {
      const res = await execute(api.post("/config/validate", newConfig));
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
              <input
                type="checkbox"
                checked={!!isConfigured}
                onChange={(e) => {
                  e.stopPropagation();
                  handleToggle(m);
                }}
                className="model-toggle"
              />
              <span className={`model-dot${isSelected ? " selected" : isConfigured ? " configured" : ""}`} />
              {m.filename}
            </div>
          );
        })}
      </div>

      {selected && (
        <div className="model-detail">
          <h3>{selected.name || selected.filename}</h3>
          <div className="meta-row">
            <div><strong>Size:</strong> {selected.size}</div>
            <div><strong>Quant:</strong> {selected.quant}</div>
          </div>

          {Object.keys(form || {}).length > 0 && (
            <>
              <h4>llama-server options</h4>
              <div className="form-list">
                {Object.keys(form).map((key) => (
                  <label key={key} className="form-field">
                    <strong>{key}</strong>
                    <input
                      value={form[key] ?? ""}
                      onChange={(e) => handleChange(key, e.target.value)}
                    />
                  </label>
                ))}
              </div>
            </>
          )}

          {Object.keys(form || {}).length === 0 && (
            <p className="model-untoggled">Toggle this model to add it to config, then set options below.</p>
          )}

          <div className="form-actions">
            <button type="button" onClick={openPreview} disabled={!config?.models?.[selected.name] && Object.keys(form || {}).length === 0}>Validate & Preview</button>
          </div>

          {previewOpen && (
            <ConfigPreviewModal
              config={config}
              newConfig={previewConfig}
              validationResult={validationResult}
              onClose={() => setPreviewOpen(false)}
              title={`Preview — ${selected.filename}`}
            />
          )}
        </div>
      )}

      {!selected && <div className="model-detail model-empty">Select a model</div>}
    </div>
  );
}
