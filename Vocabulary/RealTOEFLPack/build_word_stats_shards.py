#!/usr/bin/env python3
"""
Build lazy-loadable word-stat shards from the three TOEFL CSV files.

Place this script beside:
    counts_new.csv
    counts_merged.csv
    counts_old.csv

Then run:
    python3 build_word_stats_shards.py

It creates:
    word_stats_shards/
        manifest.js
        shard_00.js
        ...
        shard_ff.js

The files are JavaScript rather than JSON so the app can load them both from
a website and from a local file:// page without relying on fetch() permissions.
Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable


DATASETS = (
    ("new", "New-format tests", "counts_new.csv"),
    ("merged", "Merged corpus", "counts_merged.csv"),
    ("old", "Old-format tests", "counts_old.csv"),
)

POS_COLUMNS = (
    ("noun", "Noun"),
    ("proper_noun", "Proper noun"),
    ("verb", "Verb"),
    ("auxiliary", "Auxiliary"),
    ("adjective", "Adjective"),
    ("adverb", "Adverb"),
    ("pronoun", "Pronoun"),
    ("other", "Other"),
)

REQUIRED_COLUMNS = {
    "lemma",
    "count",
    "observed_forms",
    *(name for name, _label in POS_COLUMNS),
}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        description="Preprocess TOEFL word-count CSVs into lazy-loadable shards."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=script_dir,
        help="Directory containing the three CSV files (default: script directory).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Output directory (default: INPUT_DIR/word_stats_shards). "
            "The directory is created automatically."
        ),
    )
    parser.add_argument(
        "--shards",
        type=int,
        default=256,
        help="Number of hash shards to create (default: 256).",
    )
    return parser.parse_args()


def normalize_token(value: str) -> str:
    """Match the normalization used by the browser app."""
    token = unicodedata.normalize("NFKC", value or "")
    token = token.replace("’", "'").replace("‘", "'")
    token = token.strip().lower()

    start = 0
    end = len(token)

    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1

    return token[start:end]


def fnv1a_32_utf8(value: str) -> int:
    """FNV-1a over UTF-8 bytes; mirrored exactly in the browser."""
    result = 0x811C9DC5
    for byte in value.encode("utf-8"):
        result ^= byte
        result = (result * 0x01000193) & 0xFFFFFFFF
    return result


def to_int(value: Any) -> int:
    try:
        return int(str(value or "0").strip())
    except (TypeError, ValueError):
        return 0


def parse_observed_forms(raw_value: str) -> list[list[Any]]:
    """
    Return compact [surface_form, count] pairs.

    The last '=' is used as the separator so an unusual form containing '='
    earlier in the text does not break parsing.
    """
    result: list[list[Any]] = []

    for item in str(raw_value or "").split(";"):
        item = item.strip()
        if not item:
            continue

        if "=" not in item:
            form = item
            count = 0
        else:
            form, raw_count = item.rsplit("=", 1)
            form = form.strip()
            count = to_int(raw_count)

        if normalize_token(form):
            result.append([form, count])

    return result


def compact_json(value: Any) -> str:
    # ASCII escaping makes the generated JavaScript safe for all browsers.
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=False,
    )


def write_js(path: Path, callback: str, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    source = (
        f'window.__KOOSHKY_TOEFL_WORD_STATS__.{callback}'
        f"({compact_json(payload)});\n"
    )
    temporary.write_text(source, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def validate_headers(path: Path, fieldnames: Iterable[str] | None) -> None:
    present = set(fieldnames or ())
    missing = sorted(REQUIRED_COLUMNS - present)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{path.name} is missing required columns: {joined}")


def build(input_dir: Path, output_dir: Path, shard_count: int) -> None:
    if shard_count < 1 or shard_count > 4096:
        raise ValueError("--shards must be between 1 and 4096.")

    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    build_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    hex_width = max(2, len(f"{shard_count - 1:x}"))

    # Each shard keeps a compact record array and a term -> [record, exact count]
    # index. A record is copied only to shards containing one of its search terms.
    shards: list[dict[str, Any]] = [
        {"records": [], "terms": {}, "record_lookup": {}}
        for _ in range(shard_count)
    ]

    dataset_manifest: list[dict[str, Any]] = []
    total_source_rows = 0

    for dataset_index, (key, label, filename) in enumerate(DATASETS):
        csv_path = input_dir / filename
        if not csv_path.is_file():
            raise FileNotFoundError(
                f"Required file not found: {csv_path}\n"
                "Place this script beside all three CSV files or use --input-dir."
            )

        source_rows = 0

        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            validate_headers(csv_path, reader.fieldnames)

            for source_row_number, row in enumerate(reader, start=2):
                lemma = str(row.get("lemma") or "").strip()
                normalized_lemma = normalize_token(lemma)
                if not normalized_lemma:
                    continue

                observed_forms = parse_observed_forms(row.get("observed_forms", ""))
                pos_counts = [to_int(row.get(column)) for column, _ in POS_COLUMNS]
                total_count = to_int(row.get("count"))

                # Compact record schema:
                # [dataset index, lemma, total count, observed forms, POS counts]
                compact_record = [
                    dataset_index,
                    lemma,
                    total_count,
                    observed_forms,
                    pos_counts,
                ]

                # One normalized term can appear through several raw spellings.
                exact_counts: dict[str, int] = {}
                for surface_form, count in observed_forms:
                    normalized_form = normalize_token(str(surface_form))
                    if normalized_form:
                        exact_counts[normalized_form] = (
                            exact_counts.get(normalized_form, 0) + to_int(count)
                        )

                # A lemma must always be searchable, even if it is not explicitly
                # listed among observed forms.
                exact_counts.setdefault(normalized_lemma, 0)

                record_identity = (dataset_index, source_row_number)

                for term, exact_count in exact_counts.items():
                    bucket = fnv1a_32_utf8(term) % shard_count
                    shard = shards[bucket]
                    record_lookup: dict[tuple[int, int], int] = shard["record_lookup"]

                    record_index = record_lookup.get(record_identity)
                    if record_index is None:
                        record_index = len(shard["records"])
                        record_lookup[record_identity] = record_index
                        shard["records"].append(compact_record)

                    term_entries = shard["terms"].setdefault(term, [])
                    term_entries.append([record_index, exact_count])

                source_rows += 1

        total_source_rows += source_rows
        dataset_manifest.append(
            {
                "key": key,
                "label": label,
                "source": filename,
                "rows": source_rows,
            }
        )
        print(f"Read {source_rows:,} rows from {filename}")

    # Remove only files generated by earlier runs of this builder.
    for stale_file in output_dir.glob("shard_*.js"):
        stale_file.unlink()
    manifest_path = output_dir / "manifest.js"
    if manifest_path.exists():
        manifest_path.unlink()

    total_terms = 0
    total_shard_records = 0
    total_output_bytes = 0

    for bucket, shard in enumerate(shards):
        shard_id = f"{bucket:0{hex_width}x}"
        records = shard["records"]
        terms = shard["terms"]

        # Stable term ordering improves reproducibility and compression.
        ordered_terms = {term: terms[term] for term in sorted(terms)}

        payload = {
            "v": 1,
            "b": build_id,
            "id": shard_id,
            "r": records,
            "t": ordered_terms,
        }

        shard_path = output_dir / f"shard_{shard_id}.js"
        write_js(shard_path, "registerShard", payload)
        total_output_bytes += shard_path.stat().st_size
        total_terms += len(ordered_terms)
        total_shard_records += len(records)

    manifest = {
        "v": 1,
        "build_id": build_id,
        "generated_at": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "shard_count": shard_count,
        "shard_hex_width": hex_width,
        "shard_prefix": "shard_",
        "shard_suffix": ".js",
        "datasets": dataset_manifest,
        "pos_columns": [
            {"key": key, "label": label} for key, label in POS_COLUMNS
        ],
        "source_rows": total_source_rows,
        "indexed_terms": total_terms,
        "shard_record_copies": total_shard_records,
    }

    write_js(manifest_path, "registerManifest", manifest)
    total_output_bytes += manifest_path.stat().st_size

    print()
    print(f"Created {shard_count:,} shards in: {output_dir}")
    print(f"Indexed terms across shards: {total_terms:,}")
    print(f"Total generated size: {total_output_bytes / (1024 * 1024):.2f} MiB")
    print(f"Build ID: {build_id}")


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir.expanduser()
    output_dir = (
        args.output_dir.expanduser()
        if args.output_dir is not None
        else input_dir / "word_stats_shards"
    )

    try:
        build(input_dir, output_dir, args.shards)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
