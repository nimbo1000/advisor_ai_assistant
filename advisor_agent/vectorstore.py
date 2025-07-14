# Make sure to install chromadb and langchain: pip install chromadb langchain
import os
from langchain_community.vectorstores.pgvector import PGVector
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDINGS_MODEL = os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-ada-002")

PGVECTOR_CONNECTION_STRING = os.getenv("PGVECTOR_CONNECTION_STRING", "postgresql://jump_app_user:bDezwu848D1eI8rcaawDqRzopshmyqo1@dpg-d1pup9nfte5s73cpe84g-a.oregon-postgres.render.com/jump_app")
PGVECTOR_COLLECTION_NAME = os.getenv("PGVECTOR_COLLECTION_NAME", "advisor_agent_docs")

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model=OPENAI_EMBEDDINGS_MODEL)

vectorstore = PGVector(
    connection_string=PGVECTOR_CONNECTION_STRING,
    embedding_function=embeddings,
    collection_name=PGVECTOR_COLLECTION_NAME,
)

def add_documents_to_vectorstore(user_id, docs, source):
    """
    docs: List of dicts, each with at least 'text' and 'external_id'.
    source: 'gmail', 'hubspot_contact', 'hubspot_note', etc.
    """
    user_id_str = str(user_id)
    texts = []
    metadatas = []
    ids = []
    for doc in docs:
        metadata = {
            'user_id': user_id_str,
            'source': source,
            'external_id': doc['external_id'],
        }
        for k, v in doc.items():
            if k not in ('text', 'external_id'):
                metadata[k] = v
        texts.append(doc['text'])
        metadatas.append(metadata)
        ids.append(f"{user_id_str}:{source}:{doc['external_id']}")
    if texts:
        vectorstore.add_texts(texts, metadatas=metadatas, ids=ids)
        print(f"Added {docs} for {user_id}")

def query_user_documents(user_id, query, top_k=5, type=None):
    """
    Retrieve top_k documents for a user matching the query, optionally filtered by type.
    Accepts user_id as int, str, dict with 'user_id', or JSON string.
    """
    # Handle user_id as JSON string or dict (e.g., '{"user_id": 1}' or {'user_id': 1})
    import json
    if isinstance(user_id, str):
        try:
            parsed = json.loads(user_id)
            if isinstance(parsed, dict) and 'user_id' in parsed:
                user_id = parsed['user_id']
        except Exception:
            pass
    if isinstance(user_id, dict) and 'user_id' in user_id:
        user_id = user_id['user_id']
    user_id_str = str(user_id)
    # Build filter for similarity_search
    filter_dict = None
    if type is not None:
        filter_dict = {"type": type}
    results = vectorstore.similarity_search(query, k=top_k, filter=filter_dict) if filter_dict else vectorstore.similarity_search(query, k=top_k)
    print(f"results: {results}")
    print(f"user_id {user_id}")
    filtered = []
    for doc in results:
        meta = doc.metadata
        if meta.get('user_id') == user_id_str:
            if type is None or meta.get('type') == type:
                filtered.append(doc)
    return {
        'documents': [[doc.page_content] for doc in filtered],
        'metadatas': [[doc.metadata] for doc in filtered],
    } 