#!/usr/bin/env python3
"""
Generate separate MP3 files for TOEFL Listen and Repeat sets using edge-tts.

Accepted input forms
--------------------
1. A plain JSON array:
   [
     { ... },
     { ... }
   ]

2. A JavaScript variable containing a JSON-compatible array:
   const listenAndRepeatSets = [
     { ... },
     { ... }
   ];

3. export default [...], module.exports = [...], or a single object.

The generated object format should use double-quoted keys and strings. Strict
JSON-compatible JavaScript works without any extra parser. If the file uses
single quotes, comments, unquoted keys, or trailing commas, install json5:

    pip install json5

Required package
----------------
    pip install edge-tts

Typical usage
-------------
    python generate_listen_repeat_audio.py listen_repeat_sets.js

    python generate_listen_repeat_audio.py listen_repeat_sets.js \
        --output-dir listen_repeat_audio \
        --voice en-US-AriaNeural \
        --rate=-5%

Useful options
--------------
    --include-situation   Also generate 00_situation.mp3 for every set.
    --overwrite           Regenerate MP3 files that already exist.
    --dry-run             Validate input and show planned output without TTS.
    --allow-invalid       Continue despite word-count/progression validation errors.
    --concurrency 3       Number of simultaneous TTS requests.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_VOICE = "en-US-AriaNeural"
DEFAULT_RATE = "+0%"
DEFAULT_VOLUME = "+0%"
DEFAULT_PITCH = "+0Hz"

WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'’][A-Za-z0-9]+)*")


@dataclass(frozen=True)
class AudioJob:
    set_index: int
    set_id: str
    set_name: str
    kind: str
    sentence_number: int | None
    text: str
    output_path: Path


def count_words(text: str) -> int:
    """Count contractions and hyphenated compounds as one word."""
    return len(WORD_RE.findall(text))


def slugify(value: str, max_length: int = 70) -> str:
    """Create a readable, cross-platform filename component."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_text).strip("_").lower()
    slug = re.sub(r"_+", "_", slug)
    return (slug[:max_length].rstrip("_") or "untitled")


def remove_javascript_wrapper(source: str) -> str:
    """Remove common JavaScript assignments while preserving the array/object."""
    text = source.lstrip("\ufeff").strip()

    wrapper_patterns = [
        r"^\s*export\s+default\s+",
        r"^\s*export\s+(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*",
        r"^\s*(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*",
        r"^\s*module\.exports\s*=\s*",
        r"^\s*window\.[A-Za-z_$][\w$]*\s*=\s*",
    ]

    for pattern in wrapper_patterns:
        updated = re.sub(pattern, "", text, count=1, flags=re.DOTALL)
        if updated != text:
            text = updated.strip()
            break

    if text.endswith(";"):
        text = text[:-1].rstrip()

    return text


def load_input_file(path: Path) -> list[dict[str, Any]]:
    """Load strict JSON-compatible JavaScript, with optional JSON5 fallback."""
    source = path.read_text(encoding="utf-8-sig")
    payload = remove_javascript_wrapper(source)

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as strict_error:
        try:
            import json5  # type: ignore
        except ImportError as exc:
            raise ValueError(
                f"Could not parse {path.name} as strict JSON-compatible JavaScript.\n"
                f"Original parser error: {strict_error}\n\n"
                "Keep keys and strings in double quotes and remove comments/trailing "
                "commas, or install the optional parser with:\n"
                "    pip install json5"
            ) from exc

        try:
            data = json5.loads(payload)
        except Exception as json5_error:
            raise ValueError(
                f"Could not parse {path.name} as JavaScript/JSON5: {json5_error}"
            ) from json5_error

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        raise ValueError("The input must contain one object or a list of objects.")

    if not data:
        raise ValueError("The input list is empty.")

    if not all(isinstance(item, dict) for item in data):
        raise ValueError("Every item in the input list must be an object.")

    return data


def require_nonempty_string(
    item: dict[str, Any],
    field_name: str,
    set_number: int,
) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Set {set_number}: '{field_name}' must be a nonempty string."
        )
    return value.strip()


def validate_sets(
    raw_sets: list[dict[str, Any]],
    allow_invalid: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate schema and TOEFL length progression before generating audio."""
    normalized_sets: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    for set_index, item in enumerate(raw_sets, start=1):
        try:
            set_id = require_nonempty_string(item, "setId", set_index)
            set_name = require_nonempty_string(item, "setName", set_index)
            set_type = require_nonempty_string(item, "setType", set_index).upper()
            situation = require_nonempty_string(item, "situation", set_index)
            speaker_role = require_nonempty_string(item, "speakerRole", set_index)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if set_type not in {"ORIENTATION", "PROCEDURE"}:
            errors.append(
                f"Set {set_index} ({set_name}): 'setType' must be "
                "'ORIENTATION' or 'PROCEDURE'."
            )

        sentences = item.get("sentences")
        if not isinstance(sentences, list):
            errors.append(
                f"Set {set_index} ({set_name}): 'sentences' must be a list."
            )
            continue

        if len(sentences) != 7:
            errors.append(
                f"Set {set_index} ({set_name}): exactly 7 sentences are required; "
                f"found {len(sentences)}."
            )
            continue

        normalized_sentences: list[dict[str, Any]] = []
        actual_counts: list[int] = []

        for expected_number, sentence in enumerate(sentences, start=1):
            if not isinstance(sentence, dict):
                errors.append(
                    f"Set {set_index} ({set_name}), sentence {expected_number}: "
                    "each sentence must be an object."
                )
                continue

            sentence_number = sentence.get("sentenceNumber")
            if sentence_number != expected_number:
                errors.append(
                    f"Set {set_index} ({set_name}): sentence position "
                    f"{expected_number} must have sentenceNumber {expected_number}."
                )

            text = sentence.get("text")
            if not isinstance(text, str) or not text.strip():
                errors.append(
                    f"Set {set_index} ({set_name}), sentence {expected_number}: "
                    "'text' must be a nonempty string."
                )
                continue
            text = text.strip()

            actual_count = count_words(text)
            supplied_count = sentence.get("wordCount")
            if not isinstance(supplied_count, int):
                errors.append(
                    f"Set {set_index} ({set_name}), sentence {expected_number}: "
                    "'wordCount' must be an integer."
                )
            elif supplied_count != actual_count:
                errors.append(
                    f"Set {set_index} ({set_name}), sentence {expected_number}: "
                    f"wordCount says {supplied_count}, but the script counts "
                    f"{actual_count}: {text}"
                )

            if "?" in text:
                errors.append(
                    f"Set {set_index} ({set_name}), sentence {expected_number}: "
                    "repeatable sentences must not be questions."
                )

            actual_counts.append(actual_count)
            normalized_sentences.append(
                {
                    "sentenceNumber": expected_number,
                    "text": text,
                    "wordCount": actual_count,
                }
            )

        if len(normalized_sentences) != 7:
            continue

        if any(
            current <= previous
            for previous, current in zip(actual_counts, actual_counts[1:])
        ):
            errors.append(
                f"Set {set_index} ({set_name}): word counts must rise strictly; "
                f"found {' -> '.join(map(str, actual_counts))}."
            )

        total_words = sum(actual_counts)
        if not 64 <= total_words <= 74:
            warnings.append(
                f"Set {set_index} ({set_name}): total length is {total_words} words; "
                "the preferred range is 64-74."
            )

        normalized_sets.append(
            {
                "setId": set_id,
                "setName": set_name,
                "setType": set_type,
                "situation": situation,
                "speakerRole": speaker_role,
                "sentences": normalized_sentences,
                "qualityAudit": item.get("qualityAudit"),
            }
        )

    if errors and not allow_invalid:
        formatted = "\n".join(f"- {message}" for message in errors)
        raise ValueError(
            "Input validation failed. No audio was generated:\n" + formatted
        )

    if errors and allow_invalid:
        warnings.extend("INVALID BUT ALLOWED: " + message for message in errors)

    return normalized_sets, warnings


def sentence_filename(sentence_number: int, text: str) -> str:
    readable_text = slugify(text, max_length=64)
    return f"{sentence_number:02d}_{readable_text}.mp3"


def build_jobs(
    sets: list[dict[str, Any]],
    output_dir: Path,
    include_situation: bool,
) -> tuple[list[AudioJob], list[dict[str, Any]]]:
    jobs: list[AudioJob] = []
    manifest_sets: list[dict[str, Any]] = []

    for set_index, item in enumerate(sets, start=1):
        set_name = item["setName"]
        set_id = item["setId"]
        folder_name = f"{set_index:03d}_{slugify(set_name, max_length=60)}"
        set_dir = output_dir / folder_name

        manifest_entry: dict[str, Any] = {
            "setIndex": set_index,
            "setId": set_id,
            "setName": set_name,
            "setType": item["setType"],
            "speakerRole": item["speakerRole"],
            "folder": folder_name,
            "situationAudio": None,
            "sentenceAudio": [],
        }

        if include_situation:
            situation_path = set_dir / "00_situation.mp3"
            jobs.append(
                AudioJob(
                    set_index=set_index,
                    set_id=set_id,
                    set_name=set_name,
                    kind="situation",
                    sentence_number=None,
                    text=item["situation"],
                    output_path=situation_path,
                )
            )
            manifest_entry["situationAudio"] = (
                situation_path.relative_to(output_dir).as_posix()
            )

        for sentence in item["sentences"]:
            number = sentence["sentenceNumber"]
            audio_path = set_dir / sentence_filename(number, sentence["text"])
            jobs.append(
                AudioJob(
                    set_index=set_index,
                    set_id=set_id,
                    set_name=set_name,
                    kind="sentence",
                    sentence_number=number,
                    text=sentence["text"],
                    output_path=audio_path,
                )
            )
            manifest_entry["sentenceAudio"].append(
                {
                    "sentenceNumber": number,
                    "text": sentence["text"],
                    "wordCount": sentence["wordCount"],
                    "audioFile": audio_path.relative_to(output_dir).as_posix(),
                }
            )

        manifest_sets.append(manifest_entry)

    return jobs, manifest_sets


async def synthesize_job(
    job: AudioJob,
    *,
    edge_tts_module: Any,
    voice: str,
    rate: str,
    volume: str,
    pitch: str,
    overwrite: bool,
    retries: int,
    semaphore: asyncio.Semaphore,
) -> tuple[AudioJob, str, str | None]:
    path = job.output_path

    if path.exists() and path.stat().st_size > 0 and not overwrite:
        return job, "skipped", None

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".part")

    async with semaphore:
        for attempt in range(1, retries + 1):
            try:
                if temporary_path.exists():
                    temporary_path.unlink()

                communicator = edge_tts_module.Communicate(
                    job.text,
                    voice=voice,
                    rate=rate,
                    volume=volume,
                    pitch=pitch,
                )
                await communicator.save(str(temporary_path))

                if not temporary_path.exists() or temporary_path.stat().st_size == 0:
                    raise RuntimeError("The service returned an empty audio file.")

                temporary_path.replace(path)
                return job, "created", None

            except Exception as exc:  # Network/service errors vary by version.
                if temporary_path.exists():
                    temporary_path.unlink()

                if attempt >= retries:
                    return job, "failed", str(exc)

                await asyncio.sleep(min(2 ** (attempt - 1), 8))

    return job, "failed", "Unknown generation error."


async def generate_audio(
    jobs: list[AudioJob],
    *,
    voice: str,
    rate: str,
    volume: str,
    pitch: str,
    overwrite: bool,
    retries: int,
    concurrency: int,
) -> list[tuple[AudioJob, str, str | None]]:
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError(
            "edge-tts is not installed. Install it with:\n"
            "    pip install edge-tts"
        ) from exc

    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        synthesize_job(
            job,
            edge_tts_module=edge_tts,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
            overwrite=overwrite,
            retries=retries,
            semaphore=semaphore,
        )
        for job in jobs
    ]

    results: list[tuple[AudioJob, str, str | None]] = []
    for completed in asyncio.as_completed(tasks):
        result = await completed
        results.append(result)
        job, status, error = result
        label = (
            f"sentence {job.sentence_number}"
            if job.sentence_number is not None
            else "situation"
        )
        if status == "failed":
            print(f"[FAILED] {job.set_name} - {label}: {error}", file=sys.stderr)
        else:
            print(f"[{status.upper()}] {job.set_name} - {label}")

    return results


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one MP3 per TOEFL Listen and Repeat sentence from a "
            "JavaScript/JSON list of set objects."
        )
    )
    parser.add_argument("input_file", type=Path, help="Input .js or .json file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("listen_repeat_audio"),
        help="Output directory (default: listen_repeat_audio).",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Edge-TTS voice (default: {DEFAULT_VOICE}).",
    )
    parser.add_argument(
        "--rate",
        default=DEFAULT_RATE,
        help="Speech rate, such as +0%% or -5%%. Use --rate=-5%% for negatives.",
    )
    parser.add_argument(
        "--volume",
        default=DEFAULT_VOLUME,
        help="Speech volume, such as +0%% or -10%%.",
    )
    parser.add_argument(
        "--pitch",
        default=DEFAULT_PITCH,
        help="Speech pitch, such as +0Hz or -5Hz.",
    )
    parser.add_argument(
        "--include-situation",
        action="store_true",
        help="Also generate a situation/setup MP3 for each set.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate files that already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and display planned files without generating audio.",
    )
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="Continue despite sentence-count or progression validation errors.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Simultaneous TTS requests (default: 3).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Attempts per failed audio file (default: 3).",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1.")
    if args.retries < 1:
        parser.error("--retries must be at least 1.")
    if not args.input_file.is_file():
        parser.error(f"Input file not found: {args.input_file}")

    try:
        raw_sets = load_input_file(args.input_file)
        sets, warnings = validate_sets(raw_sets, args.allow_invalid)
        jobs, manifest_sets = build_jobs(
            sets,
            args.output_dir,
            args.include_situation,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    print(
        f"Validated {len(sets)} set(s), containing "
        f"{sum(len(item['sentences']) for item in sets)} repeatable sentences."
    )
    print(f"Planned audio files: {len(jobs)}")
    print(f"Voice: {args.voice} | Rate: {args.rate}")

    if args.dry_run:
        for job in jobs:
            print(f"  {job.output_path.as_posix()}  <-  {job.text}")
        print("Dry run complete; no audio was generated.")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        results = asyncio.run(
            generate_audio(
                jobs,
                voice=args.voice,
                rate=args.rate,
                volume=args.volume,
                pitch=args.pitch,
                overwrite=args.overwrite,
                retries=args.retries,
                concurrency=args.concurrency,
            )
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    created = sum(status == "created" for _, status, _ in results)
    skipped = sum(status == "skipped" for _, status, _ in results)
    failed_results = [
        (job, error)
        for job, status, error in results
        if status == "failed"
    ]

    manifest = {
        "sourceFile": str(args.input_file),
        "voice": args.voice,
        "rate": args.rate,
        "volume": args.volume,
        "pitch": args.pitch,
        "includeSituation": args.include_situation,
        "sets": manifest_sets,
    }
    manifest_path = args.output_dir / "audio_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"Created: {created}")
    print(f"Skipped existing: {skipped}")
    print(f"Failed: {len(failed_results)}")
    print(f"Manifest: {manifest_path}")

    if failed_results:
        failure_log = args.output_dir / "failed_audio.txt"
        failure_log.write_text(
            "\n".join(
                f"{job.output_path}\t{error or 'Unknown error'}"
                for job, error in failed_results
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Failure log: {failure_log}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
