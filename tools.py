"""Run the official FAHES binary (external/FAHES, unmodified) and read its output."""
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
FAHES_DATA = ROOT / "external" / "FAHES" / "Data"
FAHES_SRC = ROOT / "external" / "FAHES" / "src"
FAHES_BUILD = ROOT / "build" / "fahes"
FAHES_BIN = FAHES_BUILD / "FAHES"

# Tool ids of the official FAHES binary (external/FAHES/README.md).
FAHES_MODULES = {"syntactic": 1, "random": 2, "numerical": 3, "all": 4}


def build_fahes():
    """Compile the official code with its own makefile in build/fahes/ (outside the submodule)."""
    if not FAHES_BIN.exists():
        if not (FAHES_SRC / "makefile").is_file():
            raise RuntimeError("FAHES source is missing. Run: git submodule update --init")
        missing = [tool for tool in ("make", "g++") if shutil.which(tool) is None]
        if missing:
            raise RuntimeError(f"Missing build tools: {', '.join(missing)}. Install Xcode Command Line Tools "
                               "on macOS or build-essential on Debian/Ubuntu.")
        shutil.rmtree(FAHES_BUILD, ignore_errors=True)
        shutil.copytree(FAHES_SRC, FAHES_BUILD)
        try:
            subprocess.run(["make", "-s"], cwd=FAHES_BUILD, check=True, capture_output=True,
                           text=True, errors="replace")
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"FAHES compilation failed:\n{exc.stdout}\n{exc.stderr}") from exc
    return FAHES_BIN


def parse_fahes_output(path):
    """FAHES writes 'Table Name,Attribute Name,DMV,Frequency,Detecting Tool' without quoting;
    a DMV may itself contain commas, so the value is everything between the second field and
    the last two fields."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split(",")
        if len(parts) >= 5:
            rows.append({"column": parts[1], "value": ",".join(parts[2:-2]),
                         "frequency": int(parts[-2]), "tool": parts[-1]})
    return pd.DataFrame(rows, columns=["column", "value", "frequency", "tool"])


def run_fahes(csv_path, module="all"):
    """Run FAHES on a CSV; return the detected DMVs and the wall-clock time in seconds."""
    build_fahes()
    csv_path = Path(csv_path).resolve()
    with tempfile.TemporaryDirectory() as out_dir:
        start = time.perf_counter()
        proc = subprocess.run([str(FAHES_BIN), str(csv_path), out_dir + "/", str(FAHES_MODULES[module])],
                              capture_output=True, text=True, errors="replace")
        seconds = time.perf_counter() - start
        output = Path(out_dir) / f"DMV_{csv_path.name}"
        if proc.returncode != 0 or not output.exists():
            raise RuntimeError(f"FAHES failed on {csv_path.name}: {proc.stdout[-500:]} {proc.stderr[-500:]}")
        return parse_fahes_output(output), seconds
