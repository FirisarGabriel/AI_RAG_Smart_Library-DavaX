
"""
Local tools callable by the LLM (OpenAI Responses) for the Smart Library project.

Ce oferă:
- get_summary_by_title(title: str) -> str
- get_tools() -> list[dict] (schema pentru Responses)
- build_tool_outputs(required_action: dict) -> list[dict]

Data source: backend/app/data/book_summaries.json
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional
from difflib import get_close_matches

from pydantic import BaseModel
from openai import pydantic_function_tool

# -----------------------------
# Paths & data loading
# -----------------------------

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]  
DATA_DIR = pathlib.Path(__file__).parent / "data"
BOOKS_JSON = DATA_DIR / "book_summaries.json"


def _load_books() -> List[Dict[str, Any]]:
    if not BOOKS_JSON.exists():
        raise FileNotFoundError(f"books file not found: {BOOKS_JSON}")
    with open(BOOKS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("book_summaries.json must contain a list of books")
    return data


def _norm(s: str) -> str:
    return (s or "").strip().casefold()


_BOOKS_CACHE: Optional[List[Dict[str, Any]]] = None
_TITLE_INDEX: Optional[Dict[str, Dict[str, Any]]] = None


def _ensure_cache() -> None:
    global _BOOKS_CACHE, _TITLE_INDEX
    if _BOOKS_CACHE is None or _TITLE_INDEX is None:
        books = _load_books()
        _BOOKS_CACHE = books
        _TITLE_INDEX = {}
        for b in books:
            title = str(b.get("title", "")).strip()
            if title:
                _TITLE_INDEX[_norm(title)] = b


# -----------------------------
# Public implementation
# -----------------------------

def get_summary_by_title(title: str) -> str:
    _ensure_cache()
    assert _BOOKS_CACHE is not None and _TITLE_INDEX is not None

    if not title or not title.strip():
        return "Nu am primit niciun titlu. Te rog trimite un titlu de carte valid."

    key = _norm(title)

    if key in _TITLE_INDEX:
        book = _TITLE_INDEX[key]
        summary = str(book.get("summary") or "").strip()
        if summary:
            return summary
        return f"Cartea „{book.get('title','(fără titlu)')}” nu are un rezumat disponibil."

    candidates = [b for tkey, b in _TITLE_INDEX.items() if key in tkey or tkey.startswith(key)]
    if not candidates:
        all_titles = [b.get("title", "") for b in _BOOKS_CACHE]
        close = get_close_matches(title, all_titles, n=1, cutoff=0.6)
        if close:
            close_title = close[0]
            book = _TITLE_INDEX[_norm(close_title)]
            summary = str(book.get("summary") or "").strip()
            if summary:
                return summary
            return f"Am găsit cartea cea mai apropiată „{close_title}”, dar nu are rezumat."
        return f"Nu am găsit nicio carte cu titlul „{title}”."

    best = candidates[0]
    summary = str(best.get("summary") or "").strip()
    if summary:
        return summary
    return f"Cartea „{best.get('title','(necunoscut)')}” nu are rezumat disponibil."


# -----------------------------
# Responses tool schema
# -----------------------------
from pydantic import BaseModel
from openai import pydantic_function_tool

class GetSummaryArgs(BaseModel):
    title: str

def _tool_get_summary_by_title(args: GetSummaryArgs) -> str:
    return get_summary_by_title(args.title)

def get_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_summary_by_title",
                "description": (
                    "Returnează rezumatul complet al unei cărți din colecția locală, "
                    "identificată prin titlu (case-insensitive, toleranță la mici greșeli)."
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Titlul exact sau aproximativ al cărții."
                        }
                    },
                    "required": ["title"],
                    "additionalProperties": False
                },
            },
        }
    ]

# -----------------------------
# Helper pentru tool_outputs
# -----------------------------

def build_tool_outputs(required_action: Dict[str, Any]) -> List[Dict[str, str]]:
    if not required_action or required_action.get("type") != "submit_tool_outputs":
        return []

    tool_calls = required_action.get("submit_tool_outputs", {}).get("tool_calls") or []
    outputs: List[Dict[str, str]] = []

    for call in tool_calls:
        call_id = call.get("id")
        fn = (call.get("function") or {})
        name = fn.get("name")
        raw_args = fn.get("arguments")

        output_str = "Eroare: nu am putut executa funcția."
        try:
            if isinstance(raw_args, dict):
                args = raw_args
            elif isinstance(raw_args, str) and raw_args.strip():
                args = json.loads(raw_args)
            else:
                args = {}

            if name == "get_summary_by_title":
                output_str = get_summary_by_title(str(args.get("title", "")))
            else:
                output_str = f"Eroare: funcție necunoscută '{name}'."
        except Exception as e:
            output_str = f"Eroare la executarea funcției '{name}': {e}"

        if call_id:
            outputs.append({"tool_call_id": call_id, "output": output_str})

    return outputs


def list_titles() -> List[str]:
    _ensure_cache()
    assert _BOOKS_CACHE is not None
    return [str(b.get("title", "")) for b in _BOOKS_CACHE]
