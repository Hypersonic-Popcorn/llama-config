import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_settings(tmp_path):
    with patch("src.core.yaml_handler.settings") as mock:
        mock.config_path = tmp_path / "config.yaml"
        mock.backup_dir = tmp_path / "backups"
        mock.model_directory = tmp_path / "models"
        mock.docs_dir = tmp_path / "docs"
        mock.docker_container_name = "llama-swap"
        mock.health_check_url = "http://localhost:8080/v1/models"
        mock.health_check_timeout = 30
        mock.health_check_interval = 2
        mock.log_file = tmp_path / "logs"
        yield mock


@pytest.fixture
def tmp_write_protect_dir(tmp_path):
    return tmp_path


def _write_yaml(path, data):
    from ruamel.yaml import YAML

    yaml = YAML()
    with open(path, "w") as f:
        yaml.dump(data, f)


def test_read_config_returns_dict(mock_settings):
    config_path = mock_settings.config_path
    _write_yaml(config_path, {"model": "llama", "n_gpu_layers": 35})

    from src.core.yaml_handler import read_config

    result = read_config()

    assert result == {"model": "llama", "n_gpu_layers": 35}


def test_read_config_returns_empty_on_not_found(mock_settings):
    config_path = mock_settings.config_path
    assert config_path.exists() is False

    from src.core.yaml_handler import read_config

    result = read_config()

    assert result == {}


def test_read_config_returns_empty_on_parse_error(mock_settings):
    config_path = mock_settings.config_path
    config_path.write_text("{{invalid yaml\n")

    from src.core.yaml_handler import read_config

    result = read_config()

    assert result == {}


def test_write_config_writes_yaml(mock_settings):
    data = {"model": "llama", "n_gpu_layers": 35}

    from src.core.yaml_handler import write_config

    write_config(data)

    from ruamel.yaml import YAML

    yaml = YAML()
    with open(mock_settings.config_path, "r") as f:
        result = yaml.load(f)
    assert result == data


def test_write_config_creates_backup(mock_settings):
    data = {"model": "llama", "n_gpu_layers": 35}

    from src.core.yaml_handler import write_config

    write_config(data)

    backup_dir = mock_settings.backup_dir
    assert backup_dir.exists()
    backup_files = list(backup_dir.glob("*.yaml"))
    assert len(backup_files) == 1


def test_write_config_adds_to_history(mock_settings):
    data = {"model": "llama", "n_gpu_layers": 35}

    from src.core.yaml_handler import write_config

    write_config(data)

    history_path = mock_settings.backup_dir / "backup_history.json"
    with open(history_path, "r") as f:
        history = json.load(f)
    assert len(history) == 1
    assert history[0]["config_path"] == str(mock_settings.config_path)


def test_write_config_with_label(mock_settings):
    data = {"model": "llama", "n_gpu_layers": 35}

    from src.core.yaml_handler import write_config

    write_config(data, label="test-label")

    history_path = mock_settings.backup_dir / "backup_history.json"
    with open(history_path, "r") as f:
        history = json.load(f)
    assert history[0]["label"] == "test-label"


def test_write_config_propagates_permission_error(mock_settings):
    data = {"model": "llama"}

    mock_settings.config_path = Path("/root/protected/config.yaml")

    from src.core.yaml_handler import write_config

    with pytest.raises(PermissionError):
        write_config(data)


def test_list_backups_returns_list(mock_settings):
    history_path = mock_settings.backup_dir / "backup_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "w") as f:
        json.dump(
            [
                {
                    "backup_id": "20250101_120000_config.yaml",
                    "timestamp": "2025-01-01T12:00:00",
                    "label": None,
                    "config_path": str(mock_settings.config_path),
                }
            ],
            f,
            indent=2,
        )

    from src.core.yaml_handler import list_backups

    result = list_backups()

    assert len(result) == 1
    assert result[0]["backup_id"] == "20250101_120000_config.yaml"


def test_list_backups_returns_empty_on_missing(mock_settings):
    from src.core.yaml_handler import list_backups

    result = list_backups()

    assert result == []


def test_list_backups_returns_empty_on_bad_json(mock_settings):
    history_path = mock_settings.backup_dir / "backup_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text("{{not valid json}}")

    from src.core.yaml_handler import list_backups

    result = list_backups()

    assert result == []


def test_restore_backup_restores_file(mock_settings):
    backup_dir = mock_settings.backup_dir

    backup_file = backup_dir / "20250101_120000_config.yaml"
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file.write_bytes(b"model: llama\nn_gpu_layers: 35\n")

    original_config = Path("/tmp/original_config.yaml")
    original_config.write_bytes(b"model: mistral\n")
    mock_settings.config_path = original_config

    from src.core.yaml_handler import restore_backup

    restore_backup("20250101_120000_config.yaml")

    assert original_config.read_bytes() == b"model: llama\nn_gpu_layers: 35\n"
    original_config.unlink()


def test_restore_backup_raises_if_not_found(mock_settings):
    from src.custom_exceptions import ContainerNotRunning

    from src.core.yaml_handler import restore_backup

    with pytest.raises(ContainerNotRunning) as exc_info:
        restore_backup("nonexistent_backup.yaml")

    assert "Backup not found" in str(exc_info.value)


def test_restore_backup_raises_permission_error(tmp_write_protect_dir):
    from src.core.yaml_handler import restore_backup

    backup_dir = tmp_write_protect_dir / "backups"
    backup_file = backup_dir / "20250101_120000_config.yaml"
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file.write_bytes(b"model: llama\n")

    config_path = tmp_write_protect_dir / "protected_config.yaml"
    config_path.write_bytes(b"model: mistral\n")
    config_path.chmod(0o000)

    with patch("src.core.yaml_handler.settings") as mock:
        mock.config_path = config_path
        mock.backup_dir = backup_dir
        mock.model_directory = tmp_write_protect_dir / "models"
        mock.docs_dir = tmp_write_protect_dir / "docs"
        mock.docker_container_name = "llama-swap"

        with pytest.raises(PermissionError):
            restore_backup("20250101_120000_config.yaml")

    config_path.chmod(0o644)
    config_path.unlink()
