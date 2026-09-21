from app.core.database import SessionLocal
from app.services.embedding_service import generate_embedding
from app.rag.hybrid_search import vector_similarity_search


QUESTION = "What is the admission fee for Grade 1?"

SCHOOL_ID = 1


def main():
    db = SessionLocal()

    try:
        # 1. Generate embedding for the question
        query_embedding = generate_embedding(
            QUESTION
        )

        print("Query embedding generated")
        print(
            "Vector dimensions:",
            len(query_embedding)
        )

        # 2. Search similar chunks
        results = vector_similarity_search(
            db=db,
            query_embedding=query_embedding,
            school_id=SCHOOL_ID,
            top_k=5
        )

        # 3. Display results
        print("\nVector Search Results")
        print("=" * 60)

        if not results:
            print("No matching chunks found.")
            return

        for index, result in enumerate(
            results,
            start=1
        ):
            print(f"\nResult {index}")
            print(f"Chunk ID: {result['id']}")
            print(
                f"Document ID: "
                f"{result['document_id']}"
            )
            print(
                f"School ID: "
                f"{result['school_id']}"
            )
            print(
                f"Page: "
                f"{result['page_number']}"
            )
            print(
                f"Similarity: "
                f"{result['similarity']:.4f}"
            )
            print(
                f"Content: "
                f"{result['content'][:300]}"
            )

    except Exception as e:
        print("Vector search failed")
        print("Error:", e)

    finally:
        db.close()


if __name__ == "__main__":
    main()