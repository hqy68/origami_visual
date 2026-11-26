"""origami.me: step-by-step tutorials. We index title, designer, difficulty, summary and
the cover image URL, and send readers to origami.me for the actual instructions."""
from __future__ import annotations

from typing import List, Optional

from bs4 import BeautifulSoup

from .common import clean, meta, sitemap_locs, tags_from_title

NAME = "origami.me"
SITEMAPS = ["https://origami.me/post-sitemap1.xml", "https://origami.me/post-sitemap2.xml"]


def list_urls(fetcher) -> List[str]:
    urls: List[str] = []
    for sm in SITEMAPS:
        urls += [u for u in sitemap_locs(fetcher.get(sm)) if "/wp-content/" not in u]
    return urls


def parse(url: str, html: str) -> Optional[dict]:
    soup = BeautifulSoup(html, "html.parser")
    designer_el = soup.select_one(".designer .fn")
    if not designer_el:
        return None  # not a model tutorial (guides, paper reviews, news)
    h1 = soup.select_one("h1.entry-title") or soup.find("h1")
    title = clean(h1.get_text()) if h1 else None
    if not title:
        return None
    difficulty = None
    for li in soup.select("li"):
        strong = li.find("strong")
        if strong and strong.get_text(strip=True).lower().startswith("difficulty"):
            difficulty = clean(li.get_text().split(":", 1)[-1])
            break
    short = title
    for prefix in ("How to Fold a Traditional Origami ", "How to Fold an Origami ",
                   "How to Fold a Origami ", "How to Fold an ", "How to Fold a ", "How to Make an Origami ",
                   "How to Make a Origami ", "How to Make an ", "How to Make a ", "How to Fold ", "How to Make "):
        if short.startswith(prefix):
            short = short[len(prefix):]
            break
    for word in ("Easy Origami ", "Origami "):
        if short.startswith(word):
            short = short[len(word):]
    return {
        "source": NAME,
        "url": url,
        "title": short,
        "designer": clean(designer_el.get_text()),
        "kind": "tutorial",
        "difficulty": difficulty,
        "description": meta(soup, "og:description"),
        "image_url": meta(soup, "og:image"),
        "tags": tags_from_title(title),
        "license_note": "Tutorial content belongs to origami.me and the designer; follow the link to view it.",
    }
