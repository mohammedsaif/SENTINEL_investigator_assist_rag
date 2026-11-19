"""FastAPI entrypoint.  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.explain import Explainer, TransactionNotFound
from app.llm import EuriLLM
from app.reason_codes import load_rules
from app.schemas import ExplainRequest, ExplainResponse
from app.stores.graph import GraphStore
from app.stores.policy import PolicyStore
from app.stores.transactions import make_store

state: dict = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    s = get_settings()
    graph = GraphStore(s) if s.neo4j_uri else None
    state["explainer"] = Explainer(
        txn_store=make_store(s),
        graph_store=graph,
        policy_store=PolicyStore(s),
        llm=EuriLLM(s),
        rules=load_rules(s.rules_file),
        label_field=s.label_field,
        llm_model=s.llm_model,
    )
    yield
    if graph:
        graph.close()


app = FastAPI(title="SENTINEL Explain API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    try:
        return state["explainer"].explain(req.transaction_id)
    except TransactionNotFound:
        raise HTTPException(404, f"transaction {req.transaction_id} not found")
