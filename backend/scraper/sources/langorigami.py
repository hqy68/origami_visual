"""langorigami.com: Robert J. Lang's published crease patterns. We index the title and
the crease-pattern image URL and link to his page, where the terms of use are stated."""
from __future__ import annotations

from typing import List, Optional

from bs4 import BeautifulSoup

from .common import clean, sitemap_locs, tags_from_title

NAME = "langorigami.com"
SITEMAP = "https://langorigami.com/wp-sitemap-posts-crease-pattern-1.xml"


def list_urls(fetcher) -> List[str]:
    return [u for u in sitemap_locs(fetcher.get(SITEMAP)) if "/crease-pattern/" in u]


def parse(url: str, html: str) -> Optional[dict]:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = clean(h1.get_text()) if h1 else None
    if not title:
        return None
    image = None
    # The crease pattern is the first uploaded image on the page (the logo is a theme asset).
    for img in soup.find_all("img"):
        src = img.get("data-lazy-src") or img.get("src") or ""
        if "/wp-content/uploads/" in src:
            image = src
            break
    return {
        "source": NAME,
        "url": url,
        "title": title,
        "designer": "Robert J. Lang",
        "kind": "crease_pattern",
        "difficulty": "Advanced (crease pattern only)",
        "description": f"Crease pattern for {title} by Robert J. Lang.",
        "image_url": image,
        "tags": tags_from_title(title) + ["crease", "pattern"],
        "license_note": "© Robert J. Lang. Crease pattern shown by link; see the source page for terms of use.",
    }
