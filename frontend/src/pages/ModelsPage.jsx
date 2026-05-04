import { useEffect, useState } from "react";
import api from "@/api/client";
import { useApi } from "@/hooks/useApi";

export default function ModelsPage() {
  const [models, setModels] = useState([]);
  const [config, setConfig] = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({});
  const [previewOpen, setPreviewOpen] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
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
    setPreviewOpen(true);
    const previewConfig = {
      ...(config || {}),
      models: {
        ...(config?.models || {}),
        [selected.name]: form,
      },
    };
    try {
      const res = await execute(api.post("/config/validate", previewConfig));
      setValidationResult(res.data);
    } catch (err) {
      setValidationResult({ error: err.response?.data || "Validation failed" });
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
            <ModelsPreviewModal
              config={config}
              modelName={selected.name}
              form={form}
              validationResult={validationResult}
              onClose={() => setPreviewOpen(false)}
            />
          )}
        </div>
      )}

      {!selected && <div className="model-detail model-empty">Select a model</div>}
    </div>
  );
}

function ModelsPreviewModal({ config, modelName, form, validationResult, onClose }) {
  const previewConfig = {
    ...(config || {}),
    models: {
      ...(config?.models || {}),
      [modelName]: form,
    },
  };

  return (
    <div className="modal-overlay">
      <div className="modal-dialog">
        <h3>Config Preview</h3>
        {validationResult?.error ? (
          <p className="error-text">{validationResult.error}</p>
        ) : (
          <pre className="modal-body">
            {JSON.stringify(previewConfig, null, 2)}
          </pre>
        )}
        <div className="modal-footer">
          <button type="button" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
