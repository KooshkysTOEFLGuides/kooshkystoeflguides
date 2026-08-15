#!/usr/bin/env python3
"""Synchronize per-topic Speaking Pack prompt directories from topics.txt.

Topic numbers are stable identities. Directories without a generated HTML file
are managed by this script and may be regenerated, renamed, or removed. A topic
directory containing a top-level HTML file is locked until that HTML file is
removed explicitly.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEAKING_DIR = SCRIPT_DIR.parent
PACK_DIR = SPEAKING_DIR / "topics"
STATE_PATH = SCRIPT_DIR / ".topic-scaffolder-state.json"
TEMPLATE_NAMES = ("words.txt", "ideas.txt", "questions.txt")
OBSOLETE_PROMPT_NAMES = ("html.txt",)
HEADER_RE = re.compile(r"^#\s+(\d+)\.\s+(.+?)\s*$")
TRAILING_STATUS_RE = re.compile(r"\s+[xX✓]\s*$")
TOKEN_RE = re.compile(r"{{([A-Z][A-Z0-9_]*)}}")


@dataclass(frozen=True)
class Topic:
    number: int
    title: str
    subtopics: tuple[str, ...]

    @property
    def key(self) -> str:
        return str(self.number)

    @property
    def directory_name(self) -> str:
        return self.title

    @property
    def slug(self) -> str:
        normalized = unicodedata.normalize("NFKD", self.title)
        ascii_title = normalized.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")

    @property
    def output_filename(self) -> str:
        return f"{self.slug}-toefl-speaking-topic-pack.html"


def parse_topics(path: Path) -> list[Topic]:
    topics: list[Topic] = []
    current_number: int | None = None
    current_title = ""
    current_subtopics: list[str] = []

    def finish() -> None:
        nonlocal current_number, current_title, current_subtopics
        if current_number is None:
            return
        if not current_subtopics:
            raise ValueError(f"Topic {current_number} ({current_title}) has no subtopics")
        topics.append(Topic(current_number, current_title, tuple(current_subtopics)))

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        match = HEADER_RE.match(stripped)
        if match:
            finish()
            current_number = int(match.group(1))
            current_title = TRAILING_STATUS_RE.sub("", match.group(2)).strip()
            current_subtopics = []
            if not current_title:
                raise ValueError(f"Missing topic title on line {line_number}")
            continue
        if stripped.startswith("#"):
            continue
        if current_number is None:
            raise ValueError(f"Subtopic appears before the first numbered topic on line {line_number}")
        current_subtopics.append(stripped.removeprefix("- ").strip())

    finish()
    numbers = [topic.number for topic in topics]
    duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
    if duplicates:
        raise ValueError(f"Duplicate topic numbers: {', '.join(map(str, duplicates))}")
    return topics


def load_state() -> dict[str, dict[str, object]]:
    if not STATE_PATH.exists():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read {STATE_PATH.name}: {error}") from error
    records = data.get("topics") if isinstance(data, dict) else None
    if not isinstance(records, dict):
        raise ValueError(f"{STATE_PATH.name} has an invalid structure")
    return records


def is_locked(topic_dir: Path) -> bool:
    return topic_dir.is_dir() and any(path.is_file() for path in topic_dir.glob("*.html"))


def html_names(topic_dir: Path) -> str:
    return ", ".join(sorted(path.name for path in topic_dir.glob("*.html")))


def render(template: str, values: dict[str, str], source_name: str) -> str:
    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        if token not in values:
            raise ValueError(f"Unknown token {{{{{token}}}}} in {source_name}")
        return values[token]

    return TOKEN_RE.sub(replace, template)


def topic_values(topic: Topic) -> dict[str, str]:
    subtopics = "\n".join(f"- {item}" for item in topic.subtopics)
    return {
        "MAIN_TOPIC": topic.title,
        "SEED_SUBTOPICS": subtopics,
        "ADJACENT_PACKS": "NONE PROVIDED",
        "OUTPUT_FILENAME": topic.output_filename,
        "TOPIC_TITLE": topic.title,
        "TOPIC_SLUG": topic.slug,
        "CORPUS_PATH": "SpeakingPack/prompt/references/real-toefl-speaking-corpus.txt",
        "META_DESCRIPTION": f"A TOEFL Speaking Interview topic pack about {topic.title.lower()}, with vocabulary, reusable ideas, interview questions, and sample answers.",
        "HERO_DESCRIPTION": f"Build flexible language, ideas, and interview answers for speaking about {topic.title.lower()}.",
        "VOCABULARY_CONTENT": "{{VOCABULARY_CONTENT}}",
        "IDEA_CONTENT": "{{IDEA_CONTENT}}",
        "QUESTION_CONTENT": "{{QUESTION_CONTENT}}",
    }


def write_text(path: Path, content: str, dry_run: bool) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    return True


def state_record(topic: Topic) -> dict[str, object]:
    return {
        "number": topic.number,
        "title": topic.title,
        "directory": topic.directory_name,
        "subtopics": list(topic.subtopics),
    }


def synchronize(topics_path: Path, dry_run: bool = False, refresh_locked_prompts: bool = False) -> tuple[int, int]:
    topics = parse_topics(topics_path)
    old_state = load_state()
    new_state: dict[str, dict[str, object]] = {}
    warnings = 0
    changes = 0

    templates = {
        name: (SCRIPT_DIR / name).read_text(encoding="utf-8")
        for name in TEMPLATE_NAMES
    }
    current_keys = {topic.key for topic in topics}

    for key, record in old_state.items():
        if key in current_keys:
            continue
        directory_name = str(record.get("directory", ""))
        old_dir = PACK_DIR / directory_name
        if not directory_name or old_dir.parent != PACK_DIR:
            raise ValueError(f"Unsafe managed directory in state for topic {key!r}")
        if is_locked(old_dir):
            print(f"WARNING: topic {key} was removed from {topics_path.name}, but {directory_name!r} is locked by {html_names(old_dir)}; keeping it unchanged.", file=sys.stderr)
            new_state[key] = record
            warnings += 1
        elif old_dir.exists():
            print(f"REMOVE  {old_dir.relative_to(PACK_DIR)}")
            if not dry_run:
                shutil.rmtree(old_dir)
            changes += 1

    for topic in topics:
        record = old_state.get(topic.key)
        old_name = str(record.get("directory", "")) if record else topic.directory_name
        old_dir = PACK_DIR / old_name
        target_dir = PACK_DIR / topic.directory_name

        # Step 4 is now deterministic Python rendering, so remove the obsolete
        # model-driven HTML prompt even from otherwise locked historical packs.
        for obsolete_name in OBSOLETE_PROMPT_NAMES:
            obsolete_path = target_dir / "prompts" / obsolete_name
            if obsolete_path.is_file():
                print(f"REMOVE  {obsolete_path.relative_to(PACK_DIR)}")
                if not dry_run:
                    obsolete_path.unlink()
                changes += 1

        if record and old_name != topic.directory_name:
            if is_locked(old_dir):
                print(f"WARNING: topic {topic.number} changed from {old_name!r} to {topic.title!r}, but the old directory is locked by {html_names(old_dir)}; keeping its directory and prompts unchanged. Remove the HTML file to allow the rename.", file=sys.stderr)
                new_state[topic.key] = record
                warnings += 1
                continue
            if old_dir.exists() and target_dir.exists() and old_dir != target_dir:
                print(f"WARNING: cannot rename {old_name!r} to {topic.directory_name!r} because the destination already exists; leaving the old topic unchanged.", file=sys.stderr)
                new_state[topic.key] = record
                warnings += 1
                continue
            if old_dir.exists():
                print(f"RENAME  {old_name} -> {topic.directory_name}")
                if not dry_run:
                    old_dir.rename(target_dir)
                changes += 1

        if is_locked(target_dir) and not refresh_locked_prompts:
            changed_in_taxonomy = bool(record) and (
                record.get("title") != topic.title
                or record.get("subtopics") != list(topic.subtopics)
            )
            if changed_in_taxonomy:
                print(f"WARNING: topic {topic.number} ({topic.title}) changed in {topics_path.name}, but its directory is locked by {html_names(target_dir)}; prompts were not edited. Remove the HTML file to apply the change.", file=sys.stderr)
                warnings += 1
            else:
                print(f"LOCKED  {topic.directory_name} ({html_names(target_dir)})")
            new_state[topic.key] = state_record(topic) if not record else record
            continue

        if is_locked(target_dir):
            print(f"REFRESH {topic.directory_name} prompts (HTML remains untouched)")

        values = topic_values(topic)
        prompt_dir = target_dir / "prompts"
        topic_changes = 0
        for name, template in templates.items():
            content = render(template, values, name)
            topic_changes += int(write_text(prompt_dir / name, content, dry_run))
        if topic_changes:
            print(f"SYNC    {topic.directory_name} ({topic_changes} files)")
            changes += topic_changes
        new_state[topic.key] = state_record(topic)

    state_payload = {"version": 1, "topics": new_state}
    state_text = json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n"
    changes += int(write_text(STATE_PATH, state_text, dry_run))
    return changes, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics-file", type=Path, default=SCRIPT_DIR / "topics.txt", help="Taxonomy file to synchronize (default: prompt/topics.txt)")
    parser.add_argument("--dry-run", action="store_true", help="Show changes and warnings without writing or deleting files")
    parser.add_argument("--refresh-locked-prompts", action="store_true", help="Explicitly update prompt files in HTML-locked topics without changing their HTML")
    args = parser.parse_args()
    try:
        changes, warnings = synchronize(args.topics_file.resolve(), args.dry_run, args.refresh_locked_prompts)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    mode = "Dry run" if args.dry_run else "Done"
    print(f"{mode}: {changes} change(s), {warnings} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
