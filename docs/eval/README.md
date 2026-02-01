# Evaluation assets

This directory contains datasets and outputs used for retrieval-augmented generation (RAG) evaluation.

## Contents
- `rag_eval_queries.jsonl` — baseline query set with optional expected CELEX identifiers.
- `results/` — generated outputs from `apps/api/scripts/rag_benchmark.py`.

## Running the benchmark
```bash
python apps/api/scripts/rag_benchmark.py
```

The default output path is `docs/eval/results/rag_eval_results.jsonl`.
