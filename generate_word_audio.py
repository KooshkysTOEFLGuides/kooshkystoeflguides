#!/usr/bin/env python3
"""
Generate one pronunciation MP3 per unique Word of the Day filename.

Put this script directly inside the WordOfTheDay directory and run:

    pip install edge-tts
    python generate_word_audio.py

For a file such as:
    meticulous-extended.html
    implication_extended.html
    imply.html

the generated files are:
    audios/meticulous.mp3
    audios/implication.mp3
    audios/imply.mp3

Existing non-empty MP3 files are skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

import edge_tts


DEFAULT_VOICE = "en-US-AriaNeural"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate pronunciation audio for Word of the Day HTML files."
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Edge TTS voice. Default: {DEFAULT_VOICE}",
    )
    parser.add_argument(
        "--rate",
        default="-5%",
        help='Speaking rate, such as "-5%%" or "+0%%". Default: -5%%',
    )
    parser.add_argument(
        "--volume",
        default="+0%",
        help='Volume adjustment. Default: +0%%',
    )
    parser.add_argument(
        "--pitch",
        default="+0Hz",
        help='Pitch adjustment. Default: +0Hz',
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate files even when a non-empty MP3 already exists.",
    )
    return parser.parse_args()


def word_from_filename(path: Path) -> str:
    """
    Take everything before the first hyphen, underscore, or dot.

    Examples:
      foster-extended.html      -> foster
      implication_extended.html -> implication
      imply.html                 -> imply
    """
    first_part = re.split(r"[-_.]", path.name, maxsplit=1)[0]
    return first_part.strip().lower()


def collect_words(directory: Path) -> list[str]:
    words: dict[str, str] = {}

    for html_path in sorted(directory.glob("*.html")):
        word = word_from_filename(html_path)

        if not word:
            print(f"Skipping filename with no usable word: {html_path.name}")
            continue

        # Several HTML files may begin with the same word.
        words.setdefault(word.casefold(), word)

    return sorted(words.values(), key=str.casefold)


async def generate_one(
    word: str,
    output_path: Path,
    *,
    voice: str,
    rate: str,
    volume: str,
    pitch: str,
) -> None:
    temporary_path = output_path.with_suffix(".mp3.part")

    try:
        communicate = edge_tts.Communicate(
            text=word,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )
        await communicate.save(str(temporary_path))

        if not temporary_path.exists() or temporary_path.stat().st_size == 0:
            raise RuntimeError("Edge TTS produced an empty file.")

        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


async def main_async() -> int:
    args = parse_args()
    directory = Path(__file__).resolve().parent
    audio_directory = directory / "audios"
    audio_directory.mkdir(parents=True, exist_ok=True)

    words = collect_words(directory)

    if not words:
        print(f"No HTML files found in {directory}")
        return 0

    generated = 0
    skipped = 0
    failed = 0

    for word in words:
        output_path = audio_directory / f"{word}.mp3"

        if (
            not args.force
            and output_path.exists()
            and output_path.stat().st_size > 0
        ):
            print(f"SKIP  {output_path.name}")
            skipped += 1
            continue

        print(f"MAKE  {output_path.name}")

        try:
            await generate_one(
                word,
                output_path,
                voice=args.voice,
                rate=args.rate,
                volume=args.volume,
                pitch=args.pitch,
            )
            generated += 1
        except Exception as exc:
            failed += 1
            print(
                f"ERROR {word}: {exc}",
                file=sys.stderr,
            )

    print()
    print(
        f"Done: {generated} generated, "
        f"{skipped} skipped, {failed} failed."
    )

    return 1 if failed else 0


def main() -> int:
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
