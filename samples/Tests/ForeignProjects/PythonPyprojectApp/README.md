# PythonPyprojectApp - foreign project test (pyproject.toml, src layout)

PEP 621 `pyproject.toml` with a `[project.scripts]` entry point, `src/` layout, `__main__.py`, unittest/pytest
tests and a VS Code `launch.json`. Open `pyproject.toml` (or the folder): targets `wordstat (entry point)`,
`python -m wordstat`, `tests`; F5 debugs with debugpy; Native menu: create .venv, pip install -e ., pytest.
