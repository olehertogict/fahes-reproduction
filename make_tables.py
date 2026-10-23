"""Turn results/raw/*.csv into the tables in results/results.md.

Precision and recall over distinct DMVs, i.e. distinct (column, value) pairs, as in the
paper (section 6.1): precision = true DMVs detected / pairs reported; recall = true DMVs
detected / all true DMVs. Values are compared after trimming spaces, numbers by their
numeric value ("0" equals "0.0").

  uv run python make_tables.py
"""
from pathlib import Path

import pandas as pd

RAW, OUT = Path("results/raw"), Path("results")
MODULES = ["all", "syntactic", "numerical", "random"]
LABELS = {"all": "FAHES", "syntactic": "syntactic module", "numerical": "numerical-outlier module",
          "random": "RandomDMVD module"}

# Paper, Table 5, row "UCI ML-Repo." (4 tables, not named): (precision, recall).
PAPER_UCI = {"all": (0.384, 0.952), "syntactic": (0.528, 0.905), "numerical": (0.833, 0.238),
             "random": (0.375, 0.429)}
# Paper, Table 6: FAHES running time in seconds.
PAPER_RUNTIME = {"Pima Ind. Dia.": 0.039, "Adult {UCI}": 11.070, "DOE H. School Perf.": 0.297,
                 "Avg. Daily Traf. Counts": 0.197, "Website Analytics": 0.638}


def canon_column(column):
    return str(column).replace("﻿", "").strip()


def canon_value(value):
    text = str(value).strip()
    try:
        return repr(float(text))
    except ValueError:
        return text


def as_set(df):
    return set(zip(df.column.map(canon_column), df.value.map(canon_value)))


def fmt(x, digits=3):
    return "–" if pd.isna(x) else f"{x:.{digits}f}"


def md(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def scores(detections, truth, experiment):
    """Reported, hits, precision and recall per (dataset, module)."""
    rows = []
    for dataset, true in truth[truth.experiment == experiment].groupby("dataset"):
        true_set = as_set(true)
        for module in MODULES:
            found = as_set(detections[(detections.experiment == experiment) & (detections.dataset == dataset)
                                      & (detections.module == module)])
            hits = len(found & true_set)
            rows.append({"dataset": dataset, "module": module, "reported": len(found), "hits": hits,
                         "truth": len(true_set), "precision": hits / len(found) if found else float("nan"),
                         "recall": hits / len(true_set)})
    return pd.DataFrame(rows)


def aggregate_scores(runs):
    """Macro = unweighted mean over datasets (precision only where something was reported);
    pooled = summed hits divided by summed reported or true DMVs."""
    hits, reported, truth = (runs[c].sum() for c in ("hits", "reported", "truth"))
    return {"macro_precision": runs.precision.mean(), "macro_recall": runs.recall.mean(),
            "precision_defined": int(runs.precision.notna().sum()), "n": len(runs),
            "pooled_precision": hits / reported if reported else float("nan"),
            "pooled_recall": hits / truth if truth else float("nan")}


def paper_examples_table(detections, truth):
    part = truth[truth.experiment == "paper_examples"]
    rows = []
    for t in part.itertuples(index=False):
        cells = []
        for module in MODULES:
            found = as_set(detections[(detections.experiment == "paper_examples") & (detections.dataset == t.dataset)
                                      & (detections.module == module)])
            cells.append("yes" if (canon_column(t.column), canon_value(t.value)) in found else "no")
        rows.append([t.dataset, t.column, f"`{t.value}`", t.kind, *cells])
    for dataset in part.dataset.unique():
        sub = detections[(detections.experiment == "paper_examples") & (detections.dataset == dataset)]
        rows.append([dataset, "", "", "*values reported*", *[len(as_set(sub[sub.module == m])) for m in MODULES]])
    return md(["dataset", "column", "DMV (paper Table 1)", "kind", *[LABELS[m] for m in MODULES]], rows)


def documented_table(s):
    rows = []
    for module in MODULES:
        m = s[s.module == module]
        a = aggregate_scores(m)
        per_dataset = "; ".join(f"{r.dataset} {fmt(r.precision, 2)}/{fmt(r.recall, 2)}" for r in m.itertuples())
        rows.append([LABELS[module], fmt(a["macro_precision"]), f"{a['precision_defined']}/{a['n']}",
                     fmt(a["macro_recall"]), fmt(a["pooled_precision"]), fmt(a["pooled_recall"]),
                     fmt(PAPER_UCI[module][0]), fmt(PAPER_UCI[module][1]), per_dataset])
    return md(["method", "macro precision", "datasets with a report", "macro recall", "pooled precision",
               "pooled recall", "paper precision (UCI row)", "paper recall (UCI row)",
               "per dataset: precision/recall"], rows)


def runtime_table(runs):
    part = runs[runs.experiment == "runtime"]
    rows = [[dataset, fmt(part[part.dataset == dataset].seconds.median()), fmt(paper)]
            for dataset, paper in PAPER_RUNTIME.items()]
    return md(["data set", "FAHES, ours (median of 5 runs)", "FAHES, paper"], rows)


def main():
    detections = pd.read_csv(RAW / "detections.csv", dtype=str, keep_default_na=False)
    truth = pd.read_csv(RAW / "truth.csv", dtype=str, keep_default_na=False)
    runs = pd.read_csv(RAW / "runs.csv")
    documented = scores(detections, truth, "documented")
    sections = [
        "# Results\n\nGenerated by `make_tables.py` from `results/raw/`. Precision and recall over distinct "
        "(column, value) pairs, as in the paper. A dash means undefined (nothing reported).",
        "## 1. Sample DMVs of the paper (Table 1) in the official data files\n\n"
        "yes = the DMV is among the values FAHES reports. These files contain more DMVs than the "
        "paper lists, so only recall is meaningful here.\n\n" + paper_examples_table(detections, truth),
        "## 2. UCI datasets with documented missing-value codes (compare: paper Table 5, UCI row)\n\n"
        "Ground truth = the documented codes. Other reported values are not labelled, so precision is "
        "a lower bound. Macro = mean over the 4 datasets (precision only over datasets where FAHES "
        "reported something); pooled = summed counts. The paper's UCI row covers 4 tables it does not "
        "name and does not say how it averages.\n\n" + documented_table(documented),
        "## 3. Running time in seconds (compare: paper Table 6)\n\n"
        "Different hardware than the paper.\n\n" + runtime_table(runs),
    ]
    OUT.mkdir(exist_ok=True)
    (OUT / "results.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    documented.to_csv(OUT / "scores.csv", index=False, encoding="utf-8")
    print((OUT / "results.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
