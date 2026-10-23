"""Run all FAHES experiments and write the raw results to results/raw/ (about 10–20 minutes).

  uv run python run_experiments.py

  paper_examples  official data files that contain the sample DMVs of the paper's Table 1
  documented      UCI datasets with documented missing-value codes
  runtime         the data files of the paper's Table 6 that ship with the official code

Each FAHES run adds a row to runs.csv and one row per detected DMV to detections.csv;
truth.csv holds the ground truth.
"""
import csv
from pathlib import Path

import datasets as D
from tools import FAHES_DATA, FAHES_MODULES, run_fahes

RAW = Path("results/raw")
RUNTIME_REPETITIONS = 5


def write(path, rows, fields):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    cases = [("paper_examples", name, *D.paper_example(name)) for name in D.PAPER_EXAMPLES]
    cases += [("documented", name, *D.documented(name)) for name in D.DOCUMENTED]
    jobs = [(e, d, path, module, 0) for e, d, path, _ in cases for module in FAHES_MODULES]
    jobs += [("runtime", d, FAHES_DATA / f, "all", rep) for d, f in D.RUNTIME_FILES.items()
             for rep in range(RUNTIME_REPETITIONS)]

    runs, detections = [], []
    for experiment, dataset, path, module, repetition in jobs:
        found, seconds = run_fahes(path, module)
        base = {"experiment": experiment, "dataset": dataset, "module": module, "repetition": repetition}
        runs.append({**base, "seconds": round(seconds, 4), "n_detected": len(found)})
        detections += [{**base, **row} for row in found.to_dict("records")]
        print(f"{experiment:15s} {dataset:24s} {module:10s} rep {repetition}  {len(found):3d} DMVs  {seconds:7.3f}s",
              flush=True)

    write(RAW / "runs.csv", runs, ["experiment", "dataset", "module", "repetition", "seconds", "n_detected"])
    write(RAW / "detections.csv", detections,
          ["experiment", "dataset", "module", "repetition", "column", "value", "frequency", "tool"])
    write(RAW / "truth.csv", [{"experiment": e, "dataset": d, "column": c, "value": v, "kind": k}
                              for e, d, _, truth in cases for c, v, k in truth],
          ["experiment", "dataset", "column", "value", "kind"])


if __name__ == "__main__":
    main()
