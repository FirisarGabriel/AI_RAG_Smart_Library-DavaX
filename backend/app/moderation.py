from __future__ import annotations
import re
from typing import Optional

OFFENSIVE_PATTERNS = [
    r"\bidiot\w*\b",
    r"\bprost\w*\b",
    r"\bnesimțit\w*\b",
    r"\bjeg\w*\b",
    r"\bjigod\w*\b",
    r"\bjigăod\w*\b",
    r"\bbozgor\w*\b",     
    r"\bdoamne\-fer\w*\b",
    r"\bdracu\w*\b",
    r"\bnaib\w*\b",
    r"\bpul\w*\b",      
    r"\bcur\w*\b",
    r"\bmuist\w*\b",
    r"\bțigan\w*\b",       
    r"\bhandicapat\w*\b",
    r"\bbou\w*\b",
    r"\bboulean\w*\b",
    r"\bporc\w*\b",
    r"\bvacă\w*\b",
    r"\bgunoa\w*\b",
    r"\bmăgar\w*\b",
    r"\bzdrențăros\w*\b",
    r"\bjavr\w*\b",
    r"\bmoron\w*\b",
    r"\bjerk\w*\b",
    r"\bjackass\w*\b",
    r"\basshole\w*\b",
    r"\bshit\w*\b",
    r"\bfuck\w*\b",
    r"\bcunt\w*\b",
    r"\bretard\w*\b",
    r"\bbitch\w*\b",
    r"\bwhore\w*\b",
    r"\bslut\w*\b",
    r"\bbastard\w*\b",
]

_COMPILED = re.compile("|".join(OFFENSIVE_PATTERNS), re.IGNORECASE | re.UNICODE)

def is_offensive(text: str) -> Optional[str]:
    """
    Returnează termenul găsit dacă textul conține limbaj nepotrivit; altfel None.
    Nu trimite nicăieri textul — e local only.
    """
    if not text:
        return None
    m = _COMPILED.search(text)
    return m.group(0) if m else None
