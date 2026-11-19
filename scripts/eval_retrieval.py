"""Task step 5: retrieval hit@5 on hand-labelled questions.

    python -m scripts.eval_retrieval [--questions eval/retrieval_questions.json] [--k 5]

A question is a hit if ANY of the top-k chunks comes from its expected document.
Also reports MRR so you can see *how high* the right document ranks.
Writes results/retrieval_eval.json and results/retrieval_eval.md.
"""
import argparse
import json
from pathlib import Path

from app.config import get_settings
from app.stores.policy import PolicyStore


def matches(doc: str, expected: list[str]) -> bool:
    d = doc.lower()
    return any(e.lower() == d or e.lower() in d for e in expected)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="eval/retrieval_questions.json")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    qs = json.loads(Path(args.questions).read_text())
    store = PolicyStore(get_settings())
    rows, hits, rr_sum = [], 0, 0.0

    for q in qs:
        expected = q["expected_doc"] if isinstance(q["expected_doc"], list) else [q["expected_doc"]]
        chunks = store.search(q["question"], k=args.k)
        rank = next((i + 1 for i, c in enumerate(chunks) if matches(c.document, expected)), None)
        hits += rank is not None
        rr_sum += 1 / rank if rank else 0
        rows.append({
            "id": q["id"],
            "question": q["question"],
            "expected_doc": expected,
            "hit": rank is not None,
            "rank": rank,
            "top_k": [{"document": c.document, "chunk_id": c.chunk_id, "score": round(c.score, 4)} for c in chunks],
        })
        print(f"{q['id']:>4}  {'HIT ' if rank else 'MISS'}  rank={rank}  {q['question'][:70]}")

    n = len(qs)
    summary = {f"hit@{args.k}": hits / n, "mrr": rr_sum / n, "n": n, "rows": rows}
    out = Path("results")
    out.mkdir(exist_ok=True)
    (out / "retrieval_eval.json").write_text(json.dumps(summary, indent=2))

    md = [f"**hit@{args.k} = {hits}/{n} = {hits / n:.0%}**  |  MRR = {rr_sum / n:.3f}\n",
          "| id | question | expected doc | hit | rank | top-1 doc |", "|---|---|---|---|---|---|"]
    for r in rows:
        top1 = r["top_k"][0]["document"] if r["top_k"] else "-"
        md.append(f"| {r['id']} | {r['question']} | {', '.join(r['expected_doc'])} | "
                  f"{'yes' if r['hit'] else 'no'} | {r['rank'] or '-'} | {top1} |")
    (out / "retrieval_eval.md").write_text("\n".join(md) + "\n")
    print(f"\nhit@{args.k} = {hits / n:.0%}   MRR = {rr_sum / n:.3f}  -> results/retrieval_eval.md")


if __name__ == "__main__":
    main()
