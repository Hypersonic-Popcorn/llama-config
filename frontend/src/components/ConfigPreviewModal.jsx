import { useState } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { yaml } from "@codemirror/lang-yaml";
import { createTwoFilesPatch } from "diff";

export default function ConfigPreviewModal({
  config,
  newConfig,
  validationResult,
  onClose,
  onApply,
  title = "Config Preview",
}) {
  const [activeTab, setActiveTab] = useState("summary");

  if (validationResult?.error) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
          <h3>Validation Error</h3>
          <p className="error-text">{validationResult.error}</p>
          <div className="modal-footer">
            <button type="button" onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    );
  }

  const yamlString = JSON.stringify(newConfig, null, 2);

  const summaryDiff = getSummary(config, newConfig);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>

        <div className="modal-tabs">
          <button
            type="button"
            onClick={() => setActiveTab("summary")}
            className={activeTab === "summary" ? "tab-active" : ""}
          >
            Summary
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("config")}
            className={activeTab === "config" ? "tab-active" : ""}
          >
            Full Config
          </button>
        </div>

        {activeTab === "summary" && (
          <div className="modal-body modal-body-code">
            {summaryDiff === null ? (
              <p className="text-muted">No changes detected.</p>
            ) : (
              <pre className="modal-body-code" dangerouslySetInnerHTML={{ __html: summaryDiff }} />
            )}
          </div>
        )}

        {activeTab === "config" && (
          <div className="modal-body modal-body-code">
            <CodeMirror
              value={yamlString}
              theme="default"
              extensions={[yaml()]}
              editable={false}
            />
          </div>
        )}

        <div className="modal-footer">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="button" onClick={onApply} className="btn btn-apply">
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}

function getSummary(oldConfig, newConfig) {
  const oldYaml = JSON.stringify(oldConfig, null, 2);
  const newYaml = JSON.stringify(newConfig, null, 2);

  if (oldYaml === newYaml) return null;

  const diff = createTwoFilesPatch("old.yaml", "new.yaml", oldYaml, newYaml);
  return highlightDiff(diff);
}

function highlightDiff(diffText) {
  const lines = diffText.split("\n");
  return lines
    .map((line) => {
      if (line.startsWith("+") && !line.startsWith("+++")) {
        return `<span class="diff-add">${escapeHtml(line)}</span>`;
      }
      if (line.startsWith("-") && !line.startsWith("---")) {
        return `<span class="diff-del">${escapeHtml(line)}</span>`;
      }
      return `<span class="diff-context">${escapeHtml(line)}</span>`;
    })
    .join("\n");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}
