from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


embeddings_model = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=settings.OPENAI_API_KEY
)


def generate_embedding(text: str) -> list[float]:
    """
    Generate an embedding vector for a single text chunk.
    """

    try:
        embedding = embeddings_model.embed_query(text)

        return embedding

    except Exception as e:
        raise RuntimeError(
            f"Failed to generate embedding: {str(e)}"
        )


def generate_embeddings(
    texts: list[str]
) -> list[list[float]]:
    """
    Generate embeddings for multiple text chunks.
    """

    try:
        embeddings = embeddings_model.embed_documents(
            texts
        )

        return embeddings

    except Exception as e:
        raise RuntimeError(
            f"Failed to generate embeddings: {str(e)}"
        )