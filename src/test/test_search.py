"""
Search quality test — sends real queries through the full pipeline
(embed → pgvector top 50 → AI rerank → top 5) and evaluates whether
the returned listings actually match what a user would expect.

Usage:
    python test_search.py              # run all test queries
    python test_search.py "iphone 13"  # run a single query
"""

import asyncio
import sys
import json
from datetime import datetime
from typing import Any, Dict, List

from src.database.connection import init_db
from src.search_engine import get_search_engine

# ---------------------------------------------------------------------------
# Test queries — each has a query and keywords we'd expect to see in a good result.
# "must_contain_any" = at least one of these tokens should appear in relevant text.
# "category" = human-readable label for grouping.
# ---------------------------------------------------------------------------

TEST_QUERIES: List[Dict[str, Any]] = [
    {
        "query": "iphone 13",
        "category": "electronics",
        "must_contain_any": ["iphone", "айфон", "ayfon", "apple"],
    },
    {
        "query": "kvartira toshkentda",
        "category": "real_estate",
        "must_contain_any": ["kvartira", "xonadon", "квартир", "uy", "toshkent", "ташкент"],
    },
    {
        "query": "lacetti mashina",
        "category": "vehicles",
        "must_contain_any": ["lacetti", "lasetti", "chevrolet", "mashina", "avto", "машин"],
    },
    {
        "query": "ноутбук",
        "category": "electronics",
        "must_contain_any": ["ноутбук", "noutbuk", "laptop", "notebook", "lenovo", "hp", "asus", "acer", "macbook"],
    },
    {
        "query": "ishchi kerak",
        "category": "jobs",
        "must_contain_any": ["ish", "ishchi", "работ", "вакан", "kerak", "hodim"],
    },
    {
        "query": "samsung telefon",
        "category": "electronics",
        "must_contain_any": ["samsung", "самсунг", "galaxy", "telefon", "телефон"],
    },
    {
        "query": "arenda kvartira",
        "category": "real_estate",
        "must_contain_any": ["arenda", "ijara", "аренд", "kvartira", "квартир", "xonadon"],
    },
    {
        "query": "велосипед",
        "category": "other",
        "must_contain_any": ["велосипед", "velosiped", "bike"],
    },
]

# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------

def score_result(result: Dict[str, Any], keywords: List[str]) -> Dict[str, Any]:
    """Score a single result against expected keywords.

    Returns dict with match info:
      keyword_hit  — True if any expected keyword found in raw_text
      similarity   — cosine similarity from pgvector (0..1)
      snippet      — first 120 chars of raw_text for review
    """
    raw = (result.get("raw_text") or "").lower()
    hit_keywords = [kw for kw in keywords if kw.lower() in raw]
    return {
        "keyword_hit": len(hit_keywords) > 0,
        "hit_keywords": hit_keywords,
        "similarity": round(result.get("similarity_score", 0), 4),
        "snippet": (result.get("raw_text") or "")[:120].replace("\n", " "),
    }


def evaluate_query(query_info: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate all results for a single query."""
    keywords = query_info["must_contain_any"]
    scored = [score_result(r, keywords) for r in results]

    hits = sum(1 for s in scored if s["keyword_hit"])
    total = len(scored)
    precision = hits / total if total else 0

    avg_sim = sum(s["similarity"] for s in scored) / total if total else 0

    return {
        "query": query_info["query"],
        "category": query_info["category"],
        "result_count": total,
        "keyword_hits": hits,
        "precision": round(precision, 2),
        "avg_similarity": round(avg_sim, 4),
        "results": scored,
    }


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

GRADE_THRESHOLDS = [(0.8, "EXCELLENT"), (0.6, "GOOD"), (0.4, "FAIR"), (0.2, "POOR")]


def grade(precision: float) -> str:
    for threshold, label in GRADE_THRESHOLDS:
        if precision >= threshold:
            return label
    return "BAD"


def print_report(evaluations: List[Dict[str, Any]]) -> None:
    sep = "=" * 80
    print(f"\n{sep}")
    print(f"  SEARCH QUALITY REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(sep)

    total_precision = 0.0
    total_queries = len(evaluations)

    for ev in evaluations:
        g = grade(ev["precision"])
        total_precision += ev["precision"]

        print(f"\n  Query: \"{ev['query']}\"  [{ev['category']}]")
        print(f"  Results: {ev['result_count']}  |  Keyword hits: {ev['keyword_hits']}  "
              f"|  Precision: {ev['precision']:.0%}  |  Avg similarity: {ev['avg_similarity']}  |  Grade: {g}")
        print(f"  {'-' * 74}")

        for i, r in enumerate(ev["results"], 1):
            hit_marker = "✓" if r["keyword_hit"] else "✗"
            kw_info = f" [{', '.join(r['hit_keywords'])}]" if r["hit_keywords"] else ""
            print(f"  {hit_marker} #{i}  sim={r['similarity']}  {r['snippet']}{kw_info}")

    print(f"\n{sep}")
    avg = total_precision / total_queries if total_queries else 0
    overall = grade(avg)
    print(f"  OVERALL:  {total_queries} queries  |  Avg precision: {avg:.0%}  |  Grade: {overall}")
    print(sep)

    # Verdict
    print()
    if avg >= 0.8:
        print("  VERDICT: Users are getting highly relevant results. Search quality is strong.")
    elif avg >= 0.6:
        print("  VERDICT: Users generally find what they need. Some queries return partial matches.")
    elif avg >= 0.4:
        print("  VERDICT: Hit-or-miss. Users often see unrelated results mixed in.")
    elif avg >= 0.2:
        print("  VERDICT: Poor. Most results don't match user intent. Needs tuning.")
    else:
        print("  VERDICT: Search is essentially broken. Results are random.")
    print()


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run_tests(queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    await init_db()
    engine = get_search_engine()
    evaluations = []

    for q in queries:
        print(f"  Searching: \"{q['query']}\" ...", flush=True)
        results = await engine.search(q["query"], limit=5)
        ev = evaluate_query(q, results)
        evaluations.append(ev)

    return evaluations


def main() -> None:
    if len(sys.argv) > 1:
        custom_query = " ".join(sys.argv[1:])
        queries = [{
            "query": custom_query,
            "category": "custom",
            "must_contain_any": custom_query.lower().split(),
        }]
    else:
        queries = TEST_QUERIES

    evaluations = asyncio.run(run_tests(queries))
    print_report(evaluations)


if __name__ == "__main__":
    main()
