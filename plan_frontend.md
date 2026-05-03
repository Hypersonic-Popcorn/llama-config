# llama-config Frontend Plan

## Overview

The frontend is a React single-page application that communicates exclusively
with the Python FastAPI backend via HTTP. It never touches the filesystem or
Docker directly. All state changes flow through the backend API.

The UI is primarily for personal use but should be presentable. It is served
locally and accessed over a Tailscale tailnet.

---

## Tech Stack

```bash
npm create vite@latest llama-config-ui -- --template react
cd llama-config-ui
npm install
```

### Additional packages to install

```bash
npm install axios               # HTTP requests to the FastAPI backend
npm install react-router-dom    # Client-side routing between pages
npm install @uiw/react-codemirror  # Code editor for YAML preview
npm install diff                # Compute config diffs for the summary tab
```

### Why these choices

- **Vite**: Fast modern build tool. The old Create React App is deprecated.
- **axios**: Slightly cleaner than raw `fetch` for API calls. Lets you set a
  base URL once so every call doesn't repeat `http://localhost:8000`.
- **react-router-dom**: Standard routing library. Gives each page its own URL
  path and handles sidebar navigation cleanly.
- **@uiw/react-codemirror**: Syntax-highlighted, read-only YAML viewer for the
  config preview modal. Much better than a plain `<pre>` block.
- **diff**: Pure JS library for computing text diffs. Used to build the
  "Summary" tab in the config preview modal.

---

## Project Structure

```
llama-config-ui/
├── src/
│   ├── main.jsx               # React entry point
│   ├── App.jsx                # Root component, router, layout shell
│   ├── api/
│   │   └── client.js          # axios instance with base URL configured
│   ├── components/
│   │   ├── Sidebar.jsx        # Navigation sidebar
│   │   ├── TopBar.jsx         # Status bar, stale config indicator
│   │   └── ConfigPreviewModal.jsx  # Validate/preview/approve modal
│   ├── pages/
│   │   ├── ConfigPage.jsx     # llama-swap/server global settings
│   │   ├── ModelsPage.jsx     # Master-detail model list and config
│   │   ├── DockerPage.jsx     # Container status and controls
│   │   └── LogsPage.jsx       # Container and llama-swap logs
│   └── hooks/
│       └── useStaleConfig.js  # Shared state: has config been saved since last restart?
├── index.html
└── vite.config.js
```

---

## Layout

The app has three layout regions that are always visible:

```
┌─────────────────────────────────────────────────────┐
│  TopBar  (app title, stale config indicator)        │
├──────────┬──────────────────────────────────────────┤
│          │                                          │
│ Sidebar  │  Page content (changes with route)       │
│          │                                          │
│          │                                          │
│          │                                          │
└──────────┴──────────────────────────────────────────┘
```

### Sidebar links

- Config
- Models
- Docker
- Logs

Active link should be visually highlighted. Sidebar should show the app name
at the top.

### TopBar states

**Normal:** Just the app name / current page title.

**Stale config:** Shows a warning message like "Config saved — container running
stale config" and the restart button becomes highlighted (amber/orange color).
This state is set whenever a config is successfully written to disk and cleared
when the container is successfully restarted.

The stale config state should persist if the user navigates between pages. This
means it needs to live at the App level, not inside any individual page. See
`useStaleConfig.js` below.

---

## Shared State: `useStaleConfig.js`

This is a custom React hook that holds whether the on-disk config is newer than
the running container. Pass it down from `App.jsx` to `TopBar` and `DockerPage`.

```javascript
// hooks/useStaleConfig.js
import { useState } from "react";

export function useStaleConfig() {
  const [isStale, setIsStale] = useState(false);
  const markStale = () => setIsStale(true);
  const markFresh = () => setIsStale(false);
  return { isStale, markStale, markFresh };
}
```

`markStale()` is called after a successful config save.
`markFresh()` is called after a successful container restart.

---

## API Client: `api/client.js`

Configure axios once so every page uses the same base URL:

```javascript
import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
  timeout: 30000,  // 30s — restarts can take a moment
});

export default api;
```

Import `api` in any page component and call `api.get("/config")`,
`api.post("/docker/restart")`, etc.

---

## Pages

### ConfigPage (`/config`)

**Purpose:** Edit the global llama-swap and llama-server settings that apply
to all models.

**Layout:** A form with sections for llama-swap settings and llama-server
defaults. Below the form, a "Validate & Preview" button.

**Behavior:**
1. On mount, fetch current config from `GET /api/config`
2. Populate form fields with current values
3. As user edits fields, update local component state (not saved yet)
4. "Validate & Preview" button opens `ConfigPreviewModal`
5. On approval in the modal, POST the new config to `POST /api/config`
6. On success, call `markStale()` to update the TopBar

**Key React concepts this page teaches:**
- `useEffect` for fetching data when the component loads
- `useState` for tracking form field values
- Controlled inputs (React manages the input value, not the DOM)

---

### ModelsPage (`/models`)

**Purpose:** Browse available models, see their status, and configure
per-model llama-server options.

**Layout:** Master-detail split pane.

```
┌─────────────────┬──────────────────────────────────┐
│  Model List     │  Model Detail                    │
│                 │                                  │
│  [●] model-a   │  Name: model-a.gguf              │
│  [○] model-b   │  Size: 7B  Quant: Q4_K_M         │
│  [○] model-c   │  Context: 32768                  │
│                 │                                  │
│                 │  --- llama-server options ---    │
│                 │  [ form fields ]                 │
│                 │                                  │
│                 │  [ Add to Config ]               │
└─────────────────┴──────────────────────────────────┘
```

**Model status indicators:**
- In config + currently loaded by llama-swap: filled/green dot
- In config but not loaded: outlined dot or yellow
- Not in config: no indicator or grey

**Behavior:**
1. On mount, fetch model list from `GET /api/models`
2. Also fetch current config from `GET /api/config` to know which models
   are configured
3. Clicking a model in the list sets it as the selected model in state
4. Detail pane shows gguf metadata (read-only) and editable llama-server
   option fields, pre-populated from the current config if the model is
   already configured
5. "Add to Config" / "Update Config" button updates the pending config
   in local state (does not save to disk)
6. The pending config change feeds into the same "Validate & Preview"
   flow as the ConfigPage

**Key React concepts this page teaches:**
- Master-detail pattern (one piece of state controls which detail is shown)
- Combining data from two API calls to build UI state
- Conditional rendering (show detail pane only when a model is selected)

---

### DockerPage (`/docker`)

**Purpose:** View container status and control it.

**Layout:** Simple centered card or panel.

```
  Container Status: [ RUNNING ]  ← color coded green/red

  [ Start ]  [ Stop ]  [ Restart ← highlighted if stale ]
```

**Behavior:**
1. On mount, fetch status from `GET /api/docker/status`
2. Buttons call `POST /api/docker/restart` etc.
3. After a successful restart, call `markFresh()` to clear the stale indicator
4. While a restart is in progress, disable the buttons and show a loading state
5. Show the result (success or rollback failure) as a message on the page

**Key React concepts this page teaches:**
- Async button handlers with loading state
- Receiving props from a parent (`isStale`, `markFresh`)
- Conditional styling based on state

---

### LogsPage (`/logs`)

**Purpose:** View container and llama-swap logs.

**Layout:** Two side-by-side panels, or two tabs within the page — whichever
feels cleaner. Tabs within the page are simpler to implement first.

**Controls (shared across both log sources):**
- Manual "Refresh" button
- Auto-refresh toggle (checkbox or switch)
- Delay selector: dropdown with options (5s, 10s, 30s, 60s) plus a text
  input for custom values

**Behavior:**
1. On mount, fetch both logs once
2. Refresh button manually re-fetches
3. When auto-refresh is on, use `setInterval` inside a `useEffect` to
   re-fetch at the selected delay
4. When auto-refresh is turned off or the component unmounts, clear the
   interval (important — forgetting this causes bugs)
5. Logs display in a monospace scrollable box, newest entries at the bottom

**Key React concepts this page teaches:**
- `useEffect` with cleanup (clearing the interval on unmount)
- `useEffect` dependencies array (re-run when delay changes)
- Multiple pieces of related state (`isAutoRefresh`, `delay`, `logs`)

**Backend endpoints needed:**
- `GET /api/docker/logs` — container logs
- `GET /api/docker/llama-swap-logs` — llama-swap process logs (may be the
  same as container logs depending on how llama-swap writes output)

---

## ConfigPreviewModal

**Purpose:** Show the user what will be written before committing.

**Trigger:** "Validate & Preview" button on ConfigPage or ModelsPage.

**Layout:** A modal/dialog that overlays the page with two tabs:

- **Summary tab:** A diff view showing only what changed (additions in green,
  removals in red). Use the `diff` library to compute this against the current
  config fetched from the backend.
- **Full Config tab:** The complete YAML that would be written, displayed in
  a syntax-highlighted read-only editor using `@uiw/react-codemirror`.

**Controls inside the modal:**
- "Cancel" — closes modal, no changes made
- "Apply" — POSTs the new config to the backend, closes modal, calls `markStale()`

**Validation behavior:**
- When the modal opens, first hit `POST /api/config/validate` (validate only,
  don't write)
- If validation fails, show error messages in the modal instead of the preview
  tabs — don't let the user proceed to Apply
- If validation passes, show the tabs

**Key React concepts this page teaches:**
- Modal/portal pattern
- Conditional rendering based on async result (loading → errors or preview)
- Lifting the pending config state up to where both the page and modal can
  access it

---

## Data Flow Summary

```
User edits form fields
        ↓
Local component state updates (nothing saved yet)
        ↓
"Validate & Preview" clicked
        ↓
POST /api/config/validate  →  errors or success
        ↓ (success)
Modal opens: Summary diff + Full YAML tabs
        ↓
"Apply" clicked
        ↓
POST /api/config  →  config written to disk
        ↓
markStale() called → TopBar shows stale indicator
        ↓
User navigates to Docker page (or clicks highlighted Restart)
        ↓
POST /api/docker/restart  →  container restarts, health poll
        ↓
markFresh() called → TopBar returns to normal
```

---

## Backend Endpoints the Frontend Needs

Cross-reference with `plan_backend.md`. The frontend expects these to exist:

| Method | Path | Used by |
|--------|------|---------|
| GET | `/api/config` | ConfigPage, ModelsPage, ConfigPreviewModal |
| POST | `/api/config/validate` | ConfigPreviewModal (validate only, no write) |
| POST | `/api/config` | ConfigPreviewModal (apply) |
| GET | `/api/config/backups` | (future: backup browser) |
| GET | `/api/models` | ModelsPage |
| GET | `/api/options/llama-server` | ModelsPage (populate option fields) |
| GET | `/api/docker/status` | DockerPage |
| POST | `/api/docker/restart` | DockerPage |
| POST | `/api/docker/start` | DockerPage |
| POST | `/api/docker/stop` | DockerPage |
| GET | `/api/docker/logs` | LogsPage |
| GET | `/api/docker/llama-swap-logs` | LogsPage |

Note: `POST /api/config/validate` is a separate endpoint from `POST /api/config`.
Make sure the backend plan includes a validate-only route that does not write
anything to disk.

---

## Suggested Build Order

Build and test in this order. Each step is a working increment.

1. **Vite project setup** — get a blank React app running in the browser
2. **`api/client.js`** — configure axios, verify it can reach the backend
3. **App shell** — `App.jsx` with sidebar and top bar, no real content yet,
   just placeholder text in each page slot
4. **Routing** — add `react-router-dom`, make sidebar links navigate between
   empty page components
5. **DockerPage** — simplest page, good first real component. Fetch status,
   show it, wire up restart button
6. **LogsPage** — introduces `useEffect` with cleanup. Build manual refresh
   first, then add auto-refresh
7. **ConfigPage** — introduces controlled form inputs and the validate flow
8. **ConfigPreviewModal** — build after ConfigPage so you have real data to
   preview
9. **ModelsPage** — most complex page, build last. Master-detail pattern plus
   combining two API responses
10. **Stale config indicator** — add `useStaleConfig` hook and wire TopBar
    after DockerPage and ConfigPage both work

---

## Notes for the Local AI Agent (opencode)

- Always use `api/client.js` for HTTP calls. Never hardcode `localhost:8000`
  in a page component.
- All API calls should be inside `try/catch` blocks. Show error state in the
  UI rather than crashing.
- Use `useEffect` with a dependency array on every data-fetching effect.
  An empty array `[]` means "run once on mount." Missing dependencies cause
  stale data bugs.
- Always return a cleanup function from `useEffect` when using `setInterval`.
  Forgetting this leaks timers and causes bugs when navigating between pages.
- Keep page components focused on layout and user interaction. Move any
  non-trivial logic into hooks or helper functions.
- Use `useState` for all values that should cause a re-render when they change.
  Do not store UI state in regular variables.
- The `isStale` / `markStale` / `markFresh` values come from `App.jsx` via
  props. Do not duplicate this state in individual pages.
- CORS is already handled in the backend plan. If you see CORS errors during
  development, check that the FastAPI backend is running and the base URL in
  `client.js` matches.
- Vite's dev server runs on port 5173 by default. The backend runs on port
  8000. These are different — both need to be running during development.
- For styling, use plain CSS or CSS modules to start. Do not add a large UI
  component library until the structure is working — it adds complexity before
  the fundamentals are solid. Tailwind CSS can be added later if desired.
