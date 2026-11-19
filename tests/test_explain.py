"""Offline tests: fake stores + fake LLM, so the pipeline is checked without any cloud DB."""
from fastapi.testclient import TestClient

from app import main
from app.explain import Explainer
from app.llm import LLMOut
from app.reason_codes import evaluate, load_rules
from app.schemas import Citation, PolicyChunk

RULES = load_rules("app/rules.yaml")

TXNS = {
    "T_FRAUD": {"transaction_id": "T_FRAUD", "transaction_amount": 48210, "txn_count_last_1h": 7, "is_new_device": True,
                "distinct_customers_per_device_7d": 4, "is_new_account": True, "is_fraud": True, "split": "val"},
    "T_OK": {"transaction_id": "T_OK", "transaction_amount": 120, "txn_count_last_1h": 1, "is_new_device": False,
             "distinct_customers_per_device_7d": 1, "is_new_account": False, "is_fraud": False, "split": "val"},
}
GRAPH = {"T_FRAUD": {"device_customer_count": 4, "device_fraud_txn_count": 2, "fraud_neighbour_count": 1},
         "T_OK": {"device_customer_count": 1, "device_fraud_txn_count": 0, "fraud_neighbour_count": 0}}
CHUNKS = [PolicyChunk(document="velocity_rules_policy", chunk_id="c3", text="Five or more payments in one hour require a hold.", score=0.81)]


class FakeTxns:
    def get(self, i): return TXNS.get(i)


class FakeGraph:
    def neighbourhood(self, i, txn=None): return GRAPH.get(i)


class FakePolicy:
    def search(self, q, k=None): return CHUNKS


class FakeLLM:
    def __init__(self): self.last_prompt = ""

    def explain(self, prompt):
        self.last_prompt = prompt
        return LLMOut(
            risk_level="HIGH", risk_summary="Velocity and new device.", recommended_action="HOLD_FOR_REVIEW",
            action_rationale="Policy requires a hold.",
            cited_sources=[Citation(document="velocity_rules_policy", chunk_id="c3", quote="require a hold"),
                           Citation(document="made_up_doc", chunk_id="c99", quote="hallucinated")],
        )


def make(llm=None):
    return Explainer(FakeTxns(), FakeGraph(), FakePolicy(), llm or FakeLLM(), RULES)


def test_rules_fire_on_fraud_not_on_genuine():
    fraud = {c.code for c in evaluate(RULES, TXNS["T_FRAUD"], GRAPH["T_FRAUD"])}
    assert {"AMT_ABS_HIGH", "VELOCITY_1H", "NEW_DEVICE", "NEW_ACCOUNT",
            "DEVICE_SHARED", "DEVICE_FRAUD_HISTORY", "RING_NEIGHBOUR"} <= fraud
    assert evaluate(RULES, TXNS["T_OK"], GRAPH["T_OK"]) == []


def test_ungrounded_citations_dropped():
    r = make().explain("T_FRAUD")
    assert [(c.document, c.chunk_id) for c in r.cited_sources] == [("velocity_rules_policy", "c3")]
    assert r.debug["dropped_ungrounded_citations"][0]["document"] == "made_up_doc"


def test_label_not_leaked_to_llm():
    llm = FakeLLM()
    make(llm).explain("T_FRAUD")
    assert '"is_fraud"' not in llm.last_prompt and '"split"' not in llm.last_prompt


def test_graph_failure_degrades():
    class Broken:
        def neighbourhood(self, i, txn=None): raise ConnectionError
    e = Explainer(FakeTxns(), Broken(), FakePolicy(), FakeLLM(), RULES)
    r = e.explain("T_FRAUD")
    assert any("neo4j" in g for g in r.context_gaps)


def test_endpoint_200_and_404():
    main.state["explainer"] = make()
    client = TestClient(main.app)  # no lifespan: not used as context manager
    ok = client.post("/explain", json={"transaction_id": "T_FRAUD"})
    assert ok.status_code == 200 and ok.json()["recommended_action"] == "HOLD_FOR_REVIEW"
    assert client.post("/explain", json={"transaction_id": "NOPE"}).status_code == 404
