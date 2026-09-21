from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text_into_chunks(
    pages: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> list[dict]:
    """
    Split extracted PDF text into smaller chunks
    while preserving page information.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )

    chunks = []

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]

        page_chunks = text_splitter.split_text(text)

        for chunk_index, chunk_text in enumerate(
            page_chunks
        ):
            chunks.append({
                "page_number": page_number,
                "chunk_index": chunk_index,
                "content": chunk_text
            })

    return chunks