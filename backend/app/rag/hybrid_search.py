from sqlalchemy import text
from sqlalchemy.orm import Session


def vector_similarity_search(
    db: Session,
    query_embedding: list[float],
    school_id: int,
    top_k: int = 5
) -> list[dict]:
    """
    Perform vector similarity search using pgvector.

    Only chunks belonging to the selected school
    are searched.
    """

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

    return [
        dict(row)
        for row in rows
    ]