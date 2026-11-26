"""Allowlisted sources. Each module exposes NAME, list_urls(fetcher), and parse(url, html)."""
from . import langorigami, origami_me

SOURCES = {m.NAME: m for m in (origami_me, langorigami)}
