#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

for tool in git uv make g++; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Missing required tool: %s. See README.md for installation requirements.\n' "$tool" >&2
        exit 1
    fi
done

git submodule update --init
uv sync --locked
# Rebuild from the pinned source instead of reusing a previous generated binary.
rm -rf -- build/fahes
uv run --locked pytest -q
uv run --locked python run_experiments.py
uv run --locked python make_tables.py
