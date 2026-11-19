"""Deterministic rule engine: features + graph -> fired reason codes."""
from pathlib import Path
from typing import Any

import yaml

from app.schemas import ReasonCode

_OPS = {
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "in": lambda a, b: str(a).lower() in {str(x).lower() for x in b},
    "true": lambda a, _b: a in (True, 1, "1", "true", "True", "yes"),
}


def load_rules(path: str) -> list[dict]:
    return yaml.safe_load(Path(path).read_text())["rules"]


def evaluate(rules: list[dict], features: dict[str, Any], graph: dict[str, Any] | None) -> list[ReasonCode]:
    fired: list[ReasonCode] = []
    for r in rules:
        src = features if r["source"] == "features" else (graph or {})
        val = src.get(r["field"])
        if val is None:
            continue
        try:
            if r["op"] not in ("in", "true", "eq", "neq"):
                val = float(val)
            if _OPS[r["op"]](val, r.get("value")):
                shown = r.get("value", "")
                fired.append(
                    ReasonCode(
                        code=r["code"],
                        description=r["description"],
                        evidence=f"{r['field']}={val} {r['op']} {shown}".strip(),
                        source=r["source"],
                    )
                )
        except (TypeError, ValueError):
            continue
    return fired
