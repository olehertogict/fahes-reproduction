# Prerequisites

- Git and [uv](https://docs.astral.sh/uv/getting-started/installation/).
- macOS/Linux: Bash, `make` and a C++ compiler available as `g++`:
  - macOS: install Xcode Command Line Tools with `xcode-select --install`.
  - Ubuntu/Debian: install `build-essential`.
- Windows 10/11 (x64): install [MSYS2](https://www.msys2.org/), then run
  `pacman -S mingw-w64-ucrt-x86_64-gcc` in its UCRT64 terminal. Add
  `C:\msys64\ucrt64\bin` to your Windows `PATH` and open a new terminal.
  WSL is not required.
- Internet access for the initial setup and dataset downloads.

Python 3.12.15 and the locked Python dependencies are installed automatically by uv.

# Reproduce the results

```bash
git clone --recurse-submodules https://github.com/olehertogict/fahes-reproduction.git
cd fahes-reproduction
```

macOS/Linux:

```bash
bash reproduce.sh
```

Windows (PowerShell or Command Prompt):

```powershell
.\reproduce.cmd
```

This downloads the datasets, builds FAHES, runs the tests and all 61 experiments, and generates:

- `results/results.md`: result tables.
- `results/scores.csv`: precision and recall per dataset and module.
- `results/raw/`: detections, labels and run timings.

A full run can take tens of minutes, depending on the machine. Timings vary with hardware
and system load. Running the command again overwrites the generated results.

## Manual fallback

If the script does not work, run these commands one at a time from the `fahes-reproduction`
folder. They work in Bash, PowerShell and Command Prompt. The same prerequisites apply;
stop if a command reports an error.

```text
git submodule update --init
uv sync --locked
uv run --locked python -c "from pathlib import Path; import shutil; p = Path('build/fahes'); shutil.rmtree(p) if p.exists() else None"
uv run --locked python -X utf8 -m pytest -q
uv run --locked python -X utf8 run_experiments.py
uv run --locked python -X utf8 make_tables.py
```
