from app.services.embedding_service import generate_embedding


text="The school admission fee for Grade 1 is ₹50,000."


try:
    embedding=generate_embedding(text)

    print("Embedding genarated successfully")
    print(f"vectore dimensions:{ len(embedding)}")
    print(f"First 5 Values:{embedding[:100]}")

except Exception as e:
     print("Embedding generation failed")
     print("Error:", e)