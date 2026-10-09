
def build_context(
    chunks: list[dict],
    max_chunks: int = 3,
) -> str:

    if not chunks:
        return ""

    selected_chunks = chunks[:max_chunks]
    context_parts = []

    for index, chunk in enumerate(selected_chunks, start=1):
        school_name = chunk.get("school_name", "Unknown school")
        school_id = chunk.get("school_id")
        pdf_filename = chunk.get("pdf_filename", "Unknown PDF")
        document_id = chunk.get("document_id")
        page_number = chunk.get("page_number")
        content = chunk.get("content", "")

        context = (
            f"[Source {index}]\n"
            f"School: {school_name}\n"
            f"School ID: {school_id}\n"
            f"PDF: {pdf_filename}\n"
            f"Document ID: {document_id}\n"
            f"Page: {page_number}\n"
            f"Content:\n{content}"
        )

        context_parts.append(context)

    return "\n\n".join(context_parts)
