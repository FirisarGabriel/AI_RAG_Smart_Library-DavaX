# Smart Library

Smart Library is an AI-powered book recommendation and summarization platform. It combines a modern React frontend with a FastAPI backend, using Retrieval-Augmented Generation (RAG) and OpenAI models to deliver relevant book suggestions and summaries in Romanian.

## Features

- **Book Recommendation:** Suggests the most relevant book for a user's query using RAG and OpenAI.
- **Local Summaries:** Injects full book summaries from a local JSON file.
- **Offensive Language Moderation:** Filters inappropriate language before processing queries.
- **Speech Synthesis:** Reads assistant responses aloud in Romanian.
- **Streaming Responses:** Uses Server-Sent Events (SSE) for incremental assistant replies.
- **Frontend:** Built with React, TypeScript, and Vite.
- **Backend:** FastAPI with Python, ChromaDB for vector storage, and OpenAI API integration.

## Project Structure

```
.
├── .env
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── app_types.py
│       ├── main.py
│       ├── moderation.py
│       ├── prompts.py
│       ├── rag.py
│       ├── setup_db.py
│       ├── tools.py
│       ├── data/
│       │   ├── book_summaries.json
│       │   └── vector_store/
│       └── __pycache__/
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── public/
│   └── src/
│       ├── App.tsx
│       ├── components/
│       ├── lib/
│       └── assets/
```

## Backend Setup

1. **Environment Variables:**  
   Create a `.env` file in the project root with:
   ```
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4.1-nano
   EMBEDDING_MODEL=text-embedding-3-small
   CHROMA_DIR=backend/app/data/vector_store
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```

2. **Install Python dependencies:**
   ```sh
   cd backend
   pip install -r requirements.txt
   ```

3. **Populate ChromaDB with book summaries:**
   ```sh
   python app/setup_db.py
   ```

4. **Start the backend server:**
   ```sh
   uvicorn app.main:app --reload
   ```

## Frontend Setup

1. **Install Node.js dependencies:**
   ```sh
   cd frontend
   npm install
   ```

2. **Start the development server:**
   ```sh
   npm run dev
   ```

3. **Access the app:**  
   Open [http://localhost:5173](http://localhost:5173) in your browser.

## Data

- **Book Summaries:** Located in `backend/app/data/book_summaries.json`
- **Vector Store:** Located in `backend/app/data/vector_store/`

## Technical Details

- **RAG Context:** The backend retrieves relevant book passages using vector similarity and builds a context block for the assistant.
- **Tool-Calling:** The assistant uses a backend tool (`get_summary_by_title`) to fetch the full summary for the selected book.
- **Streaming:** Responses are streamed to the frontend using SSE for a smooth user experience.
- **Moderation:** Queries are checked for offensive language before processing.
- **Speech Synthesis:** The frontend uses the browser's SpeechSynthesis API to read assistant replies aloud.

## Development

- **Linting:** ESLint is configured for type-aware linting in the frontend.
- **Hot Reload:** Both frontend and backend support hot reload for rapid development.
