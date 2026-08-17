#!/usr/bin/env python3
"""Render Speaking Pack HTML deterministically from versioned JSON content."""

from __future__ import annotations

import argparse
from collections import Counter
import html
import json
import re
import sys
import unicodedata
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEAKING_DIR = SCRIPT_DIR.parent
PACK_DIR = SPEAKING_DIR / "topics"
TEMPLATE_PATH = SCRIPT_DIR / "speaking-pack-template.html"
DATA_FILES = ("words.json", "ideas.json", "questions.json")
TOKEN_RE = re.compile(r"{{([A-Z][A-Z0-9_]*)}}")
MIN_CONTENT_SECTIONS = 8
MIN_HEADWORDS = 80
MIN_PHRASES = 80
MIN_IDEAS = 90
TOPIC_MINIMUMS = {
    "Weather, Seasons, and Climate in Daily Life": {
        "sections": 6,
        "headwords": 50,
        "phrases": 50,
        "ideas": 55,
    }
}
SUSPICIOUS_COLLOCATION_FRAMES = {
    "check the [headword]",
    "prepare for [headword]",
    "affected by [headword]",
    "a period of [headword]",
    "changes in [headword]",
    "deal with [headword]",
    "because of [headword]",
    "need to [headword]",
    "try to [headword]",
    "[headword] quickly",
    "[headword] safely",
    "[headword] when necessary",
    "[headword] in advance",
    "[headword] gradually",
}


def content_minimums(topic: str) -> dict[str, int]:
    """Return narrow-topic exceptions without weakening global pack standards."""
    return TOPIC_MINIMUMS.get(topic, {
        "sections": MIN_CONTENT_SECTIONS,
        "headwords": MIN_HEADWORDS,
        "phrases": MIN_PHRASES,
        "ideas": MIN_IDEAS,
    })


class DataError(ValueError):
    """A content file does not satisfy the renderer contract."""


def reject_dominant_count(counts: list[int], threshold: float, label: str, path: Path) -> None:
    """Reject quantities that strongly suggest fixed-size model templating."""
    if not counts:
        return
    count, frequency = Counter(counts).most_common(1)[0]
    share = frequency / len(counts)
    if share >= threshold:
        percentage = round(share * 100)
        raise DataError(
            f"{path}: mechanical quantity pattern detected: {frequency} of {len(counts)} "
            f"{label} ({percentage}%) contain exactly {count} items. Regenerate the affected "
            "content by judging each content unit independently; do not add filler or "
            "randomly delete useful material merely to vary the counts."
        )


def require(value: object, kind: type, location: str):
    if not isinstance(value, kind) or (kind in (str, list) and not value):
        raise DataError(f"{location} must be a non-empty {kind.__name__}")
    return value


def exact_keys(value: dict, required: set[str], optional: set[str], location: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise DataError(f"{location} is missing: {', '.join(sorted(missing))}")
    if extra:
        raise DataError(f"{location} has unknown fields: {', '.join(sorted(extra))}")


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise DataError(f"{path}: invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}") from error
    require(value, dict, str(path))
    if value.get("schema_version") != 1:
        raise DataError(f"{path}: schema_version must be 1")
    return value


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def unique_id(label: str, used: set[str]) -> str:
    base = slugify(label) or "section"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def validate_common(data: dict, path: Path) -> str:
    topic = require(data.get("topic"), str, f"{path}: topic")
    return topic


def render_phrase(phrase: dict, location: str) -> str:
    require(phrase, dict, location)
    exact_keys(phrase, {"text", "reusable_core"}, set(), location)
    text = require(phrase["text"], str, f"{location}.text")
    core = require(phrase["reusable_core"], str, f"{location}.reusable_core")
    if text.count(core) != 1:
        raise DataError(f"{location}.reusable_core must occur exactly once in text")
    before, after = text.split(core)
    return f"{esc(before)}<mark>{esc(core)}</mark>{esc(after)}"


def render_words(data: dict, path: Path, used_ids: set[str]) -> str:
    exact_keys(data, {"schema_version", "topic", "coverage_map", "sections"}, set(), str(path))
    topic = validate_common(data, path)
    minimums = content_minimums(topic)
    coverage = require(data["coverage_map"], list, f"{path}: coverage_map")
    for index, item in enumerate(coverage, 1):
        require(item, str, f"{path}: coverage_map[{index}]")
    sections = require(data["sections"], list, f"{path}: sections")
    if len(sections) < minimums["sections"]:
        raise DataError(f"{path}: sections must contain at least {minimums['sections']} thematic sections")
    headword_total = sum(len(section.get("headwords", [])) for section in sections if isinstance(section, dict))
    phrase_total = sum(len(section.get("phrases", [])) for section in sections if isinstance(section, dict))
    if headword_total < minimums["headwords"]:
        raise DataError(f"{path}: requires at least {minimums['headwords']} headwords; found {headword_total}")
    if phrase_total < minimums["phrases"]:
        raise DataError(f"{path}: requires at least {minimums['phrases']} phrases; found {phrase_total}")
    if len(sections) >= 6:
        reject_dominant_count(
            [len(section.get("headwords", [])) for section in sections if isinstance(section, dict)],
            0.60,
            "thematic sections",
            path,
        )
        reject_dominant_count(
            [len(section.get("phrases", [])) for section in sections if isinstance(section, dict)],
            0.60,
            "phrase banks",
            path,
        )
        paired_counts = [
            len(section.get("headwords", [])) == len(section.get("phrases", []))
            for section in sections
            if isinstance(section, dict)
        ]
        paired_share = sum(paired_counts) / len(paired_counts)
        if paired_share >= 0.75:
            raise DataError(
                f"{path}: mechanical paired quantity pattern detected: headword and phrase "
                f"counts are identical in {sum(paired_counts)} of {len(paired_counts)} sections "
                f"({round(paired_share * 100)}%). Regenerate phrase-bank depth independently "
                "from headword-card depth; do not add filler merely to alter the counts."
            )
    output: list[str] = []
    seen_forms: set[tuple[str, str]] = set()
    example_frames: Counter[str] = Counter()
    collocation_frames: Counter[str] = Counter()
    for si, section in enumerate(sections, 1):
        location = f"{path}: sections[{si}]"
        require(section, dict, location)
        exact_keys(section, {"title", "headwords", "phrases"}, set(), location)
        title = require(section["title"], str, f"{location}.title")
        headwords = require(section["headwords"], list, f"{location}.headwords")
        phrases = require(section["phrases"], list, f"{location}.phrases")
        section_id = unique_id(f"vocabulary-{title}", used_ids)
        output.append(f'<section class="vocab-chapter content-section"><div class="chapter-marker">Vocabulary chapter {si}</div><h3 id="{section_id}">{esc(title)}</h3><div class="vocab-grid">')
        for hi, item in enumerate(headwords, 1):
            item_location = f"{location}.headwords[{hi}]"
            require(item, dict, item_location)
            exact_keys(item, {"term", "part_of_speech", "definition", "examples", "collocations"}, set(), item_location)
            term = require(item["term"], str, f"{item_location}.term")
            part = require(item["part_of_speech"], str, f"{item_location}.part_of_speech")
            form_key = (term.casefold().strip(), part.casefold().strip())
            if form_key in seen_forms:
                raise DataError(f"{item_location}: duplicate headword and part of speech: {term!r} ({part})")
            seen_forms.add(form_key)
            definition = require(item["definition"], str, f"{item_location}.definition")
            examples = require(item["examples"], list, f"{item_location}.examples")
            if len(examples) != 2 or any(not isinstance(example, str) or not example for example in examples):
                raise DataError(f"{item_location}.examples must contain exactly two non-empty strings")
            for example in examples:
                frame = re.sub(re.escape(term), "[headword]", example, flags=re.IGNORECASE)
                frame = re.sub(r"\s+", " ", frame.casefold()).strip()
                example_frames[frame] += 1
            collocations = require(item["collocations"], list, f"{item_location}.collocations")
            if any(not isinstance(collocation, str) or not collocation for collocation in collocations):
                raise DataError(f"{item_location}.collocations must contain non-empty strings")
            for collocation in collocations:
                frame = re.sub(re.escape(term), "[headword]", collocation, flags=re.IGNORECASE)
                frame = re.sub(r"\s+", " ", frame.casefold()).strip()
                collocation_frames[frame] += 1
            chips = "".join(f'<a class="collocation-chip" href="#" data-collocation="{esc(c)}" target="_blank" rel="noopener noreferrer">{esc(c)}</a>' for c in collocations)
            output.append(f'<article class="vocab-card"><div class="vocab-card__header"><div><h4>{esc(term)}</h4><div class="part-of-speech">{esc(part)}</div></div><button class="pronounce-button" type="button" data-pronounce="{esc(term)}" aria-label="Pronounce {esc(term)}">Listen</button></div><p class="definition">{esc(definition)}</p><ol class="example-list"><li>{esc(examples[0])}</li><li>{esc(examples[1])}</li></ol><div class="chip-list">{chips}</div></article>')
        output.append('</div><div class="phrase-bank"><h4>Useful phrases, sentence parts, and free collocations</h4><ul>')
        for pi, phrase in enumerate(phrases, 1):
            output.append(f"<li>{render_phrase(phrase, f'{location}.phrases[{pi}]')}</li>")
        output.append("</ul></div></section>")
    collocation_counts = [
        len(item.get("collocations", []))
        for section in sections
        if isinstance(section, dict)
        for item in section.get("headwords", [])
        if isinstance(item, dict)
    ]
    if len(collocation_counts) >= 20:
        reject_dominant_count(collocation_counts, 0.75, "headwords", path)
    repeated_frames = [(frame, count) for frame, count in example_frames.items() if count >= 3]
    if repeated_frames:
        frame, count = max(repeated_frames, key=lambda item: item[1])
        raise DataError(
            f"{path}: substitution-template examples detected: one normalized sentence frame "
            f"occurs {count} times ({frame!r}). Rewrite examples independently with natural, "
            "headword-specific grammar and concrete contexts."
        )
    repeated_collocation_frames = [
        (frame, count)
        for frame, count in collocation_frames.items()
        if count >= 25 or (count >= 5 and frame in SUSPICIOUS_COLLOCATION_FRAMES)
    ]
    if repeated_collocation_frames:
        frame, count = max(repeated_collocation_frames, key=lambda item: item[1])
        raise DataError(
            f"{path}: substitution-template collocations detected: one normalized frame "
            f"occurs {count} times ({frame!r}). Select natural collocations independently "
            "for each headword; shared part of speech does not make a pattern idiomatic."
        )
    return "".join(output)


def render_ideas(data: dict, path: Path, used_ids: set[str]) -> str:
    exact_keys(data, {"schema_version", "topic", "sections", "coverage_audit", "added_categories"}, set(), str(path))
    topic = validate_common(data, path)
    minimums = content_minimums(topic)
    audit = require(data["coverage_audit"], list, f"{path}: coverage_audit")
    for ai, item in enumerate(audit, 1):
        location = f"{path}: coverage_audit[{ai}]"
        require(item, dict, location)
        exact_keys(item, {"section", "coverage"}, set(), location)
        require(item["section"], str, f"{location}.section")
        coverage = require(item["coverage"], list, f"{location}.coverage")
        if any(not isinstance(value, str) or not value for value in coverage):
            raise DataError(f"{location}.coverage must contain non-empty strings")
    if not isinstance(data["added_categories"], list):
        raise DataError(f"{path}: added_categories must be a list")
    if any(not isinstance(value, str) or not value for value in data["added_categories"]):
        raise DataError(f"{path}: added_categories must contain non-empty strings")
    sections = require(data["sections"], list, f"{path}: sections")
    if len(sections) < minimums["sections"]:
        raise DataError(f"{path}: sections must contain at least {minimums['sections']} thematic categories")
    idea_total = sum(len(section.get("ideas", [])) for section in sections if isinstance(section, dict))
    if idea_total < minimums["ideas"]:
        raise DataError(f"{path}: requires at least {minimums['ideas']} ideas; found {idea_total}")
    if len(sections) >= 6:
        reject_dominant_count(
            [len(section.get("ideas", [])) for section in sections if isinstance(section, dict)],
            0.60,
            "idea categories",
            path,
        )
    output: list[str] = []
    number = 0
    for si, section in enumerate(sections, 1):
        location = f"{path}: sections[{si}]"
        require(section, dict, location)
        exact_keys(section, {"title", "ideas"}, set(), location)
        title = require(section["title"], str, f"{location}.title")
        ideas = require(section["ideas"], list, f"{location}.ideas")
        section_id = unique_id(f"ideas-{title}", used_ids)
        output.append(f'<section class="content-section"><div class="chapter-marker">Idea category {si}</div><h3 id="{section_id}">{esc(title)}</h3><div class="idea-grid">')
        for ii, idea in enumerate(ideas, 1):
            item_location = f"{location}.ideas[{ii}]"
            require(idea, dict, item_location)
            exact_keys(idea, {"idea", "context"}, set(), item_location)
            heading = require(idea["idea"], str, f"{item_location}.idea")
            context = require(idea["context"], str, f"{item_location}.context")
            number += 1
            output.append(f'<article class="idea-card"><div class="editorial-label">Idea {number}</div><h4>{esc(heading)}</h4><details><summary>Use in context</summary><p>{esc(context)}</p></details></article>')
        output.append("</div></section>")
    return "".join(output)


def render_questions(data: dict, path: Path, used_ids: set[str]) -> str:
    exact_keys(data, {"schema_version", "topic", "sets", "corpus_calibration_audit"}, set(), str(path))
    validate_common(data, path)
    audit = require(data["corpus_calibration_audit"], list, f"{path}: corpus_calibration_audit")
    for ai, item in enumerate(audit, 1):
        location = f"{path}: corpus_calibration_audit[{ai}]"
        require(item, dict, location)
        exact_keys(item, {"set_title", "question_functions", "subtopics"}, set(), location)
        require(item["set_title"], str, f"{location}.set_title")
        functions = require(item["question_functions"], list, f"{location}.question_functions")
        if len(functions) != 4 or any(not isinstance(value, str) or not value for value in functions):
            raise DataError(f"{location}.question_functions must contain four non-empty strings")
        subtopics = require(item["subtopics"], list, f"{location}.subtopics")
        if any(not isinstance(value, str) or not value for value in subtopics):
            raise DataError(f"{location}.subtopics must contain non-empty strings")
    sets = require(data["sets"], list, f"{path}: sets")
    output: list[str] = []
    for si, interview in enumerate(sets, 1):
        location = f"{path}: sets[{si}]"
        require(interview, dict, location)
        exact_keys(interview, {"title", "setup", "questions"}, set(), location)
        title = require(interview["title"], str, f"{location}.title")
        setup = require(interview["setup"], str, f"{location}.setup")
        questions = require(interview["questions"], list, f"{location}.questions")
        if len(questions) != 4:
            raise DataError(f"{location}.questions must contain exactly four questions")
        section_id = unique_id(f"interview-{title}", used_ids)
        output.append(f'<section class="interview-set content-section"><div class="editorial-label">Interview set {si}</div><h3 id="{section_id}">{esc(title)}</h3><p class="interview-setup">{esc(setup)}</p><div class="question-list">')
        for qi, question in enumerate(questions, 1):
            item_location = f"{location}.questions[{qi}]"
            require(question, dict, item_location)
            exact_keys(question, {"number", "question", "sample_answer"}, set(), item_location)
            if type(question["number"]) is not int or question["number"] != qi:
                raise DataError(f"{item_location}.number must be {qi}")
            wording = require(question["question"], str, f"{item_location}.question")
            answer = require(question["sample_answer"], str, f"{item_location}.sample_answer")
            answer_words = re.findall(r"\b[\w’'-]+\b", answer)
            answer_sentences = [part for part in re.split(r"(?<=[.!?])\s+", answer) if part.strip()]
            sentence_lengths = [len(re.findall(r"\b[\w’'-]+\b", sentence)) for sentence in answer_sentences]
            if not 60 <= len(answer_words) <= 100:
                raise DataError(f"{item_location}.sample_answer must contain 60–100 spoken words; found {len(answer_words)}")
            if not 3 <= len(answer_sentences) <= 7:
                raise DataError(f"{item_location}.sample_answer must contain 3–7 spoken sentences; found {len(answer_sentences)}")
            if max(sentence_lengths) > 25:
                raise DataError(f"{item_location}.sample_answer has a sentence longer than 25 words; rewrite it for spoken delivery")
            if re.search(r"\b(?:However|Therefore|In conclusion|In principle),", answer):
                raise DataError(f"{item_location}.sample_answer uses essay-like transition language; rewrite it for spoken delivery")
            output.append(f'<article class="question-card"><p><span class="question-number">Q{qi}.</span> {esc(wording)}</p><details class="sample-answer"><summary>Sample 45-second answer</summary><div class="sample-answer__content"><p>{esc(answer)}</p></div></details></article>')
        output.append("</div></section>")
    return "".join(output)


def render_topic(topic_dir: Path, template: str, dry_run: bool) -> tuple[Path, bool]:
    paths = [topic_dir / name for name in DATA_FILES]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise DataError(f"{topic_dir}: missing {', '.join(missing)}")
    words, ideas, questions = (load_json(path) for path in paths)
    topic = validate_common(words, paths[0])
    for data, path in ((ideas, paths[1]), (questions, paths[2])):
        if validate_common(data, path) != topic:
            raise DataError(f"{path}: topic does not match {paths[0]}")
    if topic != topic_dir.name:
        raise DataError(f"{paths[0]}: topic must exactly match directory name {topic_dir.name!r}")
    slug = slugify(topic)
    used_ids: set[str] = set()
    replacements = {
        "TOPIC_TITLE": esc(topic),
        "TOPIC_SLUG": slug,
        "META_DESCRIPTION": esc(f"A TOEFL Speaking Interview topic pack about {topic.lower()}, with vocabulary, reusable ideas, interview questions, and sample answers."),
        "HERO_DESCRIPTION": esc(f"Build flexible language, ideas, and interview answers for speaking about {topic.lower()}."),
        "VOCABULARY_CONTENT": render_words(words, paths[0], used_ids),
        "IDEA_CONTENT": render_ideas(ideas, paths[1], used_ids),
        "QUESTION_CONTENT": render_questions(questions, paths[2], used_ids),
    }
    rendered = TOKEN_RE.sub(lambda match: replacements.get(match.group(1), match.group(0)), template)
    remaining = sorted(set(TOKEN_RE.findall(rendered)))
    if remaining:
        raise DataError(f"template has unreplaced tokens: {', '.join(remaining)}")
    existing_outputs = sorted(topic_dir.glob("*.html"))
    if len(existing_outputs) > 1:
        raise DataError(f"{topic_dir}: multiple top-level HTML files make the output target ambiguous")
    output_path = existing_outputs[0] if existing_outputs else topic_dir / f"{slug}-toefl-speaking-topic-pack.html"
    changed = not output_path.exists() or output_path.read_text(encoding="utf-8") != rendered
    if changed and not dry_run:
        temporary = output_path.with_name(f".{output_path.name}.tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(output_path)
    return output_path, changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topics", nargs="*", help="Topic directory names or paths (default: every topic with all three JSON files)")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing HTML")
    args = parser.parse_args()
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if args.topics:
        topic_dirs = [Path(value).resolve() if Path(value).is_absolute() else (PACK_DIR / value).resolve() for value in args.topics]
    else:
        topic_dirs = sorted({path.parent for name in DATA_FILES for path in PACK_DIR.glob(f"*/{name}") if all((path.parent / required).is_file() for required in DATA_FILES)})
    if not topic_dirs:
        print("No complete topic datasets found; nothing to render.")
        return 0
    errors = 0
    changes = 0
    for topic_dir in topic_dirs:
        if topic_dir.parent != PACK_DIR or not topic_dir.is_dir():
            print(f"ERROR: unsafe or missing topic directory: {topic_dir}", file=sys.stderr)
            errors += 1
            continue
        try:
            output, changed = render_topic(topic_dir, template, args.dry_run)
        except (OSError, DataError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            errors += 1
            continue
        status = "WOULD RENDER" if args.dry_run and changed else "RENDER" if changed else "CURRENT"
        print(f"{status:<12} {output.relative_to(PACK_DIR)}")
        changes += int(changed)
    print(f"{'Dry run' if args.dry_run else 'Done'}: {changes} change(s), {errors} error(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
