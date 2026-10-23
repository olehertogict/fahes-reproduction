@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0" || exit /b 1

for %%T in (git uv g++) do (
    where %%T >nul 2>nul
    if errorlevel 1 (
        echo Missing required tool: %%T. See README.md for installation requirements.
        exit /b 1
    )
)

git submodule update --init || exit /b 1
uv sync --locked || exit /b 1
if exist "build\fahes" rmdir /s /q "build\fahes"
if exist "build\fahes" exit /b 1
uv run --locked pytest -q || exit /b 1
uv run --locked python run_experiments.py || exit /b 1
uv run --locked python make_tables.py || exit /b 1
