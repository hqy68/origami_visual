from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from bs4 import BeautifulSoup

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def sitemap_locs(xml_text: Optional[str]) -> List[str]:
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        return re.findall(r"<loc>([^<]+)</loc>", xml_text)
    return [el.text.strip() for el in root.iter(f"{{{NS['sm']}}}loc") if el.text]


def meta(soup: BeautifulSoup, prop: str) -> Optional[str]:
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return tag.get("content").strip() if tag and tag.get("content") else None


def clean(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def tags_from_title(title: str) -> List[str]:
    words = re.findall(r"[a-z]+", title.lower())
    stop = {"how", "to", "fold", "an", "a", "the", "origami", "opus", "and", "of", "easy",
            "traditional", "step", "by", "instructions", "make"}
    return sorted({w for w in words if w not in stop and len(w) > 2})
