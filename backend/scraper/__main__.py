"""Ingestion worker.

    python -m scraper --source all --limit 40
    python -m scraper --source langorigami.com --limit 0   # 0 = no limit
    python -m scraper --takedown https://example.com/page   # remove and block a URL
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402
from scraper.fetcher import Fetcher  # noqa: E402
from scraper.sources import SOURCES  # noqa: E402


def run(source_names, limit: int, use_cache: bool) -> None:
    fetcher = Fetcher(use_cache=use_cache)
    with db.connect() as conn:
        for name in source_names:
            src = SOURCES[name]
            urls = src.list_urls(fetcher)
            if limit:
                urls = urls[:limit]
            print(f"{name}: {len(urls)} pages")
            saved = 0
            for i, url in enumerate(urls, 1):
                html = fetcher.get(url)
                record = src.parse(url, html) if html else None
                if record:
                    db.upsert_model(conn, record)
                    saved += 1
                    conn.commit()
                print(f"  [{i}/{len(urls)}] {'saved' if record else 'skipped'} {url}")
            print(f"{name}: saved {saved}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="all", choices=["all", *SOURCES])
    ap.add_argument("--limit", type=int, default=40, help="pages per source; 0 for all")
    ap.add_argument("--no-cache", action="store_true", help="refetch pages already cached")
    ap.add_argument("--takedown", metavar="URL", help="delete a URL and never index it again")
    args = ap.parse_args()
    if args.takedown:
        with db.connect() as conn:
            db.add_takedown(conn, args.takedown)
        print(f"removed and blocked {args.takedown}")
        return
    names = list(SOURCES) if args.source == "all" else [args.source]
    run(names, args.limit, not args.no_cache)


if __name__ == "__main__":
    main()
