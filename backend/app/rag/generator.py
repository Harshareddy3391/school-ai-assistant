from langchain_openai import ChatOpenAI

from app.core.config import settings


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=settings.OPENAI_API_KEY
)


SYSTEM_PROMPT = """
You are a School AI Assistant.

Answer the user's question using ONLY the provided school context.

Rules:
1. Do not invent information.
2. If the answer is not available in the context, say:
   "I couldn't find this information in the school's documents."
3. Give a clear and concise answer.
4. Use the provided source information when answering.
5. Do not mention internal retrieval, embeddings, or reranking.
"""


def generate_answer(
    question: str,
    context: str
) -> str:

    prompt = f"""
{SYSTEM_PROMPT}

School Context:
----------------
{context}
----------------

User Question:
{question}

Answer:
"""

    try:
        response = llm.invoke(prompt)

        return response.content

    except Exception as e:
        raise RuntimeError(
            f"Failed to generate answer: {str(e)}"
        )