"""Polite HTTP fetching: robots.txt, per-host rate limits, and an on-disk cache."""
from __future__ import annotations

import hashlib
import os
import time
import urllib.robotparser
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
USER_AGENT = os.environ.get(
    "SCRAPER_USER_AGENT",
    "OrigamiPatternStudio/0.1 (indexes titles and links back to the source)",
)
MIN_DELAY = float(os.environ.get("SCRAPER_DELAY", "2.0"))


class Fetcher:
    def __init__(self, use_cache: bool = True):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.use_cache = use_cache
        self._robots: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last: Dict[str, float] = {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _robots_for(self, url: str) -> urllib.robotparser.RobotFileParser:
        host = urlparse(url).netloc
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{host}/robots.txt"
            try:
                resp = self.session.get(robots_url, timeout=15)
                rp.parse(resp.text.splitlines() if resp.ok else [])
            except requests.RequestException:
                rp.parse(["User-agent: *", "Disallow: /"])  # unknown -> stay out
            self._robots[host] = rp
        return self._robots[host]

    def allowed(self, url: str) -> bool:
        return self._robots_for(url).can_fetch(USER_AGENT, url)

    def _wait(self, url: str) -> None:
        host = urlparse(url).netloc
        delay = max(MIN_DELAY, float(self._robots_for(url).crawl_delay(USER_AGENT) or 0))
        elapsed = time.monotonic() - self._last.get(host, 0)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last[host] = time.monotonic()

    def get(self, url: str) -> Optional[str]:
        key = CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest() + ".html")
        if self.use_cache and key.exists():
            return key.read_text(encoding="utf-8")
        if not self.allowed(url):
            print(f"  skip (robots.txt): {url}")
            return None
        self._wait(url)
        try:
            resp = self.session.get(url, timeout=20)
        except requests.RequestException as e:
            print(f"  error {url}: {e}")
            return None
        if resp.status_code == 429:
            print("  rate-limited; backing off 60s")
            time.sleep(60)
            return None
        if not resp.ok:
            print(f"  HTTP {resp.status_code}: {url}")
            return None
        key.write_text(resp.text, encoding="utf-8")
        return resp.text
