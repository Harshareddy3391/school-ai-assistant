# backend/app/rag/reranker.py

from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

reranker_model = CrossEncoder(MODEL_NAME)


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 3
) -> list[dict]:

    if not chunks:
        return []

    pairs = [
        (query, chunk["content"])
        for chunk in chunks
    ]

    scores = reranker_model.predict(pairs)

    reranked_chunks = []

    for chunk, score in zip(chunks, scores):
        reranked_chunk = {
            **chunk,
            "rerank_score": float(score)
        }

        reranked_chunks.append(reranked_chunk)

    reranked_chunks.sort(
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    return reranked_chunks[:top_k]