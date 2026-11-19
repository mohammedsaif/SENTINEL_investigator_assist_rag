"""Orchestrator: fetch from three stores -> rules -> retrieve -> LLM -> ground."""
import time
from typing import Any

from app.llm import build_user_prompt, ground_citations
from app.reason_codes import evaluate
from app.schemas import ExplainResponse

# Strip columns that would leak the answer to the LLM.
LEAKY_FIELDS = {"is_fraud", "isFraud", "label", "fraud_label", "isFlaggedFraud", "split", "reason_codes"}


class TransactionNotFound(Exception):
    pass


def build_retrieval_query(txn: dict, codes: list) -> str:
    """Policy search text: reason-code descriptions are what the policy docs talk about."""
    if codes:
        parts = [f"{c.code}: {c.description}" for c in codes]
        return "Fraud policy for: " + "; ".join(parts) + ". Recommended investigator action and escalation."
    amt = txn.get("amount", "")
    typ = txn.get("type", txn.get("transaction_type", ""))
    return f"Policy for low-risk {typ} payment of amount {amt} with no risk signals; approval criteria."


class Explainer:
    def __init__(self, txn_store, graph_store, policy_store, llm, rules, label_field="is_fraud", llm_model=""):
        self.txns, self.graph, self.policy, self.llm = txn_store, graph_store, policy_store, llm
        self.rules = rules
        self.leaky = LEAKY_FIELDS | {label_field}
        self.llm_model = llm_model

    def explain(self, txn_id: str) -> ExplainResponse:
        t0 = time.perf_counter()
        gaps: list[str] = []

        raw = self.txns.get(txn_id)
        if raw is None:
            raise TransactionNotFound(txn_id)
        txn = {k: v for k, v in raw.items() if k not in self.leaky}

        graph: dict[str, Any] | None = None
        try:
            graph = self.graph.neighbourhood(txn_id, txn) if self.graph else None
            if graph is None:
                gaps.append("neo4j: customer not found in graph")
        except Exception as e:  # degrade, don't fail the investigator
            gaps.append(f"neo4j: {type(e).__name__}")

        codes = evaluate(self.rules, txn, graph)

        query = build_retrieval_query(txn, codes)
        chunks = []
        try:
            chunks = self.policy.search(query)
            if not chunks:
                gaps.append("qdrant: no policy chunks returned")
        except Exception as e:
            gaps.append(f"qdrant: {type(e).__name__}")

        out = self.llm.explain(build_user_prompt(txn, graph, codes, chunks))
        cites, dropped = ground_citations(out.cited_sources, chunks)

        return ExplainResponse(
            transaction_id=txn_id,
            risk_level=out.risk_level,
            risk_summary=out.risk_summary,
            reason_codes=codes,
            recommended_action=out.recommended_action,
            action_rationale=out.action_rationale,
            cited_sources=cites,
            context_gaps=gaps,
            debug={
                "retrieval_query": query,
                "retrieved": [{"document": c.document, "chunk_id": c.chunk_id, "score": round(c.score, 4)} for c in chunks],
                "dropped_ungrounded_citations": dropped,
                "llm_model": self.llm_model,
                "latency_ms": round((time.perf_counter() - t0) * 1000),
            },
        )
