"""
RAG benchmark runner.

Runs retrieval once per question, then optionally asks multiple LLM providers to
answer from the same context. Outputs JSONL + summary stats.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import httpx

from src.ai.rag_service import RAGService
from src.search import search_rag_chunks

OPENAI_RETRIES = 0
OPENAI_BACKOFF = 2.0
OPENAI_DELAY = 0.0
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DEFAULT_QUERIES_PATH = os.path.join(REPO_ROOT, "docs", "eval", "rag_eval_queries.jsonl")
DEFAULT_OUTPUT_PATH = os.path.join(REPO_ROOT, "docs", "eval", "results", "rag_eval_results.jsonl")


@dataclass
class ProviderResult:
    provider: str
    answer: Optional[str]
    error: Optional[str]
    latency_s: float


def load_queries(path: Optional[str]) -> List[Dict[str, Any]]:
    if not path:
        path = DEFAULT_QUERIES_PATH
    queries: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))
    return queries


def build_prompt(question: str, chunks: List[Dict[str, Any]]) -> str:
    rag = RAGService()
    return rag._build_rag_prompt(question, chunks)


def run_anthropic(prompt: str) -> ProviderResult:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return ProviderResult("anthropic", None, "missing ANTHROPIC_API_KEY", 0.0)

    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
    start = time.time()
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=1200,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = message.content[0].text if message.content else ""
        return ProviderResult("anthropic", answer, None, time.time() - start)
    except Exception as exc:
        return ProviderResult("anthropic", None, str(exc), time.time() - start)


def run_openai_compatible(prompt: str) -> ProviderResult:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1")

    if not api_key:
        return ProviderResult("openai", None, "missing OPENAI_API_KEY", 0.0)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1200,
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    start = time.time()
    for attempt in range(OPENAI_RETRIES + 1):
        try:
            response = httpx.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            if response.status_code == 429 and attempt < OPENAI_RETRIES:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    sleep_s = float(retry_after)
                else:
                    sleep_s = OPENAI_BACKOFF * (2**attempt)
                time.sleep(sleep_s)
                continue
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return ProviderResult("openai", answer, None, time.time() - start)
        except Exception as exc:
            if attempt < OPENAI_RETRIES:
                time.sleep(OPENAI_BACKOFF * (2**attempt))
                continue
            return ProviderResult("openai", None, str(exc), time.time() - start)
    # Should not reach here, but mypy requires a return
    return ProviderResult("openai", None, "unexpected control flow", 0.0)


def iter_providers(names: Iterable[str], prompt: str) -> List[ProviderResult]:
    results: List[ProviderResult] = []
    for name in names:
        name = name.strip().lower()
        if name in {"anthropic", "claude"}:
            results.append(run_anthropic(prompt))
        elif name in {"openai", "openai-compatible", "oai"}:
            results.append(run_openai_compatible(prompt))
        elif name in {"none", "retrieval"}:
            results.append(ProviderResult("retrieval", "", None, 0.0))
        else:
            results.append(ProviderResult(name, None, "unknown provider", 0.0))
    return results


def evaluate_retrieval(
    chunks: List[Dict[str, Any]], expected: Optional[List[str]]
) -> Dict[str, Any]:
    if not expected:
        return {"expected_hit": None, "expected_celex": None}

    retrieved = {c.get("celex") for c in chunks if c.get("celex")}
    expected_set = set(expected)
    return {
        "expected_celex": list(expected_set),
        "expected_hit": bool(retrieved.intersection(expected_set)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", help="Path to JSONL queries")
    parser.add_argument("--providers", default="anthropic,openai", help="Comma-separated providers")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Output JSONL file")
    parser.add_argument("--retries", type=int, default=0, help="Retries for 429 errors")
    parser.add_argument("--backoff", type=float, default=2.0, help="Backoff base seconds")
    parser.add_argument(
        "--delay", type=float, default=0.0, help="Delay between questions (seconds)"
    )
    args = parser.parse_args()

    global OPENAI_RETRIES, OPENAI_BACKOFF, OPENAI_DELAY
    OPENAI_RETRIES = max(0, args.retries)
    OPENAI_BACKOFF = max(0.1, args.backoff)
    OPENAI_DELAY = max(0.0, args.delay)

    queries = load_queries(args.queries)
    if args.limit:
        queries = queries[: args.limit]

    provider_names = [p.strip() for p in args.providers.split(",") if p.strip()]

    total = 0
    expected_hits = 0
    written = 0

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as handle:
        for item in queries:
            question = item.get("question")
            if not question:
                continue

            try:
                chunks = search_rag_chunks(q=question, size=8).get("results", [])
                retrieval_error = None
            except Exception as exc:
                chunks = []
                retrieval_error = str(exc)

            prompt = build_prompt(question, chunks)

            eval_meta = evaluate_retrieval(chunks, item.get("expected_celex"))
            if eval_meta.get("expected_hit") is True:
                expected_hits += 1
            if eval_meta.get("expected_hit") is not None:
                total += 1

            provider_results = iter_providers(provider_names, prompt)
            for result in provider_results:
                payload = {
                    "question_id": item.get("id"),
                    "question": question,
                    "provider": result.provider,
                    "answer": result.answer,
                    "error": result.error or retrieval_error,
                    "latency_s": round(result.latency_s, 3),
                    "retrieved_celex": [c.get("celex") for c in chunks if c.get("celex")],
                    "retrieved_chunks": len(chunks),
                    "retrieved_titles": [c.get("title") for c in chunks if c.get("title")],
                }
                payload.update(eval_meta)
                handle.write(json.dumps(payload) + "\n")
                written += 1

            if OPENAI_DELAY:
                time.sleep(OPENAI_DELAY)

    hit_rate = (expected_hits / total) * 100 if total else 0.0
    print(f"✅ Wrote {written} rows to {args.output}")
    if total:
        print(f"Retrieval expected-hit rate: {expected_hits}/{total} ({hit_rate:.1f}%)")
    else:
        print("No expected_celex provided; retrieval hit rate skipped.")


if __name__ == "__main__":
    main()
