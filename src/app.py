import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import yaml

SETTINGS_YAML = "llama-config.yaml"


def main():
    args = parse_args()
    settings = load_settings(args)
    apply_settings(settings)

    # Set scanned models path to CWD for the backend process
    os.environ["SCANNED_MODELS_PATH"] = str(Path.cwd() / "scanned_models.yaml")

    print("Starting backend...")
    backend_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--log-level",
            "info",
        ],
        cwd=PROJECT_ROOT,
        env=os.environ,
    )

    print("Waiting for backend to be ready...")
    poll_health(
        settings["health_check_url"],
        settings["health_check_timeout"],
        settings["health_check_interval"],
    )
    print("Backend is ready.")

    print("Starting frontend...")
    frontend_proc = subprocess.Popen(
        ["npx", "vite", "--host", "0.0.0.0"],
        cwd=str(PROJECT_ROOT / "frontend"),
    )

    shutdown = threading.Event()

    def handle_signal(signum, _frame):
        print("\nShutting down...")
        shutdown.set()
        try:
            backend_proc.terminate()
        except ProcessLookupError:
            pass
        try:
            frontend_proc.terminate()
        except ProcessLookupError:
            pass

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print("\nBackend: http://localhost:8000")
    print("Frontend: http://localhost:5173")
    print("(Ctrl+C to stop)")

    # Wait on backend in a thread so we can detect its exit
    def wait_backend():
        backend_proc.wait()

    backend_thread = threading.Thread(target=wait_backend, daemon=True)
    backend_thread.start()

    try:
        while not shutdown.is_set():
            shutdown.wait(0.5)
        backend_thread.join(timeout=5)
    except KeyboardInterrupt:
        pass

    # Wait for processes to fully exit
    try:
        backend_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        backend_proc.kill()
        backend_proc.wait()

    try:
        frontend_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        frontend_proc.kill()
        frontend_proc.wait()

    print("Done.")
    sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(
        description="llama-config: start backend + frontend with a single command.",
    )
    parser.add_argument("-c", "--config-path", help="Path to llama-swap config.yaml")
    parser.add_argument("-m", "--model-dir", help="Directory to scan for models")
    parser.add_argument("-n", "--container", help="Docker container name")
    parser.add_argument("-b", "--backup-dir", help="Backup directory path")
    parser.add_argument("-d", "--docs-dir", help="llama-swap docs directory")
    parser.add_argument("-u", "--health-url", help="Health check URL")
    parser.add_argument(
        "--health-timeout", type=int, help="Health check timeout (seconds)"
    )
    parser.add_argument(
        "--health-interval", type=int, help="Health check poll interval (seconds)"
    )
    return parser.parse_args()


def load_settings(args):
    """Load settings from CLI args and llama-config.yaml."""
    defaults = _defaults()
    file_path = Path.cwd() / SETTINGS_YAML

    # Load from YAML file if it exists
    if file_path.exists():
        try:
            with open(file_path) as f:
                file_data = yaml.safe_load(f) or {}
        except Exception:
            file_data = {}
    else:
        file_data = {}

    # Build settings dict: defaults ← file ← CLI
    settings = dict(defaults)

    # Override with file values (only keys that exist in defaults)
    for k in defaults:
        if k in file_data:
            settings[k] = file_data[k]

    # Override with CLI args (non-None only)
    cli_map = {
        "config_file": args.config_path,
        "model_dir": args.model_dir,
        "docker_container_name": args.container,
        "backup_dir": args.backup_dir,
        "docs_dir": args.docs_dir,
        "health_check_url": args.health_url,
        "health_check_timeout": args.health_timeout,
        "health_check_interval": args.health_interval,
    }

    for settings_key, cli_val in cli_map.items():
        if cli_val is not None:
            settings[settings_key] = cli_val

    # Save back to YAML file (persist all current values)
    try:
        with open(file_path, "w") as f:
            yaml.dump(settings, f, default_flow_style=False)
    except Exception as e:
        print(f"Warning: could not write {SETTINGS_YAML}: {e}")

    return settings


def apply_settings(settings):
    """Override settings via environment variables for pydantic Settings."""
    env_map = {
        "config_file": "CONFIG_FILE",
        "model_dir": "MODEL_DIR",
        "docker_container_name": "DOCKER_CONTAINER_NAME",
        "backup_dir": "BACKUP_DIR",
        "docs_dir": "DOCS_DIR",
        "health_check_url": "HEALTH_CHECK_URL",
        "health_check_timeout": "HEALTH_CHECK_TIMEOUT",
        "health_check_interval": "HEALTH_CHECK_INTERVAL",
        "log_dir": "LOG_DIR",
    }

    for key, env_var in env_map.items():
        if key in settings:
            os.environ[env_var] = str(settings[key])


def _defaults():
    """Return hardcoded defaults from Settings."""
    from src.settings import Settings

    s = Settings()
    return {
        "config_file": str(s.config_file),
        "model_dir": str(s.model_dir),
        "docker_container_name": s.docker_container_name,
        "backup_dir": str(s.backup_dir),
        "docs_dir": str(s.docs_dir),
        "health_check_url": s.health_check_url,
        "health_check_timeout": s.health_check_timeout,
        "health_check_interval": s.health_check_interval,
        "log_dir": str(s.log_dir),
    }


def poll_health(url, timeout, interval):
    """Poll the backend health endpoint until it responds."""
    deadline = time.time() + timeout
    try:
        with httpx.Client(verify=False) as client:
            while time.time() < deadline:
                try:
                    resp = client.get(url, timeout=5)
                    if resp.status_code == 200:
                        return
                except (
                    httpx.ConnectError,
                    httpx.ReadTimeout,
                    httpx.TimeoutException,
                    httpx.RequestError,
                ):
                    pass
                time.sleep(interval)
    except Exception as e:
        raise Exception(f"Health check failed: {e}") from e
    raise Exception(f"Health check timeout: {url} did not respond within {timeout}s")


PROJECT_ROOT = Path(__file__).parent.parent


if __name__ == "__main__":
    main()
