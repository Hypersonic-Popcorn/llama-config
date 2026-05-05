from unittest.mock import MagicMock, patch

import pytest

from src.app import load_settings, parse_args, poll_health


def test_parse_args_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["app"])
    args = parse_args()
    assert args.config_path is None
    assert args.model_dir is None
    assert args.container is None
    assert args.backup_dir is None
    assert args.docs_dir is None
    assert args.health_url is None
    assert args.health_timeout is None
    assert args.health_interval is None


def test_parse_args_with_values(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "app",
            "-c",
            "/tmp/config.yaml",
            "-m",
            "/tmp/models",
            "-n",
            "my-container",
            "-b",
            "/tmp/backups",
            "-d",
            "/tmp/docs",
            "-u",
            "http://localhost:9999",
            "--health-timeout",
            "60",
            "--health-interval",
            "5",
        ],
    )
    args = parse_args()

    assert args.config_path == "/tmp/config.yaml"
    assert args.model_dir == "/tmp/models"
    assert args.container == "my-container"
    assert args.backup_dir == "/tmp/backups"
    assert args.docs_dir == "/tmp/docs"
    assert args.health_url == "http://localhost:9999"
    assert args.health_timeout == 60
    assert args.health_interval == 5


def test_load_settings_defaults(tmp_path):
    defaults = {
        "config_file": "/default/config.yaml",
        "model_dir": "/default/models",
        "docker_container_name": "llama-swap",
        "backup_dir": "/default/backups",
        "docs_dir": "/default/docs",
        "health_check_url": "http://localhost:8080/v1/models",
        "health_check_timeout": 30,
        "health_check_interval": 2,
        "log_dir": "/default/logs",
    }

    yaml_path = tmp_path / "llama-config.yaml"
    yaml_path.write_text("")  # exists but empty

    with patch("src.app._defaults", return_value=defaults):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("yaml.safe_load", return_value=None):
                with patch("yaml.dump"):
                    settings = load_settings(Namespace())

    assert settings["config_file"] == "/default/config.yaml"
    assert settings["model_dir"] == "/default/models"


def test_load_settings_from_yaml(tmp_path):
    defaults = {
        "config_file": "/default/config.yaml",
        "model_dir": "/default/models",
        "docker_container_name": "llama-swap",
        "backup_dir": "/default/backups",
        "docs_dir": "/default/docs",
        "health_check_url": "http://localhost:8080/v1/models",
        "health_check_timeout": 30,
        "health_check_interval": 2,
        "log_dir": "/default/logs",
    }
    file_data = {"config_file": "/yaml/config.yaml"}

    yaml_path = tmp_path / "llama-config.yaml"
    yaml_path.write_text("config_file: /yaml/config.yaml\n")

    with patch("src.app._defaults", return_value=defaults):
        with patch("yaml.safe_load", return_value=file_data):
            with patch("yaml.dump"):
                settings = load_settings(Namespace())

    assert settings["config_file"] == "/yaml/config.yaml"
    assert settings["model_dir"] == "/default/models"


def test_load_settings_cli_overrides(tmp_path):
    defaults = {
        "config_file": "/default/config.yaml",
        "model_dir": "/default/models",
        "docker_container_name": "llama-swap",
        "backup_dir": "/default/backups",
        "docs_dir": "/default/docs",
        "health_check_url": "http://localhost:8080/v1/models",
        "health_check_timeout": 30,
        "health_check_interval": 2,
        "log_dir": "/default/logs",
    }

    yaml_path = tmp_path / "llama-config.yaml"
    yaml_path.write_text("")

    with patch("src.app._defaults", return_value=defaults):
        with patch("yaml.safe_load", return_value=None):
            with patch("yaml.dump"):
                settings = load_settings(Namespace(config_path="/cli/config.yaml"))

    assert settings["config_file"] == "/cli/config.yaml"
    assert settings["model_dir"] == "/default/models"


def test_load_settings_persists_yaml(tmp_path):
    defaults = {
        "config_file": "/default/config.yaml",
        "model_dir": "/default/models",
        "docker_container_name": "llama-swap",
        "backup_dir": "/default/backups",
        "docs_dir": "/default/docs",
        "health_check_url": "http://localhost:8080/v1/models",
        "health_check_timeout": 30,
        "health_check_interval": 2,
        "log_dir": "/default/logs",
    }

    yaml_path = tmp_path / "llama-config.yaml"
    yaml_path.write_text("")

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        with patch("src.app._defaults", return_value=defaults):
            with patch("yaml.safe_load", return_value=None):
                settings = load_settings(Namespace(config_path="/cli/config.yaml"))

    assert yaml_path.exists()

    with open(yaml_path) as f:
        content = f.read()
    assert "config_file:" in content
    assert "/cli/config.yaml" in content


def test_poll_health_success(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client_ctx = MagicMock()
    mock_client_ctx.get.return_value = mock_resp

    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__enter__ = lambda s: mock_client_ctx

    monkeypatch.setattr("httpx.Client", mock_client_cls)

    poll_health("http://localhost:8000/docs", 10, 0.1)
    mock_client_cls.assert_called_once_with(verify=False)


def test_poll_health_timeout(monkeypatch):
    mock_client_ctx = MagicMock()
    mock_client_ctx.get.side_effect = Exception("connection refused")

    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__enter__ = lambda s: mock_client_ctx

    monkeypatch.setattr("httpx.Client", mock_client_cls)

    with patch("time.sleep"):
        with pytest.raises(Exception, match="Health check"):
            poll_health("http://localhost:8000/docs", 1, 0.1)


class Namespace:
    """Minimal namespace for CLI args — all attrs default to None."""

    config_path = None
    model_dir = None
    container = None
    backup_dir = None
    docs_dir = None
    health_url = None
    health_timeout = None
    health_interval = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
