"""BM25 search over the catalog with a small origami-aware synonym map."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List

TOKEN = re.compile(r"[a-z0-9]+")
STOP = {"a", "an", "the", "of", "to", "how", "fold", "folding", "make", "origami", "paper",
        "easy", "step", "by", "instructions", "and", "for", "with", "my", "i", "want", "opus"}

# Words a person might type -> words that appear in model titles.
SYNONYMS: Dict[str, List[str]] = {
    "bird": ["crane", "swan", "dove", "owl", "parrot", "eagle", "penguin", "flamingo", "hummingbird"],
    "flower": ["tulip", "rose", "lily", "lotus", "iris", "flower", "blossom"],
    "cat": ["cat", "kitten", "lucky"],
    "dog": ["dog", "puppy", "fox", "wolf"],
    "fish": ["fish", "koi", "angelfish", "goldfish", "shark", "whale", "dolphin"],
    "bug": ["insect", "beetle", "butterfly", "spider", "scorpion", "mantis", "cicada", "treehopper"],
    "insect": ["insect", "beetle", "butterfly", "spider", "scorpion", "mantis", "cicada", "treehopper"],
    "box": ["box", "masu", "container", "tray"],
    "plane": ["airplane", "plane", "glider", "dart", "jet"],
    "star": ["star", "kusudama", "ornament", "shuriken"],
    "dragon": ["dragon", "lizard", "dinosaur"],
    "frog": ["frog", "toad"],
    "heart": ["heart", "valentine"],
}


def tokenize(text: str) -> List[str]:
    out = []
    for t in TOKEN.findall((text or "").lower()):
        if t in STOP:
            continue
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]  # crude plural stemming: cranes -> crane
        out.append(t)
    return out


def expand(tokens: Iterable[str]) -> Dict[str, float]:
    """Query term weights: typed words count fully, synonyms count half."""
    weights: Dict[str, float] = {}
    for t in tokens:
        weights[t] = max(weights.get(t, 0), 1.0)
        for s in SYNONYMS.get(t, []):
            weights[s] = max(weights.get(s, 0), 0.5)
    return weights


def _doc_text(m: dict) -> str:
    # Title words are repeated so a title hit outranks a passing mention.
    title = m.get("title", "")
    return " ".join([title, title, title, " ".join(m.get("tags", [])),
                     m.get("designer") or "", m.get("description") or ""])


def search(models: List[dict], query: str, limit: int = 12,
           extra_terms: Iterable[str] = ()) -> List[dict]:
    q = expand(tokenize(query) + [t for term in extra_terms for t in tokenize(term)])
    if not q or not models:
        return []
    docs = [Counter(tokenize(_doc_text(m))) for m in models]
    n = len(docs)
    avg = sum(sum(d.values()) for d in docs) / n
    df = Counter(t for d in docs for t in d)
    k1, b = 1.4, 0.75
    scored = []
    for m, d in zip(models, docs):
        length = sum(d.values())
        score = 0.0
        for term, w in q.items():
            tf = d.get(term, 0)
            if not tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += w * idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / avg))
        if score > 0:
            scored.append((score, m))
    scored.sort(key=lambda x: -x[0])
    return [{**m, "score": round(s, 3)} for s, m in scored[:limit]]
