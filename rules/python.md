Use pytest, not unittest.
Use fixtures for setup and teardown, not setUp/tearDown methods.
Ask before using mocks.
Test one behavior per test function.
Name test functions descriptively: test_<what it does>_<expected outcome>.
Use type hints on all function signatures.
Use f-strings for string formatting, not .format() or % formatting.
Use pathlib.Path for file paths, not os.path.
Do not use bare except clauses.
Catch specific exceptions only.
Do not swallow exceptions silently.
use uv run for all python commands.
Do not add docstrings unless asked to.
When writing tests, do not include them in a class unless the test is for a 
class in which case all tests for that class should be in a  single class
named test_<the name of the class being tested>.
imports should go at the top of the file even if only a single function uses
that import.
