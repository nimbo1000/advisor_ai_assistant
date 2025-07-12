import os
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Use OpenAI embeddings with the provided API key
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Set up ChromaDB vector store (local directory)
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory=CHROMA_PERSIST_DIR,
    collection_name="advisor_documents",
)

# Example: Add a document
# vectorstore.add_texts(["This is an email body or note or event description"], metadatas=[{"type": "email"}])

# Example: Query for similar documents
# results = vectorstore.similarity_search("What was my last meeting?", k=3)
# print(results) 