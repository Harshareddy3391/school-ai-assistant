from sqlalchemy import text
from sqlalchemy.orm import Session


def vector_similarity_search(
    db: Session,
    query_embedding: list[float],
    school_id: int,
    top_k: int = 5
) -> list[dict]:

    sql = text("""
        SELECT
            id,
            document_id,
            school_id,
            content,
            page_number,
            section,
            metadata_json,
            1 - (
                embedding <=> CAST(:query_embedding AS vector)
            ) AS similarity
        FROM document_chunks
        WHERE school_id = :school_id
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:query_embedding AS vector)
        LIMIT :top_k
    """)

    result = db.execute(
        sql,
        {
            "query_embedding": str(query_embedding),
            "school_id": school_id,
            "top_k": top_k
        }
    )

    rows = result.mappings().all()

    return [dict(row) for row in rows]


def keyword_search(
    db: Session,
    query: str,
    school_id: int,
    top_k: int = 5
) -> list[dict]:

    sql = text("""
        SELECT
            id,
            document_id,
            school_id,
            content,
            page_number,
            section,
            metadata_json,
            ts_rank(
                to_tsvector('english', content),
                plainto_tsquery('english', :query)
            ) AS keyword_score
        FROM document_chunks
        WHERE school_id = :school_id
          AND to_tsvector('english', content)
              @@ plainto_tsquery('english', :query)
        ORDER BY keyword_score DESC
        LIMIT :top_k
    """)

    result = db.execute(
        sql,
        {
            "query": query,
            "school_id": school_id,
            "top_k": top_k
        }
    )

    rows = result.mappings().all()

    return [dict(row) for row in rows]


def hybrid_search(
    db: Session,
    query: str,
    query_embedding: list[float],
    school_id: int,
    top_k: int = 5
) -> list[dict]:

    vector_results = vector_similarity_search(
        db=db,
        query_embedding=query_embedding,
        school_id=school_id,
        top_k=top_k
    )

    keyword_results = keyword_search(
        db=db,
        query=query,
        school_id=school_id,
        top_k=top_k
    )

    combined_results = {}

    for result in vector_results:
        chunk_id = result["id"]

        combined_results[chunk_id] = {
            **result,
            "vector_score": float(result["similarity"]),
            "keyword_score": 0.0
        }

    for result in keyword_results:
        chunk_id = result["id"]

        if chunk_id in combined_results:
            combined_results[chunk_id]["keyword_score"] = float(
                result["keyword_score"]
            )
        else:
            combined_results[chunk_id] = {
                **result,
                "vector_score": 0.0,
                "keyword_score": float(result["keyword_score"])
            }

    max_keyword_score = max(
        (
            result["keyword_score"]
            for result in combined_results.values()
        ),
        default=0.0
    )

    if max_keyword_score > 0:
        for result in combined_results.values():
            result["keyword_score"] = (
                result["keyword_score"] / max_keyword_score
            )

    for result in combined_results.values():
        result["hybrid_score"] = (
            0.7 * result["vector_score"]
            + 0.3 * result["keyword_score"]
        )

    ranked_results = sorted(
        combined_results.values(),
        key=lambda item: item["hybrid_score"],
        reverse=True
    )

    return ranked_results[:top_k]