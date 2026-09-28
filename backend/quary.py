from app.rag.query_rewriter import rewrite_query


questions = [
    "What is the admission fee for grade 1?",
    "what about grade 2?",
    "tell me about admission documents",
    "how can I contact the school?"
]


for question in questions:
    rewritten = rewrite_query(question)

    print("Original:")
    print(question)

    print("Rewritten:")
    print(rewritten)

    print("-" * 60)