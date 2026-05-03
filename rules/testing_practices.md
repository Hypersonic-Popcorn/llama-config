# Testing Practices

## General Approach

This project uses `pytest` with `pytest-mock` and `pytest-cov` for testing.
Tests live alongside the code they test in a `tests/` directory mirroring the
`src/` structure.

## Test-First Workflow

Write tests before writing the implementation:

1. Write a failing test that describes the expected behavior
2. Write the minimum implementation to make it pass
3. Refactor if needed — tests should still pass
4. When a bug is discovered, write a failing test that catches it first,
   then fix the bug

This ensures tests reflect real requirements rather than being written to match
whatever the implementation happens to do.

## What to Test

Always write tests for:

- Every public function — at minimum one happy path test
- Every meaningful branch — if both paths of an if/else do something different,
  test both
- Every exception the function can raise — test that it raises correctly under
  the right conditions
- Edge cases realistic to the domain — empty directories, malformed YAML,
  container not found, etc.

## What Not to Test

Skip tests for:

- `settings.py` — it is a data class with no logic
- Simple pass-through functions with no branching logic
- `__init__.py` files
- Private helper functions already exercised by tests of the public functions
  that call them
- Single logging statements inside exception handlers that are unreachable
  without highly contrived mock setups

## Mocking

Use `pytest-mock` and `unittest.mock` for all external dependencies:

- **Always mock the Docker client** — tests must never require a running
  Docker container
- **Always mock file I/O** — tests must never read or write real files on disk
- **Patch at the right location** — patch where the name is used, not where
  it is defined:

```python
# Correct — patch where docker_manager imports it
mocker.patch("src.core.docker_manager.docker.DockerClient.from_env")

# Wrong — patches the original, not the reference in the module under test
mocker.patch("docker.DockerClient.from_env")
```

- Verify not just return values but that mocked methods were called with the
  right arguments using `assert_called_once_with()`

## Coverage

Target coverage is **80-90%**. Do not chase 100%.

The coverage report is a tool for spotting gaps, not a metric to optimize.
Ask this question about each uncovered line: *"If this line had a bug, would
a user notice something wrong?"* If yes, write the test. If no, leave it.

Remaining uncovered lines at the end of a module are acceptable if they are:
- Defensive exception handlers reachable only through unlikely SDK failures
- Logging statements inside except blocks
- Code paths that require contorted mocks to reach

## Bug Fix Workflow

When a bug is discovered:

1. Write a failing test that reproduces the bug
2. Confirm the test fails
3. Fix the bug
4. Confirm the test now passes
5. The test stays permanently as a regression guard

## When to Stop Writing Tests

Stop adding tests for a module when:

- All public functions have happy path coverage
- All exception paths are tested
- All meaningful branches are covered
- Coverage is in the 80-90%+ range

Resume writing tests when:

- A new function is added → test it before or alongside implementation
- A bug is found → test it before fixing
- A refactor changes behavior → update or add tests to match
