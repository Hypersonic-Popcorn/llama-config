from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app

VALID_CONFIG = {
    "healthCheckTimeout": 500,
    "logLevel": "info",
    "models": {
        "my-model": {
            "cmd": "llama-server --port 8080",
            "name": "My Model",
        }
    },
}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_yaml():
    with patch("src.api.config_routes.read_config", return_value=VALID_CONFIG):
        yield


@pytest.fixture
def mock_validate():
    from src.core.validator import ValidationResult

    result = ValidationResult(valid=True)
    with patch("src.api.config_routes.validate_config", return_value=result):
        yield


@pytest.fixture
def mock_write():
    with patch("src.api.config_routes.write_config"):
        yield


@pytest.fixture
def mock_restart():
    with patch("src.api.config_routes.restart_container"):
        yield


@pytest.fixture
def mock_health():
    with patch(
        "src.api.config_routes._wait_for_health", new_callable=lambda: AsyncMock()
    ):
        yield


@pytest.fixture
def mock_rollback():
    with patch("src.api.config_routes._rollback"):
        yield


class TestConfigRoutes:
    def test_get_config(self, client, mock_yaml):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data == VALID_CONFIG

    def test_save_config_valid(
        self, client, mock_validate, mock_write, mock_restart, mock_health
    ):
        resp = client.post(
            "/api/config", json={"config": VALID_CONFIG, "label": "test"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["errors"] == []
        assert data["warnings"] == []

    def test_save_config_invalid(self, client):
        from src.core.validator import ValidationResult

        result = ValidationResult(valid=False)
        result.add_error("Missing models")
        result.add_warning("logLevel is not set")

        with patch("src.api.config_routes.validate_config", return_value=result):
            with patch("src.api.config_routes.write_config"):
                resp = client.post("/api/config", json={"config": {}, "label": "test"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert "Missing models" in data["errors"]

    def test_validate_config(self, client):
        from src.core.validator import ValidationResult

        result = ValidationResult(valid=False)
        result.add_error("Missing models")

        with patch("src.api.config_routes.validate_config", return_value=result):
            resp = client.post(
                "/api/config/validate", json={"config": {}, "label": "test"}
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert "Missing models" in data["errors"]

    def test_save_config_restart_fails(self, client, mock_validate):
        from src.custom_exceptions import ContainerNotRunning

        with patch("src.api.config_routes.write_config"):
            with patch(
                "src.api.config_routes.restart_container",
                side_effect=ContainerNotRunning("not running"),
            ):
                with patch(
                    "src.api.config_routes._wait_for_health",
                    new_callable=lambda: AsyncMock(),
                ):
                    resp = client.post("/api/config", json={"config": VALID_CONFIG})

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert "Container restart failed" in data["warnings"]

    def test_save_config_health_fails(
        self, client, mock_validate, mock_write, mock_restart
    ):
        with patch(
            "src.api.config_routes._wait_for_health", side_effect=Exception("timeout")
        ):
            with patch("src.api.config_routes._rollback"):
                resp = client.post("/api/config", json={"config": VALID_CONFIG})

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert "Container failed to start after config change" in data["errors"]

    def test_get_backups(self, client):
        with patch(
            "src.api.config_routes.list_backups",
            return_value=[
                {
                    "backup_id": "test.yaml",
                    "timestamp": "2024-01-01",
                    "label": "backup1",
                },
            ],
        ):
            resp = client.get("/api/config/backups")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["backups"]) == 1
        assert data["backups"][0]["backup_id"] == "test.yaml"

    def test_restore_backup(self, client):
        with patch("src.api.config_routes.restore_backup"):
            with patch("src.api.config_routes.restart_container"):
                resp = client.post("/api/config/restore/test.yaml")

        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestModelRoutes:
    def test_list_models(self, client):
        from src.api import model_routes

        model_routes._models_cache = [
            {
                "name": "test",
                "architecture": "llama",
                "context_length": 4096,
                "parameter_count": "7B",
                "quantization": "Q4_0",
                "file_size": 1234567,
                "filename": "test.gguf",
                "full_path": "/models/test.gguf",
                "size": 1234567,
                "quant": "Q4_0",
            }
        ]

        resp = client.get("/api/models")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "test"


class TestDockerRoutes:
    def test_status(self, client):
        with patch("src.api.docker_routes.container_is_running", return_value=True):
            resp = client.get("/api/docker/status")

        assert resp.status_code == 200
        assert resp.json() == "RUNNING"

    def test_restart(self, client):
        with patch("src.api.docker_routes.restart_container"):
            resp = client.post("/api/docker/restart")

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_logs(self, client):
        with patch("src.api.docker_routes.get_logs", return_value=["log1", "log2"]):
            resp = client.get("/api/docker/logs")

        assert resp.status_code == 200
        assert len(resp.json()["logs"]) == 2

    def test_health_healthy(self, client):
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            resp = client.get("/api/docker/health")

        assert resp.status_code == 200
        assert resp.json()["healthy"] is True

    def test_start(self, client):
        mock_container = MagicMock()
        with patch("src.api.docker_routes.get_container", return_value=mock_container):
            resp = client.post("/api/docker/start")

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_stop(self, client):
        mock_container = MagicMock()
        with patch("src.api.docker_routes.get_container", return_value=mock_container):
            resp = client.post("/api/docker/stop")

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_llama_swap_logs(self, client):
        with patch(
            "src.api.docker_routes.get_container_stdout_logs",
            return_value=["some logs here"],
        ):
            resp = client.get("/api/docker/llama-swap-logs")

        assert resp.status_code == 200
        assert resp.json() == {"logs": ["some logs here"]}


class TestOptionsRoutes:
    def test_get_server_options(self, client):
        cache = {"llama-server": [{"flag": "--port"}], "llama-swap": []}
        with patch("src.api.options_routes.load_options_cache", return_value=cache):
            resp = client.get("/api/options/llama-server")

        assert resp.status_code == 200
        assert len(resp.json()["llama_server"]) == 1

    def test_get_swap_options(self, client):
        cache = {"llama-server": [], "llama-swap": [{"flag": "logLevel"}]}
        with patch("src.api.options_routes.load_options_cache", return_value=cache):
            resp = client.get("/api/options/llama-swap")

        assert resp.status_code == 200
        assert len(resp.json()["llama_swap"]) == 1

    def test_refresh_options(self, client):
        with patch("src.api.options_routes.build_options_cache", return_value={}):
            resp = client.post("/api/options/refresh")

        assert resp.status_code == 200
        assert resp.json()["success"] is True
