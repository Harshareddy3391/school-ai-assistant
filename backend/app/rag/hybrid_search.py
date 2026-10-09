
from sqlalchemy import text
from sqlalchemy.orm import Session


def vector_similarity_search(
    db: Session,
    query_embedding: list[float],
    school_id: int | None = None,
    school_ids: list[int] | None = None,
    top_k: int = 10,
) -> list[dict]:
    conditions = ["embedding IS NOT NULL"]
    params = {
        "query_embedding": str(query_embedding),
        "top_k": top_k,
    }

    if school_ids:
        conditions.append("school_id = ANY(:school_ids)")
        params["school_ids"] = school_ids
    elif school_id is not None:
        conditions.append("school_id = :school_id")
        params["school_id"] = school_id

    sql = text(f"""
        SELECT
            id,
            document_id,
            school_id,
            school_name,
            city,
            content,
            page_number,
            pdf_filename,
            metadata_json,
            1 - (embedding <=> CAST(:query_embedding AS vector))
                AS similarity
        FROM public.school_knowledge
        WHERE {" AND ".join(conditions)}
        ORDER BY embedding <=> CAST(:query_embedding AS vector)
        LIMIT :top_k
    """)

    rows = db.execute(sql, params).mappings().all()
    return [dict(row) for row in rows]


def keyword_search(
    db: Session,
    query: str,
    school_id: int | None = None,
    school_ids: list[int] | None = None,
    top_k: int = 10,
) -> list[dict]:
    conditions = [
        """
        to_tsvector(
            'english',
            coalesce(content, '') || ' ' ||
            coalesce(school_name, '') || ' ' ||
            coalesce(city, '')
        ) @@ plainto_tsquery('english', :query)
        """
    ]

    params = {
        "query": query,
        "top_k": top_k,
    }

    if school_ids:
        conditions.append("school_id = ANY(:school_ids)")
        params["school_ids"] = school_ids
    elif school_id is not None:
        conditions.append("school_id = :school_id")
        params["school_id"] = school_id

    sql = text(f"""
        SELECT
            id,
            document_id,
            school_id,
            school_name,
            city,
            content,
            page_number,
            pdf_filename,
            metadata_json,
            ts_rank(
                to_tsvector(
                    'english',
                    coalesce(content, '') || ' ' ||
                    coalesce(school_name, '') || ' ' ||
                    coalesce(city, '')
                ),
                plainto_tsquery('english', :query)
            ) AS keyword_score
        FROM public.school_knowledge
        WHERE {" AND ".join(conditions)}
        ORDER BY keyword_score DESC
        LIMIT :top_k
    """)

    rows = db.execute(sql, params).mappings().all()
    return [dict(row) for row in rows]


def hybrid_search(
    db: Session,
    query: str,
    query_embedding: list[float],
    school_id: int | None = None,
    school_ids: list[int] | None = None,
    top_k: int = 10,
) -> list[dict]:
    vector_results = vector_similarity_search(
        db=db,
        query_embedding=query_embedding,
        school_id=school_id,
        school_ids=school_ids,
        top_k=top_k,
    )

    keyword_results = keyword_search(
        db=db,
        query=query,
        school_id=school_id,
        school_ids=school_ids,
        top_k=top_k,
    )

    combined = {}

    for result in vector_results:
        chunk_id = result["id"]
        combined[chunk_id] = {
            **result,
            "vector_score": float(result["similarity"]),
            "keyword_score": 0.0,
        }

    for result in keyword_results:
        chunk_id = result["id"]

        if chunk_id in combined:
            combined[chunk_id]["keyword_score"] = float(
                result["keyword_score"]
            )
        else:
            combined[chunk_id] = {
                **result,
                "vector_score": 0.0,
                "keyword_score": float(result["keyword_score"]),
            }

    max_keyword = max(
        (item["keyword_score"] for item in combined.values()),
        default=0.0,
    )

    for item in combined.values():
        normalized_keyword = (
            item["keyword_score"] / max_keyword
            if max_keyword > 0
            else 0.0
        )

        item["keyword_score"] = normalized_keyword
        item["hybrid_score"] = (
            0.7 * item["vector_score"]
            + 0.3 * normalized_keyword
        )

    return sorted(
        combined.values(),
        key=lambda item: item["hybrid_score"],
        reverse=True,
    )[:top_k]
