# llama-config Backend Plan

## Project Overview

`llama-config` is a browser-based tool for managing llama-swap configuration files.
The Python backend handles all file I/O, Docker interaction, model scanning, and
config validation. The frontend (React, planned separately) talks to this backend
exclusively via HTTP using FastAPI.

---

## Packages to Install

Use `uv add` for all dependencies:

```bash
uv add fastapi
uv add "uvicorn[standard]"   # ASGI server to run FastAPI
uv add ruamel.yaml           # YAML read/write that preserves comments
uv add docker                # Docker SDK for Python
uv add gguf                  # Read metadata from .gguf model files
uv add httpx                 # HTTP client for health-checking llama-swap
uv add pydantic              # Data validation (comes with FastAPI, but pin it explicitly)
uv add pydantic-settings
```

### Why these choices

- **ruamel.yaml** instead of PyYAML: PyYAML silently strips comments on write.
  llama-swap configs written by hand often have explanatory comments. ruamel.yaml
  preserves them through read/modify/write cycles.
- **docker SDK** instead of shelling out to the `docker` CLI: cleaner API, better
  error handling, no subprocess management for basic operations.
- **gguf**: Reads model metadata directly from .gguf files — parameter count,
  quantization type, context length, etc. Lets the UI show useful info rather than
  just filenames.
- **httpx**: Used to poll the llama-swap health endpoint after a container restart
  to confirm it came back up correctly.

---

## Project Structure

```
llama-config/src/
├── main.py                  # FastAPI app entry point
├── api/
│   ├── __init__.py
│   ├── config_routes.py     # Endpoints for reading/writing llama-swap config
│   ├── model_routes.py      # Endpoints for model directory scanning
│   ├── docker_routes.py     # Endpoints for container management
│   └── options_routes.py    # Endpoints for llama-server option discovery
├── core/
│   ├── __init__.py
│   ├── yaml_handler.py      # Read, write, and backup YAML files
│   ├── docker_manager.py    # Connect to and control the Docker container
│   ├── model_scanner.py     # Find .gguf files and read their metadata
│   ├── option_parser.py     # Parse llama-server/llama-swap .md docs and --help output
│   └── validator.py         # Validate configs before writing
├── config/
│   ├── current/             # Active llama-swap config lives here (or is a path reference)
│   └── backups/             # Timestamped backup copies
└── settings.py              # App-wide settings (container name, paths, etc.)
```

---

## Module Breakdown

### `settings.py`

Central place for configuration that may vary by environment. Use Pydantic's
`BaseSettings` so values can be overridden by environment variables.

Key settings to include:
- Docker container name or ID
- Path to the llama-swap config file (inside the container or mounted)
- Path to the model directory to scan
- Path to the llama-server and llama-swap markdown documentation files
- Backup directory path
- llama-swap health check URL (e.g. `http://localhost:8080/v1/models`)
- Health check timeout and poll interval (seconds)

---

### `core/docker_manager.py`

**Purpose:** All interaction with the Docker container goes through this module.

**Key responsibilities:**
1. Connect to Docker using `docker.from_env()`
2. Get the container by name from settings
3. Verify the container is running before attempting operations
4. Execute commands inside the container with `container.exec_run()`
5. Restart the container with `container.restart()`
6. Stream or return container logs
7. Handle the container being stopped or not found with clear error messages

**Key functions to implement:**

```python
def get_container()           # Returns the container object or raises a clear error
def container_is_running()    # Boolean health check
def exec_in_container(cmd)    # Run a command, return (exit_code, output)
def restart_container()       # Restart and return immediately
def get_logs(tail=100)        # Return recent log lines as a list of strings
```

**Note on compose vs SDK restart:**
`container.restart()` from the SDK is sufficient for config management purposes.
If you later want a true `docker compose` style restart, use:
```python
subprocess.run(["docker", "compose", "restart", "service-name"],
               cwd="/path/to/compose/dir")
```
But the SDK approach is preferred for now.

---

### `core/yaml_handler.py`

**Purpose:** All YAML file reading, writing, and backup operations.

**Key responsibilities:**
1. Read the current llama-swap config into a Python dict
2. Write a modified config back to disk
3. Before any write, create a timestamped backup
4. Maintain a `backup_history.json` file tracking each backup with timestamp and
   optional label
5. Provide a restore function that writes a backup copy back as the current config

**Key functions to implement:**

```python
def read_config(path)                    # Returns dict
def write_config(path, data, label=None) # Backs up first, then writes
def list_backups()                       # Returns list of backup metadata dicts
def restore_backup(backup_id)            # Copies backup to current config path
def _create_backup(path, label=None)     # Internal: timestamped copy + history entry
```

**Use ruamel.yaml in round-trip mode:**
```python
from ruamel.yaml import YAML
yaml = YAML()
yaml.preserve_quotes = True
```
This preserves comments, quote styles, and formatting as much as possible.

---

### `core/model_scanner.py`

**Purpose:** Discover .gguf model files and read their metadata.

**Key responsibilities:**
1. Walk the configured model directory recursively
2. Find all `.gguf` files
3. For each file, read metadata using the `gguf` package
4. Return structured data: filename, full path, size, and any available metadata
   (context length, parameter count, quantization type, architecture)
5. Handle files that are incomplete or unreadable without crashing

**Useful metadata fields from gguf:**
- `general.name`, `general.basename`, `general.architecture`, `general.file_type`,
  `general.license`, `general.license.link`, `general.finetune`,
  `general.quantization_version`, `general.size_label`, `general.type`
- `general.sampling.temp`, `general.sampling.top_k`, `general.sampling.top_p`
- `<arch>.block_count` (architecture-specific, e.g. `gemma4.block_count`)
- `<arch>.context_length` (NOT `general.context_length` — always architecture-specific)
- **Always consult `@rules/parsing_gguf.md`** when working on `model_scanner.py` or
  `model_routes.py` — it documents the internal `gguf` library API and which fields to parse.

**Key functions:**

```python
def scan_models(directory)        # Returns list of model dicts
def read_model_metadata(path)     # Returns metadata dict for one .gguf file
```

**Use the internal `gguf` API** — `reader.fields` returns `ReaderField` objects with
`parts` (numpy memmap arrays) and `types`. There is no documented `metadata` property.
See `@rules/parsing_gguf.md` for the full decoding strategy.

---

### `core/option_parser.py`

**Purpose:** Discover valid options for llama-server and llama-swap dynamically,
so the UI and validator always reflect what is actually installed.

**Two-source strategy (use both, prefer docs):**

**Source 1 — Markdown documentation files:**
Parse the `.md` files for llama-server and llama-swap. These contain human-readable
descriptions that are valuable for the UI. The markdown format can be inconsistent,
so parsing should be lenient and fail gracefully.

**Source 2 — `--help` output (fallback and cross-reference):**
Run `llama-server --help` inside the Docker container via `docker_manager.exec_in_container()`.
This gives the authoritative list of valid flag names for the installed version.
Use this to validate that flags parsed from the docs actually exist.

**Caching:**
After parsing, save the result as a JSON file (e.g. `options_cache.json`). The UI
and validator use the cached version. Provide an endpoint to force a refresh.

**Key functions:**

```python
def parse_markdown_docs(md_path)       # Returns list of option dicts
def parse_help_output(help_text)       # Returns list of flag names
def build_options_cache()              # Combines both sources, writes JSON cache
def load_options_cache()               # Returns cached options or triggers rebuild
```

**Option dict shape (suggested):**
```python
{
    "flag": "--n-gpu-layers",
    "short": "-ngl",           # if it exists
    "type": "int",             # int, float, str, bool
    "default": 0,
    "description": "Number of layers to offload to GPU",
    "valid_values": None       # or a list for enum-type options
}
```

---

### `core/validator.py`

**Purpose:** Validate a config dict before it is written to disk.

**Key responsibilities:**
1. Check that all required llama-swap top-level keys are present
2. For each model entry, validate that referenced llama-server flags exist in
   the options cache
3. Check value types (a flag that expects an int should not have a string value)
4. Check that referenced model paths actually exist on disk
5. Return a structured result: valid (bool) + list of error messages

**Key functions:**

```python
def validate_config(config_dict)       # Returns ValidationResult
def validate_model_entry(entry, options_cache)
```

**ValidationResult shape (use a dataclass or Pydantic model):**
```python
@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]   # non-fatal issues worth surfacing in the UI
```

---

### `main.py` and `api/` routes

**FastAPI entry point:**

```python
from fastapi import FastAPI
from api import config_routes, model_routes, docker_routes, options_routes

app = FastAPI(title="llama-config")

app.include_router(config_routes.router, prefix="/api/config")
app.include_router(model_routes.router, prefix="/api/models")
app.include_router(docker_routes.router, prefix="/api/docker")
app.include_router(options_routes.router, prefix="/api/options")
```

**Run with:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Global error handling:**
Use FastAPI's exception handler to catch unexpected errors and return consistent
JSON responses rather than stack traces:

```python
from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )
```

**Also use Python's `logging` module** throughout the backend (not just `print`).
Write to a log file so the UI can expose a log viewer later:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("llama-config.log"),
        logging.StreamHandler()   # also print to console
    ]
)
```

---

### Suggested API Endpoints

#### Config (`/api/config`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config` | Read current config |
| POST | `/api/config` | Validate and write new config, restart container |
| GET | `/api/config/backups` | List available backups |
| POST | `/api/config/restore/{backup_id}` | Restore a backup and restart |

#### Models (`/api/models`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/models` | Scan model directory and return list with metadata |

#### Docker (`/api/docker`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/docker/status` | Is container running? |
| POST | `/api/docker/restart` | Restart container |
| GET | `/api/docker/logs` | Recent log lines |
| GET | `/api/docker/health` | Poll llama-swap health endpoint and return result |

#### Options (`/api/options`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/options/llama-server` | Get parsed llama-server options |
| GET | `/api/options/llama-swap` | Get parsed llama-swap options |
| POST | `/api/options/refresh` | Force re-parse docs and --help, rebuild cache |

---

## Config Save + Restart Flow

This is the most critical operation in the app. Implement it as an atomic sequence:

1. **Validate** the incoming config with `validator.validate_config()`
   - If invalid, return errors immediately. Do not write anything.
2. **Backup** the current config with `yaml_handler.write_config()` (backup is
   automatic before every write)
3. **Write** the new config to disk
4. **Restart** the container with `docker_manager.restart_container()`
5. **Poll** the llama-swap health endpoint (e.g. `GET /v1/models`) every 2 seconds
   for up to 30 seconds using `httpx`
6. **If healthy:** return success to the UI
7. **If timeout:** automatically restore the last backup, restart the container
   again, and return a failure response explaining what happened

This gives you automatic rollback without requiring any user action if a bad config
makes it past validation.

---

## Suggested Build Order

Build and test these modules in order. Each one depends on the previous.

1. **`settings.py`** — No dependencies. Define all paths and config values here first.
2. **`docker_manager.py`** — Verify you can connect, exec a command, and restart.
   Test with a harmless command like `echo hello`.
3. **`yaml_handler.py`** — Read the real config file, write a copy, verify backup
   creation.
4. **`option_parser.py`** — Parse `llama-server --help` via the container exec.
   Get a working options list before tackling the markdown parsing.
5. **`validator.py`** — Use the options cache from step 4. Test against your real
   config to make sure it passes.
6. **`model_scanner.py`** — Scan your actual model directory. Confirm metadata reads
   correctly.
7. **`main.py` + `api/` routes** — Wire everything together with FastAPI. Test each
   endpoint with the FastAPI interactive docs at `http://localhost:8000/docs`.

---

## Notes for the Local AI Agent (opencode)

- Always import from `settings.py` for paths and config values. Do not hardcode paths.
- Every function that touches the Docker container should handle `docker.errors.NotFound`
  and `docker.errors.APIError` explicitly.
- Every function that does file I/O should handle `FileNotFoundError` and
  `PermissionError` explicitly.
- Log at `INFO` level for normal operations, `WARNING` for recoverable issues,
  `ERROR` for failures that need user attention.
- Use Pydantic models for all FastAPI request and response bodies. This gives you
  automatic validation and good error messages for free.
- The frontend will be a separate React app running on a different port. FastAPI
  will need CORS enabled:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(CORSMiddleware, allow_origins=["*"],
                     allow_methods=["*"], allow_headers=["*"])
  ```
  Restrict `allow_origins` to the actual frontend URL once you know it.
