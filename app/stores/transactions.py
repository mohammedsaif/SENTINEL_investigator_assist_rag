"""Transaction + feature lookup (task 1). Supabase (Postgres) or MongoDB."""
from typing import Any, Protocol

from app.config import Settings


class TransactionStore(Protocol):
    def get(self, txn_id: str) -> dict[str, Any] | None: ...
    def sample(self, split: str, label: bool, n: int) -> list[str]: ...


class SupabaseStore:
    def __init__(self, s: Settings):
        from supabase import create_client

        self.s = s
        self.db = create_client(s.supabase_url, s.supabase_key)

    def _one(self, table: str, txn_id: str) -> dict | None:
        r = self.db.table(table).select("*").eq(self.s.txn_id_field, txn_id).limit(1).execute()
        return r.data[0] if r.data else None

    def get(self, txn_id: str) -> dict[str, Any] | None:
        txn = self._one(self.s.txn_table, txn_id)
        if txn is None:
            return None
        if self.s.features_table and self.s.features_table != self.s.txn_table:
            feats = self._one(self.s.features_table, txn_id) or {}
            txn = {**feats, **txn}  # raw txn columns win on name clash
        return txn

    def sample(self, split: str, label: bool, n: int) -> list[str]:
        table = self.s.labels_table or self.s.features_table or self.s.txn_table
        r = (
            self.db.table(table)
            .select(self.s.txn_id_field)
            .eq(self.s.split_field, split)
            .eq(self.s.label_field, int(label) if self.s.labels_table else label)
            .order(self.s.txn_id_field)
            .limit(n)
            .execute()
        )
        return [str(row[self.s.txn_id_field]) for row in r.data]


class MongoStore:
    def __init__(self, s: Settings):
        from pymongo import MongoClient

        self.s = s
        self.db = MongoClient(s.mongo_uri)[s.mongo_db]

    def get(self, txn_id: str) -> dict[str, Any] | None:
        q = {self.s.txn_id_field: txn_id}
        txn = self.db[self.s.txn_table].find_one(q, {"_id": 0})
        if txn is None:
            return None
        if self.s.features_table and self.s.features_table != self.s.txn_table:
            feats = self.db[self.s.features_table].find_one(q, {"_id": 0}) or {}
            txn = {**feats, **txn}
        return txn

    def sample(self, split: str, label: bool, n: int) -> list[str]:
        coll = self.db[self.s.features_table or self.s.txn_table]
        cur = coll.find(
            {self.s.split_field: split, self.s.label_field: label},
            {self.s.txn_id_field: 1, "_id": 0},
        ).sort(self.s.txn_id_field, 1).limit(n)
        return [str(d[self.s.txn_id_field]) for d in cur]


def make_store(s: Settings) -> TransactionStore:
    return MongoStore(s) if s.txn_backend == "mongo" else SupabaseStore(s)
