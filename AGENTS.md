## How to run

```
uv run pytest
uv run black .
```

## Architecture

For frontend,read and follow: @plan_frontend.md
For the backend, read and follow: @plan_backend.md

## Gotchas

- **Package manager**: use `uv` — not pip, poetry, or pdm. Run `uv sync` after pulling.
- **No conftest.py** — all fixtures are defined in individual test files.
- **Follow the .python-version for python syntax**

## Coding conventions

When working with Python code, read and follow: @rules/python.md
When working on the frontend read and follow: @rules/frontend.md
Nothing in the local_test directory should be staged or committed to git.
