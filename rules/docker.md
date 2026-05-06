# Docker Python Package — Container Timestamps

## Overview

Use the `docker` Python package to inspect when a container was last started, created, or stopped.

## Installation

```bash
uv add docker
```

## Getting Container Timestamps

```python
import docker

client = docker.from_env()
container = client.containers.get("your_container_name_or_id")

# When the container was last started
started_at = container.attrs["State"]["StartedAt"]

# When the container was created
created_at = container.attrs["Created"]

# When the container last stopped (empty if still running)
finished_at = container.attrs["State"]["FinishedAt"]
```

## Parsing Timestamps

Docker timestamps are ISO 8601 strings with nanosecond precision. Truncate to microseconds for Python's `datetime`:

```python
from datetime import datetime, timezone

def parse_docker_time(ts: str) -> datetime:
    ts = ts[:26] + "Z"
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

started = parse_docker_time(container.attrs["State"]["StartedAt"])
age = datetime.now(timezone.utc) - started
```

## List All Containers with Last Start Time

```python
import docker
from datetime import datetime, timezone

client = docker.from_env()

for container in client.containers.list(all=True):  # all=True includes stopped containers
    started_at = container.attrs["State"]["StartedAt"]
    status = container.attrs["State"]["Status"]
    print(f"{container.name:<30} status={status:<10} started={started_at}")
```

## Key Timestamp Fields

| Field | Description |
|---|---|
| `attrs["Created"]` | When the container was first created |
| `attrs["State"]["StartedAt"]` | When it was last started |
| `attrs["State"]["FinishedAt"]` | When it last stopped (`0001-01-01` if still running) |

## Checking Image Age

There is no single "last updated" field. To detect image changes, compare the container's image SHA against the image's creation time:

```python
image_id = container.attrs["Image"]
image = client.images.get(image_id)
image_created = image.attrs["Created"]
```
