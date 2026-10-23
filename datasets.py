"""Datasets and ground truth for the FAHES reproduction.

* PAPER_EXAMPLES: data files shipped with the official FAHES code that contain the sample
  DMVs of the paper's Table 1. Ground truth = those sample DMVs; other DMVs in these files
  are not labelled, so only recall is meaningful.
* DOCUMENTED: UCI datasets whose documentation states how missing values are encoded.
  Ground truth = the documented codes; undocumented DMVs may exist, so precision is a lower
  bound.
* RUNTIME_FILES: the data files of the paper's Table 6 that ship with the official code.

Ground truth is a list of (column, value, kind) tuples.
"""
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
FAHES_DATA = ROOT / "external" / "FAHES" / "Data"
DATA_DIR = ROOT / "data"

PAPER_EXAMPLES = {
    "pima": ("pima-indians-diabetes.csv", [("Diastolic blood pressure", "0", "numerical")]),
    "adult": ("adult.csv", [("workclass", "?", "syntactic"), ("education", "Some-college", "inlier")]),
    "aers": ("AERS.csv", [("EVENT_DT", "20010101", "inlier"), ("EVENT_DT", "20030101", "inlier")]),
    "vendor_location": ("10151-1.csv", [("Ref_ID", "-1", "numerical")]),
    # The paper names the attribute "Regents Num"; three columns of the file match.
    "graduation": ("16834-1.csv", [(c, v, "syntactic") for c in ("Total Regents Num", "Advanced Regents Num",
                                                                 "Regents w/o Advanced Num") for v in ("s", "-")]),
}

RUNTIME_FILES = {
    "Pima Ind. Dia.": "pima-indians-diabetes.csv",
    "Adult {UCI}": "adult.csv",
    "DOE H. School Perf.": "3397-1.csv",
    "Avg. Daily Traf. Counts": "356-1.csv",
    "Website Analytics": "5134-1.csv",
}

# name: (UCI id, archive name, data file, column names, read_csv options, documented DMVs)
DOCUMENTED = {
    # agaricus-lepiota.names: 2480 missing values, denoted by "?", all for attribute #11.
    "mushroom": (73, "mushroom", "agaricus-lepiota.data",
                 ["class", "cap-shape", "cap-surface", "cap-color", "bruises", "odor", "gill-attachment",
                  "gill-spacing", "gill-size", "gill-color", "stalk-shape", "stalk-root",
                  "stalk-surface-above-ring", "stalk-surface-below-ring", "stalk-color-above-ring",
                  "stalk-color-below-ring", "veil-type", "veil-color", "ring-number", "ring-type",
                  "spore-print-color", "population", "habitat"],
                 {}, [("stalk-root", "?")]),
    # breast-cancer-wisconsin.names: 16 instances with a single missing value, denoted by "?".
    "breast_w": (15, "breast+cancer+wisconsin+original", "breast-cancer-wisconsin.data",
                 ["id", "clump_thickness", "cell_size_uniformity", "cell_shape_uniformity", "marginal_adhesion",
                  "single_epithelial_cell_size", "bare_nuclei", "bland_chromatin", "normal_nucleoli",
                  "mitoses", "class"],
                 {}, [("bare_nuclei", "?")]),
    # auto-mpg.names: horsepower has 6 missing values (encoded as "?" in auto-mpg.data).
    "auto_mpg": (9, "auto+mpg", "auto-mpg.data",
                 ["mpg", "cylinders", "displacement", "horsepower", "weight", "acceleration", "model_year",
                  "origin", "car_name"],
                 {"sep": r"\s+", "quotechar": '"'}, [("horsepower", "?")]),
    # crx.names: missing values ("?") in A1, A2, A4, A5, A6, A7 and A14.
    "crx": (27, "credit+approval", "crx.data", [f"A{i}" for i in range(1, 17)],
            {}, [(c, "?") for c in ("A1", "A2", "A4", "A5", "A6", "A7", "A14")]),
}

# SHA256 of the original UCI data files used for the saved experiments.
DATA_SHA256 = {
    "mushroom": "e65d082030501a3ebcbcd7c9f7c71aa9d28fdfff463bf4cf4716a3fe13ac360e",
    "breast_w": "402c585309c399237740f635ef9919dc512cca12cbeb20de5e563a4593f22b64",
    "auto_mpg": "48b830e11feee5572525f8f1691ddb9d38d3d7b7063edcd8fca672c2a5e17d8d",
    "crx": "fff49bc186cbddb3ace7371d40d9fbbb3af4f126019c13ff3f562249b1454f4d",
}


def paper_example(name):
    filename, truth = PAPER_EXAMPLES[name]
    return FAHES_DATA / filename, truth


def documented(name):
    """Download the UCI dataset (once), write it as a CSV with a header, return path and truth."""
    uci_id, archive_name, filename, columns, options, codes = DOCUMENTED[name]
    folder = DATA_DIR / "uci" / name
    source = folder / filename
    if not source.is_file():
        url = f"https://archive.ics.uci.edu/static/public/{uci_id}/{archive_name}.zip"
        with urllib.request.urlopen(url, timeout=60) as response:
            archive = zipfile.ZipFile(io.BytesIO(response.read()))
        folder.mkdir(parents=True, exist_ok=True)
        archive.extractall(folder)
    if hashlib.sha256(source.read_bytes()).hexdigest() != DATA_SHA256[name]:
        raise ValueError(f"SHA256 mismatch for {source}; expected the data used in the saved experiments. "
                         "Remove this cached file and retry to download it again.")
    df = pd.read_csv(source, header=None, names=columns, dtype=str, **options)
    path = DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    return path, [(column, value, "syntactic") for column, value in codes]
