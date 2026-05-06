from unittest.mock import MagicMock, patch

import pytest

from pathlib import Path

from src.app import config_dir, load_settings, parse_args, poll_health


def test_parse_args_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["app"])
    args = parse_args()
    assert args.command == "start"
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
            "-l",
            "/tmp/logs",
            "-u",
            "http://localhost:9999",
            "--health-timeout",
            "60",
            "--health-interval",
            "5",
        ],
    )
    args = parse_args()

    assert args.command == "start"
    assert args.config_path == "/tmp/config.yaml"
    assert args.model_dir == "/tmp/models"
    assert args.container == "my-container"
    assert args.backup_dir == "/tmp/backups"
    assert args.docs_dir == "/tmp/docs"
    assert args.log_dir == "/tmp/logs"
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
        with patch("src.app.config_dir", return_value=tmp_path):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("yaml.safe_load", return_value=None):
                    settings = load_settings(Namespace())

    assert settings["config_file"] == "/default/config.yaml"
    assert settings["model_dir"] == "/default/models"


def test_config_dir_default(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    result = config_dir()
    assert result == Path.home() / ".config" / "llama-config"


def test_config_dir_with_xdg(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    result = config_dir()
    assert result == Path("/custom/config/llama-config")


def test_parse_args_init_subcommand(monkeypatch):
    monkeypatch.setattr("sys.argv", ["app", "init"])
    args = parse_args()
    assert args.command == "init"


def test_parse_args_start_default(monkeypatch):
    monkeypatch.setattr("sys.argv", ["app"])
    args = parse_args()
    assert args.command == "start"


def test_parse_args_log_dir_short(monkeypatch):
    monkeypatch.setattr("sys.argv", ["app", "-l", "/custom/logs"])
    args = parse_args()
    assert args.log_dir == "/custom/logs"


def test_parse_args_log_dir_long(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["app", "--log-dir", "/custom/logs"],
    )
    args = parse_args()
    assert args.log_dir == "/custom/logs"


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
        with patch("src.app.config_dir", return_value=tmp_path):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("yaml.safe_load", return_value=file_data):
                    settings = load_settings(Namespace())

    assert settings["config_file"] == "/yaml/config.yaml"
    assert settings["model_dir"] == "/default/models"
    assert settings["log_dir"] == "/default/logs"


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
                settings = load_settings(
                    Namespace(config_path="/cli/config.yaml", log_dir=None)
                )

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

    with patch("src.app.config_dir", return_value=tmp_path):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("yaml.safe_load", return_value=None):
                settings = load_settings(
                    Namespace(config_path="/cli/config.yaml", log_dir=None)
                )

    assert settings["config_file"] == "/cli/config.yaml"


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


def test_save_settings_writes_yaml(tmp_path):
    from src.app import save_settings

    settings = {
        "config_file": "config.yaml",
        "model_dir": "models",
        "docker_container_name": "llama-swap",
        "backup_dir": "backups",
        "docs_dir": "docs",
        "health_check_url": "http://localhost:8000",
        "health_check_timeout": 30,
        "health_check_interval": 2,
        "log_dir": "logs",
    }
    path = tmp_path / "llama-config.yaml"

    save_settings(settings, path)

    assert path.exists()
    with open(path) as f:
        content = f.read()
    assert "config_file: config.yaml" in content
    assert "model_dir: models" in content


def test_collect_cli_args_all_valid(monkeypatch, tmp_path):
    from src.app import _collect_cli_args

    model_dir = tmp_path / "models"
    model_dir.mkdir()

    args = Namespace(
        config_path=None,
        model_dir=str(model_dir),
        container=None,
        backup_dir=None,
        docs_dir=None,
        log_dir=None,
        health_url=None,
        health_timeout=None,
        health_interval=None,
    )

    result = _collect_cli_args(args)
    assert result == {"model_dir": str(model_dir)}


def test_collect_cli_args_invalid_exits(tmp_path):
    from src.app import _collect_cli_args

    with pytest.raises(SystemExit):
        _collect_cli_args(
            Namespace(config_path="/nonexistent/config.yaml", log_dir=None)
        )


def test_collect_cli_args_invalid_model_dir(tmp_path):
    from src.app import _collect_cli_args

    with pytest.raises(SystemExit):
        _collect_cli_args(
            Namespace(config_path=None, model_dir="/nonexistent/models", log_dir=None)
        )


def test_run_init_prompts_and_creates_dirs(tmp_path, monkeypatch):
    from src.app import config_dir, run_init

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda prompt: "" if False else "")

    settings = {
        "config_file": "config.yaml",
        "model_dir": "models",
        "docs_dir": "docs",
        "backup_dir": "backups",
        "log_dir": "logs",
        "docker_container_name": "llama-swap",
        "health_check_url": "http://localhost:8000",
        "health_check_timeout": 30,
        "health_check_interval": 2,
    }

    class FakeArgs:
        command = "init"
        config_path = None
        model_dir = None
        container = None
        backup_dir = None
        docs_dir = None
        log_dir = None
        health_url = None
        health_timeout = None
        health_interval = None

    settings = run_init(settings, FakeArgs())

    config_p = config_dir()
    assert config_p.exists()


def test_run_init_uses_cli_overrides(tmp_path, monkeypatch):
    from src.app import config_dir, run_init

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    settings = {
        "config_file": "config.yaml",
        "model_dir": "models",
        "docs_dir": "docs",
        "backup_dir": "backups",
        "log_dir": "logs",
        "docker_container_name": "llama-swap",
        "health_check_url": "http://localhost:8000",
        "health_check_timeout": 30,
        "health_check_interval": 2,
    }

    model_dir = tmp_path / "models"
    model_dir.mkdir()

    class FakeArgs:
        def __init__(self):
            self.command = "init"
            self.config_path = None
            self.model_dir = str(model_dir)
            self.container = "custom-container"
            self.backup_dir = None
            self.docs_dir = None
            self.log_dir = None
            self.health_url = None
            self.health_timeout = None
            self.health_interval = None

    with patch("builtins.input", return_value=""):
        settings = run_init(settings, FakeArgs())

    assert settings["model_dir"] == str(model_dir)
    assert settings["docker_container_name"] == "custom-container"


class Namespace:
    """Minimal namespace for CLI args — all attrs default to None."""

    config_path = None
    model_dir = None
    container = None
    backup_dir = None
    docs_dir = None
    log_dir = None
    health_url = None
    health_timeout = None
    health_interval = None
    command = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
