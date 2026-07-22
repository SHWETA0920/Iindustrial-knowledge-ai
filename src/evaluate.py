"""
MODULE 15: EVALUATION METRICS
-----------------------------
Runs a lightweight benchmark over query_answer() using a JSON file of labeled
questions. Metrics focus on hackathon demo value:
- average response time
- source precision@K
- expected keyword coverage in the answer
"""

import json
import os
import sys
import time

from query import query_answer

BENCHMARK_PATH = "data/eval_questions.json"
EXAMPLE_BENCHMARK_PATH = "data/eval_questions.example.json"


def _load_benchmark():
    if os.path.exists(BENCHMARK_PATH):
        path = BENCHMARK_PATH
    elif os.path.exists(EXAMPLE_BENCHMARK_PATH):
        path = EXAMPLE_BENCHMARK_PATH
    else:
        return None, None

    with open(path, "r") as f:
        items = json.load(f)
    return path, items


def score_case(case, result):
    expected_sources = set(case.get("expected_sources", []))
    expected_keywords = [k.lower() for k in case.get("expected_keywords", [])]

    returned_sources = [s.get("source") for s in result.get("sources", [])]
    if returned_sources:
        precision_at_k = len([s for s in returned_sources if s in expected_sources]) / len(returned_sources)
    else:
        precision_at_k = 0.0

    answer_lower = result.get("answer", "").lower()
    keyword_hits = len([k for k in expected_keywords if k in answer_lower])
    keyword_recall = keyword_hits / len(expected_keywords) if expected_keywords else 1.0

    return {
        "precision_at_k": round(precision_at_k, 3),
        "keyword_recall": round(keyword_recall, 3),
        "matched_sources": [s for s in returned_sources if s in expected_sources],
        "matched_keywords": [k for k in expected_keywords if k in answer_lower],
    }


def run_benchmark(limit=None):
    path, cases = _load_benchmark()
    if not cases:
        return {
            "status": "not_configured",
            "message": "Add data/eval_questions.json to run evaluation. An example file is included as data/eval_questions.example.json.",
        }

    if limit:
        cases = cases[:limit]

    results = []
    for case in cases:
        start = time.perf_counter()
        response = query_answer(case["question"])
        latency = time.perf_counter() - start
        scores = score_case(case, response)
        results.append({
            "question": case["question"],
            "latency_seconds": round(latency, 2),
            "precision_at_k": scores["precision_at_k"],
            "keyword_recall": scores["keyword_recall"],
            "matched_sources": scores["matched_sources"],
            "matched_keywords": scores["matched_keywords"],
            "returned_sources": [s.get("source") for s in response.get("sources", [])],
        })

    avg_latency = round(sum(r["latency_seconds"] for r in results) / len(results), 2)
    avg_precision = round(sum(r["precision_at_k"] for r in results) / len(results), 3)
    avg_keyword_recall = round(sum(r["keyword_recall"] for r in results) / len(results), 3)

    return {
        "status": "ok",
        "benchmark_file": path,
        "questions_evaluated": len(results),
        "average_latency_seconds": avg_latency,
        "average_source_precision_at_k": avg_precision,
        "average_keyword_recall": avg_keyword_recall,
        "details": results,
    }


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(json.dumps(run_benchmark(limit=limit), indent=2))
