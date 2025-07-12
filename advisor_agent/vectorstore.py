from .vectorstore_pg import vectorstore

def retrieve_relevant_context(query, user_id=None):
    # Use ChromaDB vectorstore for semantic search
    print(f"[VECTORSTORE] Retrieve context for query: {query}")
    results = vectorstore.similarity_search(query, k=3)
    # Return the content and metadata for each result
    return [f"{doc.page_content} (metadata: {doc.metadata})" for doc in results] 