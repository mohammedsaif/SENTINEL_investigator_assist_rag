"""Central settings. Every table / collection / field name lives here so the
service can be pointed at the schemas you built in tasks 1, 2 and 4 without
touching code."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- Transaction store (task 1) ----
    txn_backend: str = "supabase"  # "supabase" | "mongo"
    supabase_url: str = ""
    supabase_key: str = ""
    txn_table: str = "transactions"
    features_table: str = "transaction_features"  # set equal to txn_table if features live on the same row
    txn_id_field: str = "transaction_id"
    label_field: str = "is_fraud"
    labels_table: str = ""  # optional separate labels table (txn_id_field + label_field + split_field)
    split_field: str = "split"  # column holding train / val / test
    mongo_uri: str = ""
    mongo_db: str = "sentinel"

    # ---- Graph store (task 2) ----
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # ---- Policy store (task 4) ----
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "fraud_policies"
    payload_doc_field: str = "doc_id"
    payload_title_field: str = "title"
    payload_chunk_field: str = "chunk_id"
    payload_text_field: str = "text"
    top_k: int = 5

    # ---- Euri AI ----
    euri_api_key: str = ""
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536  # MUST match the dimension you indexed with in task 4
    llm_model: str = "gpt-4.1-nano"
    llm_temperature: float = 0.1

    # ---- Rules ----
    rules_file: str = "app/rules.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()
