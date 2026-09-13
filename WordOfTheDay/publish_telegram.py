#!/usr/bin/env python3
"""Publish one scheduled Word of the Day package to a Telegram channel."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")
REGISTRY_ENTRY_RE = re.compile(
    r"\{\s*word:\s*['\"](?P<word>[^'\"]+)['\"]\s*,"
    r"\s*date:\s*['\"](?P<date>\d{4}-\d{2}-\d{2})['\"]\s*,"
    r"\s*href:\s*['\"](?P<href>[^'\"]+)['\"]\s*,?\s*\}",
    re.DOTALL,
)
MAX_MESSAGE_LENGTH = 4096


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        dest="target_date",
        help="Publication date in YYYY-MM-DD. Default: today's date in Asia/Tehran.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and show the selected package without posting.")
    parser.add_argument("--force", action="store_true", help="Post again even if the ledger marks this date complete.")
    return parser.parse_args()


def parse_date(raw: str | None) -> str:
    if not raw:
        return datetime.now(TEHRAN).date().isoformat()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError(f"Invalid --date value {raw!r}; expected YYYY-MM-DD") from exc


def load_registry(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    entries = [match.groupdict() for match in REGISTRY_ENTRY_RE.finditer(text)]
    if not entries:
        raise ValueError(f"No dated entries could be read from {path}")
    return entries


def select_entry(entries: list[dict[str, str]], target_date: str) -> dict[str, str]:
    matches = [entry for entry in entries if entry["date"] == target_date]
    if not matches:
        raise ValueError(f"No Word of the Day entry is registered for {target_date}")
    if len(matches) > 1:
        words = ", ".join(entry["word"] for entry in matches)
        raise ValueError(f"Multiple entries are registered for {target_date}: {words}")
    return matches[0]


def slug_from_href(href: str) -> str:
    filename = Path(href).name
    suffix = "-extended.html"
    if not filename.endswith(suffix):
        raise ValueError(f"Unexpected WOTD page filename in registry: {href}")
    return filename[: -len(suffix)]


def public_page_url(repository_root: Path, href: str) -> str:
    """Build the deployed page URL from GitHub Pages configuration."""
    domain = (repository_root / "CNAME").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[A-Za-z0-9.-]+", domain):
        raise ValueError("CNAME must contain one valid deployment hostname")
    encoded_path = urllib.parse.quote(href.lstrip("/"), safe="/")
    return f"https://{domain}/{encoded_path}"


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "posts": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("posts"), dict):
        raise ValueError(f"Invalid Telegram publication ledger: {path}")
    return data


def save_ledger(path: Path, ledger: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def multipart_body(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = f"----kooshky-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            value.encode("utf-8"),
            b"\r\n",
        ])
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode(),
        f"Content-Type: {mime_type}\r\n\r\n".encode(),
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def telegram_request(token: str, method: str, body: bytes, content_type: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=body,
        headers={"Content-Type": content_type, "User-Agent": "Kooshky-WOTD-Publisher/1.0"},
        method="POST",
    )
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not payload.get("ok"):
                raise RuntimeError(f"Telegram rejected {method}: {payload.get('description', 'unknown error')}")
            return payload["result"]
        except urllib.error.HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                error_payload = {}
            retry_after = error_payload.get("parameters", {}).get("retry_after")
            if attempt < 3 and (exc.code == 429 or exc.code >= 500):
                time.sleep(min(int(retry_after or attempt * 2), 30))
                continue
            description = error_payload.get("description", f"HTTP {exc.code}")
            raise RuntimeError(f"Telegram {method} failed: {description}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            raise RuntimeError(f"Telegram {method} could not connect after 3 attempts") from exc
    raise RuntimeError(f"Telegram {method} failed")


def send_photo(token: str, channel: str, banner: Path, caption: str) -> int:
    body, content_type = multipart_body({"chat_id": channel, "caption": caption}, "photo", banner)
    result = telegram_request(token, "sendPhoto", body, content_type)
    return int(result["message_id"])


def send_text(token: str, channel: str, message: str) -> int:
    body = json.dumps({"chat_id": channel, "text": message}).encode("utf-8")
    result = telegram_request(token, "sendMessage", body, "application/json")
    return int(result["message_id"])


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    repository_root = base_dir.parent
    target_date = parse_date(args.target_date)
    entry = select_entry(load_registry(base_dir / "word-data.js"), target_date)
    slug = slug_from_href(entry["href"])
    page_url = public_page_url(repository_root, entry["href"])
    photo_caption = f"full explanation: {page_url}"
    html_path = repository_root / entry["href"]
    message_path = base_dir / "generated" / f"{slug}-telegram.txt"
    banner_path = base_dir / "banners" / f"{slug}-banner.png"
    ledger_path = base_dir / "telegram-posted.json"

    missing = [str(path.relative_to(repository_root)) for path in (html_path, message_path, banner_path) if not path.is_file()]
    if missing:
        raise ValueError("Missing publication file(s): " + ", ".join(missing))
    if banner_path.stat().st_size == 0:
        raise ValueError(f"Banner is empty: {banner_path}")

    message = message_path.read_text(encoding="utf-8").strip()
    if not message:
        raise ValueError(f"Telegram message is empty: {message_path}")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Telegram message is {len(message)} characters; maximum is {MAX_MESSAGE_LENGTH}")

    ledger = load_ledger(ledger_path)
    posts = ledger["posts"]
    previous = posts.get(target_date)
    if previous and previous.get("status") == "complete" and not args.force:
        print(f"SKIP: {entry['word']} for {target_date} is already recorded as posted.")
        return 0

    print(f"Selected: {entry['word']} ({target_date})")
    print(f"Page: {html_path.relative_to(repository_root)}")
    print(f"Banner: {banner_path.relative_to(repository_root)}")
    print(f"Photo caption: {photo_caption}")
    print(f"Message: {message_path.relative_to(repository_root)} ({len(message)} characters)")
    if args.dry_run:
        print("DRY RUN: no Telegram request was made and the ledger was not changed.")
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip()
    if not token or not channel:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must both be set")

    if args.force or not previous:
        previous = {
            "word": entry["word"],
            "slug": slug,
            "date": target_date,
            "status": "pending",
        }
        posts[target_date] = previous

    if not previous.get("photo_message_id"):
        previous["photo_message_id"] = send_photo(token, channel, banner_path, photo_caption)
        previous["status"] = "photo_sent"
        previous["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_ledger(ledger_path, ledger)
        print(f"Photo posted as message {previous['photo_message_id']}.")

    if not previous.get("text_message_id"):
        previous["text_message_id"] = send_text(token, channel, message)
        previous["status"] = "complete"
        previous["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_ledger(ledger_path, ledger)
        print(f"Text posted as message {previous['text_message_id']}.")

    print(f"DONE: posted {entry['word']} to {channel}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
