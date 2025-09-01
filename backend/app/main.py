
"""
FastAPI backend for Smart Library
- /healthz: liveness probe
- /respond: SSE endpoint that streams Assistant output using OpenAI Responses API
  with RAG context (Chroma). Tool-calling este ocolit temporar: selectăm titlul
  în backend și injectăm rezumatul în pasul de streaming.

Env (.env la rădăcină recomandat):
  OPENAI_API_KEY=sk-...
  OPENAI_MODEL=gpt-4.1-nano
  EMBEDDING_MODEL=text-embedding-3-small
  CHROMA_DIR=backend/app/data/vector_store
  CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from openai import OpenAI
from .moderation import is_offensive

from .rag import init_store, retrieve
from .app_types import ChatRequest, FinalResponse  
load_dotenv()

# -----------------------------
# App & Config
# -----------------------------

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano")


def _parse_cors() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(title="Smart Library Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helpers (SSE)
# -----------------------------


def _sse(data: str, event: Optional[str] = None) -> bytes:
    """
    Construiește un frame SSE. Dacă 'event' e prezent, include linia 'event:'.
    """
    payload = f"event: {event}\n" if event else ""
    payload += f"data: {data}\n\n"
    return payload.encode("utf-8")


# -----------------------------
# Responses helpers (fără tool-calling)
# -----------------------------

def _select_title(message: str, context_items: List[Dict]) -> str:
    """
    Pas scurt non-stream: cere modelului să aleagă UN titlu din context.
    Răspuns dorit: {"title":"..."} (strict JSON).
    Dacă eșuează, întoarce primul titlu din context sau "".
    """
    titles = [str(x.get("title", "")).strip() for x in context_items if x.get("title")]
    titles = [t for t in titles if t]
    if not titles:
        return ""

    client = OpenAI()

    system = (
        "Alege EXACT UN titlu din lista dată. Răspunde STRICT ca JSON valid pe o singură linie: "
        '{"title":"..."} Fără backticks, fără explicații.'
    )
    user = f"Cerere: {message}\nTitluri candidate: " + "; ".join(titles)

    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    text = (resp.output_text or "").strip()
    try:
        data = json.loads(text)
        chosen = str(data.get("title", "")).strip()
        return chosen if chosen in titles else (titles[0] if titles else "")
    except Exception:
        return titles[0] if titles else ""


async def _stream_final_with_summary(
    message: str, context_items: List[Dict], title: str
) -> AsyncIterator[bytes]:
    """
    Pas de streaming: trimite către model cererea + titlul ales + rezumatul local
    (fără tool-calling). Streamuiește textul ca 'token' și la final emite 'final'
    cu payload JSON (FinalResponse).
    """
    from .tools import get_summary_by_title 
    summary = get_summary_by_title(title) if title else ""

    client = OpenAI()

    system = (
        "Ești „Bibliotecarul Asistent”. Recomandă concis O SINGURĂ carte și explică pe scurt „De ce”. "
        "Apoi inserează rezumatul complet furnizat (nu inventa). Rămâi în română, prietenos și clar."
    )
    def _fmt(item: Dict) -> str:
        t = str(item.get("title", "") or "")
        a = ", ".join(item.get("authors", []) or [])
        s = str(item.get("summary", "") or "")
        return f"Titlu: {t}\nAutori: {a}\nRezumat scurt: {s[:350]}..."

    rag_block = "\n\n".join(_fmt(x) for x in context_items) if context_items else "—"
    user = (
        f"Cerere utilizator: {message}\n\n"
        f"Titlu ales: {title or 'N/A'}\n\n"
        f"CONTEXT (din RAG, pentru orientare – nu inventa altele):\n{rag_block}\n\n"
        f"Rezumat complet pentru titlul ales (din sursă locală):\n{summary}\n\n"
        "Structură răspuns:\n"
        "1) O propoziție cu recomandarea (doar un titlu).\n"
        "2) De ce se potrivește (2–3 fraze).\n"
        "3) Rezumatul complet (exact cum e furnizat mai sus)."
    )

    with client.responses.stream(
        model=OPENAI_MODEL,
        input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    ) as stream:
        for event in stream:
            if event.type == "response.output_text.delta":
                yield _sse(event.delta, event="token")

    final_payload = FinalResponse(
        final=True,
        recommendation={"title": title},
        summary=summary or None,
    ).model_dump()
    yield _sse(json.dumps(final_payload), event="final")

async def _stream_policy_reply() -> AsyncIterator[bytes]:
    msg = ("Aș vrea să păstrăm conversația politică și respectuoasă. "
           "Poți reformula mesajul fără termeni ofensatori?")
    yield _sse(msg, event="token")
    final_payload = FinalResponse(final=True).model_dump()
    yield _sse(json.dumps(final_payload), event="final")

# -----------------------------
# Lifecycle
# -----------------------------

@app.on_event("startup")
def _on_startup():
    try:
        added, skipped = init_store(force=False)
        print(f"[startup] Chroma ready. added={added}, skipped={skipped}")
    except Exception as e:
        print(f"[startup] init_store warning: {e}")


# -----------------------------
# Routes
# -----------------------------

@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


@app.post("/respond")
async def respond(payload: ChatRequest):
    """
    Body validat prin ChatRequest: { "message": "vreau o carte fantasy..." }

    Stream:
      - event: token → data: string (delta text)
      - event: final → data: FinalResponse (JSON)
      - event: error → data: { "error": "..." }
    """
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Field 'message' is required")

    bad = is_offensive(message)
    if bad:
        async def event_generator_policy():
            try:
                async for chunk in _stream_policy_reply():
                    yield chunk
            except Exception as e:
                yield _sse(json.dumps({"error": str(e)}), event="error")
        return StreamingResponse(event_generator_policy(), media_type="text/event-stream")

    context_items = retrieve(message, k=3)

    title = _select_title(message, context_items)

    async def event_generator() -> AsyncIterator[bytes]:
        try:
            async for chunk in _stream_final_with_summary(message, context_items, title):
                yield chunk
        except Exception as e:
            err = {"error": str(e)}
            yield _sse(json.dumps(err), event="error")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
