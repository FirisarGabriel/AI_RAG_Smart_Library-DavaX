
# -----------------------------
# IMPORTURI ȘI CONFIGURARE
# -----------------------------

import streamlit as st
import chromadb
from chromadb.config import Settings
import openai
import os
from dotenv import load_dotenv

# Încarcă cheia API din .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# -----------------------------

st.set_page_config(page_title="AI RAG Smart Library", layout="centered")

st.title("AI RAG Smart Library")
st.write("Aplicație demo pentru interogarea bazei de date cu ajutorul LLM și RAG.")

# -----------------------------
# INIȚIALIZARE CHROMADB
# -----------------------------
client = chromadb.Client(Settings(persist_directory="./chroma_db"))
collection = client.get_or_create_collection("books")

# -----------------------------
# FUNCȚIE: Obține embedding pentru text folosind OpenAI
# -----------------------------
def get_embedding(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# -----------------------------
# FUNCȚIE: Caută cărți relevante în ChromaDB folosind embedding
# -----------------------------
def search_books(query, top_k=1):
    embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k
    )
    if results["documents"] and results["documents"][0]:
        return results["metadatas"][0][0]["title"], results["documents"][0][0]
    return None, None

# -----------------------------
# UI PRINCIPAL: Un singur input pentru întrebare, cu resetare
# -----------------------------
if "question" not in st.session_state:
    st.session_state["question"] = ""

question = st.text_input(
    "Introdu o întrebare despre cărți sau conținutul lor:",
    value=st.session_state["question"],
    key="main_question"
)

if st.button("Resetare"):
    st.session_state["question"] = ""
    st.experimental_rerun()

# -----------------------------
# LOGICA RAG + GPT: Căutare și generare răspuns
# -----------------------------
if question:
    st.session_state["question"] = question
    with st.spinner("Se caută răspuns..."):
        title, context = search_books(question, top_k=1)
        if context:
            st.subheader(f"Cartea relevantă: {title}")
            st.write(f"Context extras din bază de date:")
            st.code(context, language="markdown")
            prompt = f"Întrebare: {question}\nContext: {context}\nRăspuns:"
            try:
                response = openai.chat.completions.create(
                    model="gpt-4.1-nano",  # GPT-4.1-nano
                    messages=[{"role": "system", "content": "Ești un asistent care răspunde la întrebări despre cărți."},
                              {"role": "user", "content": prompt}]
                )
                answer = response.choices[0].message.content
                st.success("Răspuns generat de LLM:")
                st.write(answer)
            except Exception as e:
                st.error(f"Eroare la generarea răspunsului: {e}")
        else:
            st.warning("Nu s-a găsit context relevant în baza de date.")
else:
    st.write("Introdu o întrebare pentru a primi răspunsuri inteligente.")

# -----------------------------
# FUNCȚIE: Recomandare carte cu GPT (opțional, pentru extensie)
# -----------------------------
def gpt_recommendation(user_query, book_title, book_summary):
    prompt = (
        f"User asked: {user_query}\n"
        f"Recommended book: {book_title}\n"
        f"Summary: {book_summary}\n"
        "Please answer in a conversational way, recommending the book and why it fits the user's interests."
    )
    response = openai.chat.completions.create(
        model="gpt-4.1-nano",  # GPT-4.1-nano
        messages=[{"role": "system", "content": "You are a helpful book recommender."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# -----------------------------
# UI Recomandare carte (opțional, extensie)
# -----------------------------
st.header("AI Book Recommender (RAG + GPT)")
user_input = st.text_input("Ce fel de carte cauți?", key="recommender_input")

if user_input:
    title, summary = search_books(user_input)
    if title:
        st.subheader(f"Recomandare: {title}")
        st.write(summary)
        gpt_resp = gpt_recommendation(user_input, title, summary)
        st.markdown(f"**GPT:** {gpt_resp}")
    else:
        st.write("Nu am găsit nicio carte potrivită.")
