import json
import chromadb
from chromadb.config import Settings
import openai
import os
from dotenv import load_dotenv

# Încarcă cheia API
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Încarcă datele din JSON
with open("book_summaries.json", "r", encoding="utf-8") as f:
    books = json.load(f)

# Inițializează ChromaDB local
client = chromadb.Client(Settings(persist_directory="./chroma_db"))
collection = client.get_or_create_collection("books")

def get_embedding(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# Adaugă fiecare carte în ChromaDB cu embedding
for book in books:
    embedding = get_embedding(book["summary"])
    collection.add(
        documents=[book["summary"]],
        embeddings=[embedding],
        metadatas=[{"title": book["title"]}],
        ids=[book["title"]]
    )

print("Baza de date ChromaDB a fost populată cu rezumate și embeddings!")
