# backend/app/rag/context_builder.py


def build_context(
    chunks: list[dict],
    max_chunks: int = 3
) -> str:

    if not chunks:
        return ""

    selected_chunks = chunks[:max_chunks]

    context_parts = []

    for index, chunk in enumerate(selected_chunks, start=1):

        content = chunk.get("content", "")
        page_number = chunk.get("page_number")
        document_id = chunk.get("document_id")
        school_id = chunk.get("school_id")

        context = (
            f"[Source {index}]\n"
            f"School ID: {school_id}\n"
            f"Document ID: {document_id}\n"
            f"Page: {page_number}\n"
            f"Content:\n{content}"
        )

        context_parts.append(context)

    return "\n\n".join(context_parts)