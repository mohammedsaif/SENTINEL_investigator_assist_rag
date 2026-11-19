"""LLM call: context in, structured JSON out (Euri AI)."""

import json
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas import Action, Citation

from euriai import EuriaiClient

SYSTEM_PROMPT = """You are SENTINEL, an assistant for payment-fraud investigators.
You receive one transaction, its engineered features, its device/customer graph
neighbourhood, the reason codes a deterministic rule engine already fired, and
numbered policy excerpts.

Rules:
1. Base every claim on the supplied context. Do not invent facts, amounts or codes.
2. Do not add or remove reason codes; explain the ones given.
3. Choose recommended_action from APPROVE, STEP_UP_AUTH, HOLD_FOR_REVIEW, BLOCK,
   and justify it with the policy excerpts.
4. cited_sources must only use document + chunk_id pairs that appear in the
   policy excerpts. The quote must be a short phrase copied from that chunk.
5. If no reason codes fired and the graph is clean, APPROVE is usually right.
6. If the policy excerpts do not cover the situation, say so in action_rationale.
Keep risk_summary to 2-4 sentences an investigator can read in 10 seconds."""

JSON_INSTRUCTIONS = """Respond with ONLY one JSON object (no markdown), with exactly these keys:
{"risk_level": "LOW|MEDIUM|HIGH", "risk_summary": str,
 "recommended_action": "APPROVE|STEP_UP_AUTH|HOLD_FOR_REVIEW|BLOCK",
 "action_rationale": str,
 "cited_sources": [{"document": str, "chunk_id": str, "quote": str}]}
Use the document and chunk_id values exactly as shown in the policy excerpts."""


class LLMOut(BaseModel):
    risk_level: str
    risk_summary: str
    recommended_action: Action
    action_rationale: str
    cited_sources: list[Citation]


def build_user_prompt(txn: dict, graph: dict | None, codes: list, chunks: list) -> str:
    excerpts = "\n\n".join(
        f"[{i + 1}] document={c.document} chunk_id={c.chunk_id} title={c.title!r}\n{c.text}"
        for i, c in enumerate(chunks)
    ) or "(no policy excerpts retrieved)"
    return (
        f"TRANSACTION + FEATURES:\n{json.dumps(txn, default=str, indent=1)}\n\n"
        f"GRAPH NEIGHBOURHOOD:\n{json.dumps(graph, default=str, indent=1) if graph else '(unavailable)'}\n\n"
        f"FIRED REASON CODES:\n{json.dumps([c.model_dump() for c in codes], indent=1) if codes else '(none)'}\n\n"
        f"POLICY EXCERPTS:\n{excerpts}"
    )


class EuriLLM:
    def __init__(self, s: Settings):
        self.s = s
        self.client = EuriaiClient(api_key=s.euri_api_key, model=s.llm_model)

    def explain(self, user_prompt: str) -> LLMOut:
        prompt = "\n\n".join([SYSTEM_PROMPT, JSON_INSTRUCTIONS, user_prompt])
        last_err: Exception | None = None
        for _ in range(3):  # models occasionally return malformed JSON; retry
            response = self.client.generate_completion(
                prompt=prompt,
                temperature=self.s.llm_temperature,
                max_tokens=4000,
                top_p=0.95,
            )
            text = response["choices"][0]["message"]["content"].strip()
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end > start:
                text = text[start : end + 1]
            try:
                return LLMOut.model_validate_json(text)
            except ValueError as e:
                last_err = e
                print(f"[llm] unparseable output, retrying: {text[:400]!r}")
        raise RuntimeError(f"LLM returned invalid JSON after 3 attempts: {last_err}")


def ground_citations(cites: list[Citation], chunks: list) -> tuple[list[Citation], list[dict[str, Any]]]:
    """Drop any citation whose (document, chunk_id) was not actually retrieved."""
    allowed = {(c.document, c.chunk_id) for c in chunks}
    kept, dropped = [], []
    for c in cites:
        (kept if (c.document, c.chunk_id) in allowed else dropped).append(c)
    return kept, [d.model_dump() for d in dropped]
