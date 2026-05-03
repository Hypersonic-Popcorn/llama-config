import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scanner import ScannerError

from src.custom_exceptions import ContainerNotRunning
from src.settings import settings

logger = logging.getLogger(__name__)

yaml = YAML()
yaml.preserve_quotes = True


def read_config() -> dict[str, Any]:  # type: ignore[return-type]
    try:
        with open(settings.config_path, "r") as f:
            data = yaml.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except FileNotFoundError:
        logger.error("Config file not found: %s", settings.config_path)
        return {}
    except (ParserError, ScannerError):
        logger.error("Failed to parse config YAML")
        return {}


def write_config(data: dict[str, Any], label: str | None = None) -> None:
    try:
        _create_backup(data, label)
        with open(settings.config_path, "w") as f:
            yaml.dump(data, f)
        logger.info("Config written successfully")
    except PermissionError as e:
        logger.error("Permission denied writing config: %s", e)
        raise
    except Exception as e:
        logger.error("Failed to write config: %s", e)
        raise


def list_backups() -> list[dict[str, Any]]:
    history_path = settings.backup_dir / "backup_history.json"
    try:
        with open(history_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse backup_history.json")
        return []


def restore_backup(backup_id: str) -> None:
    backup_dir = _get_backup_dir()
    backup_path = backup_dir / backup_id

    try:
        with open(backup_path, "rb") as f:
            data = f.read()
        with open(settings.config_path, "wb") as f:
            f.write(data)
        logger.info("Restored backup: %s", backup_id)
    except FileNotFoundError:
        logger.error("Backup file not found: %s", backup_id)
        raise ContainerNotRunning(f"Backup not found: {backup_id}")
    except PermissionError as e:
        logger.error("Permission denied restoring backup: %s", e)
        raise


def _get_backup_dir() -> Path:
    backup_dir = settings.backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _create_backup(data: dict[str, Any], label: str | None = None) -> str:
    backup_dir = _get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label_suffix = f"_{label}" if label else ""
    filename = f"{timestamp}{label_suffix}_config.yaml"
    backup_path = backup_dir / filename

    yaml.dump(data, open(backup_path, "w"))

    history = _load_history()
    entry = {
        "backup_id": filename,
        "timestamp": datetime.now().isoformat(),
        "label": label,
        "config_path": str(settings.config_path),
    }
    history.append(entry)
    history_path = backup_dir / "backup_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    logger.info("Backup created: %s", filename)
    return filename


def _load_history() -> list[dict[str, Any]]:
    history_path = settings.backup_dir / "backup_history.json"
    try:
        with open(history_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse backup_history.json")
        return []
