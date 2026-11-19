"""Task step 4: explain 5 fraud + 5 genuine validation transactions and save results.

    python -m scripts.run_test_transactions                       # pick from DB split column
    python -m scripts.run_test_transactions --ids-csv eval/val_ids.csv   # or supply ids (transaction_id,is_fraud)

Writes results/explain/<id>.json, results/test_run_summary.json and results/test_run_summary.md.
Calls the running API (default http://localhost:8000) so the saved output is exactly what /explain returns.
"""
import argparse
import csv
import json
from pathlib import Path

import httpx

from app.config import get_settings
from app.stores.transactions import make_store

OUT = Path("results")


def pick_ids(args) -> list[tuple[str, bool]]:
    if args.ids_csv:
        with open(args.ids_csv) as f:
            rows = list(csv.DictReader(f))
        truthy = {"1", "true", "True", "yes"}
        fraud = [(r["transaction_id"], True) for r in rows if r["is_fraud"] in truthy][: args.n]
        genuine = [(r["transaction_id"], False) for r in rows if r["is_fraud"] not in truthy][: args.n]
    else:
        store = make_store(get_settings())
        fraud = [(i, True) for i in store.sample(args.split, True, args.n)]
        genuine = [(i, False) for i in store.sample(args.split, False, args.n)]
    if len(fraud) < args.n or len(genuine) < args.n:
        raise SystemExit(f"need {args.n}+{args.n}, got {len(fraud)} fraud / {len(genuine)} genuine")
    return fraud + genuine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--split", default="val")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--ids-csv")
    args = ap.parse_args()

    (OUT / "explain").mkdir(parents=True, exist_ok=True)
    rows = []
    with httpx.Client(timeout=120) as http:
        for txn_id, is_fraud in pick_ids(args):
            r = http.post(f"{args.api}/explain", json={"transaction_id": txn_id})
            r.raise_for_status()
            body = r.json()
            (OUT / "explain" / f"{txn_id}.json").write_text(json.dumps(body, indent=2))
            flagged = body["recommended_action"] != "APPROVE"
            rows.append({
                "transaction_id": txn_id,
                "true_label": "fraud" if is_fraud else "genuine",
                "risk_level": body["risk_level"],
                "action": body["recommended_action"],
                "reason_codes": [c["code"] for c in body["reason_codes"]],
                "n_citations": len(body["cited_sources"]),
                "correct": flagged == is_fraud,
                "latency_ms": body["debug"].get("latency_ms"),
            })
            print(f"{txn_id:>14}  {rows[-1]['true_label']:<8} -> {body['recommended_action']}")

    acc = sum(r["correct"] for r in rows) / len(rows)
    (OUT / "test_run_summary.json").write_text(json.dumps({"accuracy_flag_vs_label": acc, "rows": rows}, indent=2))

    md = ["| transaction_id | label | risk | action | reason codes | cites | correct |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['transaction_id']} | {r['true_label']} | {r['risk_level']} | {r['action']} | "
                  f"{', '.join(r['reason_codes']) or '-'} | {r['n_citations']} | {'yes' if r['correct'] else 'no'} |")
    md.append(f"\nFlag-vs-label agreement: **{acc:.0%}** (anything other than APPROVE counts as flagged)")
    (OUT / "test_run_summary.md").write_text("\n".join(md) + "\n")
    print(f"\nagreement {acc:.0%}  -> results/test_run_summary.md")


if __name__ == "__main__":
    main()
