from app.core.database import SessionLocal
from app.services.embedding_service import generate_embedding
from app.rag.hybrid_search import hybrid_search
from app.rag.reranker import rerank_chunks
from app.rag.context_builder import build_context
from app.rag.generator import generate_answer
from sqlalchemy import text
from sqlalchemy.orm import Session

QUESTION = "What is the admission fee for Grade 1?"
SCHOOL_ID = 1


def main():
    db = SessionLocal()

    try:
        # 1. Generate query embedding
        print("Generating query embedding...")
        query_embedding = generate_embedding(QUESTION)

        # 2. Hybrid search
        print("Running hybrid search...")
        hybrid_results = hybrid_search(
            db=db,
            query=QUESTION,
            query_embedding=query_embedding,
            school_id=SCHOOL_ID,
            top_k=5
        )

        if not hybrid_results:
            print("No chunks found.")
            return

        # 3. Rerank chunks
        print("Running reranker...")
        reranked_results = rerank_chunks(
            query=QUESTION,
            chunks=hybrid_results,
            top_k=3
        )

        # 4. Build context
        print("Building context...")
        context = build_context(
            chunks=reranked_results,
            max_chunks=3
        )

        # 5. Generate answer
        print("Generating answer...")
        answer = generate_answer(
            question=QUESTION,
            context=context
        )

        print("\n" + "=" * 70)
        print("QUESTION")
        print("=" * 70)
        print(QUESTION)

        print("\n" + "=" * 70)
        print("FINAL ANSWER")
        print("=" * 70)
        print(answer)

        print("\n" + "=" * 70)
        print("SOURCES")
        print("=" * 70)

        for index, chunk in enumerate(reranked_results, start=1):
            print(
                f"Source {index}: "
                f"Page {chunk.get('page_number')}"
            )

    except Exception as e:
        print("\nRAG pipeline failed")
        print("Error:", e)

    finally:
        db.close()


if __name__ == "__main__":
    main()