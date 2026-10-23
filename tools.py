"""Run the official FAHES binary (external/FAHES, unmodified) and read its output."""
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
FAHES_DATA = ROOT / "external" / "FAHES" / "Data"
FAHES_SRC = ROOT / "external" / "FAHES" / "src"
FAHES_BUILD = ROOT / "build" / "fahes"
WINDOWS = sys.platform == "win32"
FAHES_BIN = FAHES_BUILD / ("FAHES.exe" if WINDOWS else "FAHES")

# Tool ids of the official FAHES binary (external/FAHES/README.md).
FAHES_MODULES = {"syntactic": 1, "random": 2, "numerical": 3, "all": 4}


def build_fahes():
    """Build outside the submodule; use native MinGW-w64 on Windows."""
    if not FAHES_BIN.exists():
        if not (FAHES_SRC / "makefile").is_file():
            raise RuntimeError("FAHES source is missing. Run: git submodule update --init")
        required = ("g++",) if WINDOWS else ("make", "g++")
        missing = [tool for tool in required if shutil.which(tool) is None]
        if missing:
            raise RuntimeError(f"Missing build tools: {', '.join(missing)}. Install Xcode Command Line Tools "
                               "on macOS, build-essential on Debian/Ubuntu, or MSYS2 UCRT64 GCC on Windows.")
        shutil.rmtree(FAHES_BUILD, ignore_errors=True)
        shutil.copytree(FAHES_SRC, FAHES_BUILD)
        try:
            if WINDOWS:
                # Supply the Unix type alias and filesystem call absent in MinGW.
                # The pinned source and detection algorithms stay unchanged.
                (FAHES_BUILD / "windows_compat.h").write_text(
                    "#include <cstdlib>\n"
                    "using ushort = unsigned short;\n"
                    "#define realpath(path, buffer) _fullpath(buffer, path, 0)\n",
                    encoding="utf-8")
                sources = sorted(FAHES_BUILD.glob("*.cpp"))
                objects = [source.with_suffix(".o").name for source in sources]
                for source, obj in zip(sources, objects):
                    subprocess.run(["g++", "-std=c++11", "-O0",
                                    "-include", "windows_compat.h",
                                    "-c", source.name, "-o", obj],
                                   cwd=FAHES_BUILD, check=True, capture_output=True,
                                   text=True, errors="replace")
                # Match the original makefile: unoptimized objects, -O3 only at link time.
                subprocess.run(["g++", "-std=c++11", "-O3", *objects, "-o", FAHES_BIN.name],
                               cwd=FAHES_BUILD, check=True, capture_output=True,
                               text=True, errors="replace")
            else:
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
        proc = subprocess.run([str(FAHES_BIN), csv_path.as_posix(), Path(out_dir).as_posix() + "/",
                               str(FAHES_MODULES[module])],
                              capture_output=True, text=True, errors="replace")
        seconds = time.perf_counter() - start
        output = Path(out_dir) / f"DMV_{csv_path.name}"
        if proc.returncode != 0 or not output.exists():
            raise RuntimeError(f"FAHES failed on {csv_path.name}: {proc.stdout[-500:]} {proc.stderr[-500:]}")
        return parse_fahes_output(output), seconds
