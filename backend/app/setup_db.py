import json
import chromadb
from chromadb.config import Settings
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BOOKS_PATH = os.path.join(DATA_DIR, "book_summaries.json")

with open(BOOKS_PATH, "r", encoding="utf-8") as f:
    books = json.load(f)

client = chromadb.Client(Settings(persist_directory="./chroma_db"))
collection = client.get_or_create_collection("books")

def get_embedding(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

for book in books:
    embedding = get_embedding(book["summary"])
    collection.add(
        documents=[book["summary"]],
        embeddings=[embedding],
        metadatas=[{
            "title": book["title"],
            "authors": ", ".join(book.get("authors", [])), 
            "tags": ", ".join(book.get("tags", []))         
        }],
        ids=[book["title"]]
    )

print("Baza de date ChromaDB a fost populată cu rezumate, embeddings")
