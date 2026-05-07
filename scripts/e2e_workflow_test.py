from __future__ import annotations

import argparse
import json
import sys
import time

import requests


def post_text(base: str, path: str, payload: dict, timeout: int) -> str:
    r = requests.post(base + path, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.text


def get_json(base: str, path: str, timeout: int) -> dict:
    r = requests.get(base + path, timeout=timeout)
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8001")
    ap.add_argument("--book-id", required=True)
    ap.add_argument("--requirements", default="请按章节结构梳理核心观点，并给出行动清单")
    ap.add_argument("--feelings", default="我主要想学会这本书的方法论")
    ap.add_argument("--poll-seconds", type=int, default=240)
    args = ap.parse_args()

    payload = {"user_requirements": args.requirements, "user_feelings": args.feelings}
    base = args.base.rstrip("/")
    book_id = args.book_id

    ctx = post_text(base, f"/api/books/{book_id}/workflow/context", payload, timeout=300)
    print(f"[OK] Context fetched, length={len(ctx)}")

    # 2. Outline
    print("Fetching outline...")
    outline = post_text(base, f"/api/books/{book_id}/workflow/outline", payload, timeout=300)
    print(f"[OK] Outline fetched, length={len(outline)}")

    # 3. Report
    print("Fetching full report...")
    report = post_text(base, f"/api/books/{book_id}/workflow/report", payload, timeout=300)
    print(f"[OK] Report fetched, length={len(report)}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as e:
        print(f"HTTPError: {e}", file=sys.stderr)
        raise

