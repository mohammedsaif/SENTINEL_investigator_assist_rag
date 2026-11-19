"""Device + customer neighbourhood from Neo4j (task 2).

Assumed graph model (edit the Cypher below if yours differs):
  (:Customer {customer_id})-[:MADE]->(:Transaction {transaction_id, is_fraud})
  (:Transaction)-[:USED_DEVICE]->(:Device {device_id})
"""
"""Customer / device neighbourhood from Neo4j (task 2).

Graph model (as loaded in task 2):
  (:Customer {customer_id})-[:USED_DEVICE {first_seen, last_seen, tx_count}]->(:Device {device_id})
  (:Customer)-[:PAID {transaction_id, amount, device_id, time, fraud_label}]->(:Merchant)

The graph holds historical transactions, so the transaction being explained may not be in it.
We therefore look up its customer and device (taken from the transaction row) and describe
their history. Fraud counts only use PAID edges strictly before the transaction time when
`as_of` is given, so a transaction's own label is never counted.
"""
from typing import Any

from app.config import Settings

DEVICE_Q = """
OPTIONAL MATCH (d:Device {device_id: $device_id})<-[:USED_DEVICE]-(dc:Customer)
WITH count(DISTINCT dc) AS device_customer_count
OPTIONAL MATCH (:Customer)-[p:PAID {device_id: $device_id}]->(:Merchant)
WHERE p.fraud_label = 1 AND p.transaction_id <> $txn_id
RETURN device_customer_count, count(p) AS device_fraud_txn_count
"""

CUSTOMER_Q = """
OPTIONAL MATCH (c:Customer {customer_id: $customer_id})
OPTIONAL MATCH (c)-[p:PAID]->(:Merchant) WHERE p.transaction_id <> $txn_id
WITH c, count(p) AS customer_txn_count, count(CASE WHEN p.fraud_label = 1 THEN 1 END) AS customer_fraud_txn_count
OPTIONAL MATCH (c)-[:USED_DEVICE]->(cd:Device)
WITH c, customer_txn_count, customer_fraud_txn_count, count(DISTINCT cd) AS customer_device_count
OPTIONAL MATCH (c)-[:USED_DEVICE]->(:Device)<-[:USED_DEVICE]-(n:Customer) WHERE n <> c
WITH customer_txn_count, customer_fraud_txn_count, customer_device_count, collect(DISTINCT n) AS ns
CALL (ns) {
  UNWIND ns AS n
  OPTIONAL MATCH (n)-[np:PAID]->(:Merchant) WHERE np.fraud_label = 1
  RETURN count(DISTINCT CASE WHEN np IS NOT NULL THEN n END) AS fraud_neighbour_count
}
RETURN customer_txn_count, customer_fraud_txn_count, customer_device_count,
       size(ns) AS neighbour_count, fraud_neighbour_count
"""


class GraphStore:
    def __init__(self, s: Settings):
        from neo4j import GraphDatabase

        self.s = s
        self.driver = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))

    def neighbourhood(self, txn_id: str, txn: dict[str, Any] | None = None) -> dict[str, Any] | None:
        txn = txn or {}
        customer_id, device_id = txn.get("customer_id"), txn.get("device_id")
        if not customer_id:
            return None
        out: dict[str, Any] = {"customer_id": customer_id, "device_id": device_id}
        with self.driver.session(database=self.s.neo4j_database) as sess:
            if device_id:
                out.update(sess.run(DEVICE_Q, device_id=device_id, txn_id=txn_id).single().data())
            row = sess.run(CUSTOMER_Q, customer_id=customer_id, txn_id=txn_id).single()
            out.update(row.data() if row else {})
        return out

    def close(self):
        self.driver.close()
