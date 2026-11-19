"""Policy chunk retrieval from Qdrant, queried with Euri embeddings (task 4).

The query embedding must use the same model and output dimension you used to
index the chunks, otherwise similarity scores are meaningless."""
from typing import Any

from app.config import Settings
from app.schemas import PolicyChunk


class PolicyStore:
    def __init__(self, s: Settings):
        from euriai import EuriaiEmbeddingClient
        from qdrant_client import QdrantClient

        self.s = s
        self.embed_client = EuriaiEmbeddingClient(api_key=s.euri_api_key, model=s.embed_model)
        self.qdrant = QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None)

    def embed(self, text: str) -> list[float]:
        result = self.embed_client.embed(text)
        # EuriaiEmbeddingClient returns np.ndarray; convert to list[float]
        return result.tolist() if hasattr(result, "tolist") else list(result)

    def search(self, query: str, k: int | None = None) -> list[PolicyChunk]:
        s = self.s
        hits = self.qdrant.query_points(
            collection_name=s.qdrant_collection,
            query=self.embed(query),
            limit=k or s.top_k,
            with_payload=True,
        ).points
        out = []
        for h in hits:
            p = h.payload or {}
            out.append(
                PolicyChunk(
                    document=str(p.get(s.payload_doc_field, "unknown")),
                    title=str(p.get(s.payload_title_field, "")),
                    chunk_id=str(p.get(s.payload_chunk_field, h.id)),
                    text=str(p.get(s.payload_text_field, "")),
                    score=float(h.score),
                )
            )
        return out
