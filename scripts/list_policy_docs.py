"""Print every distinct document in the Qdrant collection with its chunk count and
first chunk preview. Use this to fill in expected_doc in eval/retrieval_questions.json.

    python -m scripts.list_policy_docs
"""
from collections import defaultdict

from qdrant_client import QdrantClient

from app.config import get_settings


def main():
    s = get_settings()
    q = QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None)
    docs: dict[str, list[str]] = defaultdict(list)
    offset = None
    while True:
        pts, offset = q.scroll(s.qdrant_collection, limit=256, offset=offset, with_payload=True)
        for p in pts:
            pl = p.payload or {}
            docs[str(pl.get(s.payload_doc_field, "unknown"))].append(str(pl.get(s.payload_text_field, ""))[:100])
        if offset is None:
            break
    for d, chunks in sorted(docs.items()):
        print(f"{d}  ({len(chunks)} chunks)\n    {chunks[0]!r}")


if __name__ == "__main__":
    main()
