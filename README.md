# Prerequisites

- macOS or Linux; on Windows, use WSL.
- Git, Bash and [uv](https://docs.astral.sh/uv/getting-started/installation/).
- `make` and a C++ compiler available as `g++`:
  - macOS: install Xcode Command Line Tools with `xcode-select --install`.
  - Ubuntu/Debian: install `build-essential`.
- Internet access for the initial setup and dataset downloads.

Python 3.12.15 and the locked Python dependencies are installed automatically by uv.

# Reproduce the results

```bash
git clone --recurse-submodules https://github.com/olehertogict/fahes-reproduction.git
cd fahes-reproduction
bash reproduce.sh
```

This downloads the datasets, builds FAHES, runs the tests and all 61 experiments, and generates:

- `results/results.md`: result tables.
- `results/scores.csv`: precision and recall per dataset and module.
- `results/raw/`: detections, labels and run timings.

Execution takes several minutes and depends on the machine. Timings vary with hardware
and system load. Running the command again overwrites the generated results.
