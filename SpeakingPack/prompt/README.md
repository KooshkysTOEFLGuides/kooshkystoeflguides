# Speaking topic-pack prompt pipeline

`topics.txt` is the source of truth for topic numbers, titles, and seed subtopics.
Run the scaffolder from the repository root:

```bash
python3 SpeakingPack/prompt/generate_topic_prompts.py
```

Preview its work without changing files:

```bash
python3 SpeakingPack/prompt/generate_topic_prompts.py --dry-run
```

An intentional pipeline-format migration can refresh prompts in locked topics without touching their HTML:

```bash
python3 SpeakingPack/prompt/generate_topic_prompts.py --refresh-locked-prompts
```

For every unlocked topic, the script creates or synchronizes:

```text
SpeakingPack/topics/<Topic>/prompts/
├── words.txt
├── ideas.txt
└── questions.txt
```

Use the files in that order:

1. Run `words.txt`; save its exact JSON response as `SpeakingPack/topics/<Topic>/words.json`.
2. Supply `words.json` with `ideas.txt`; save its response as `SpeakingPack/topics/<Topic>/ideas.json`.
3. Supply both JSON files to `questions.txt`; it uses the shared real TOEFL Speaking corpus at `SpeakingPack/prompt/references/real-toefl-speaking-corpus.txt`. Save its response as `SpeakingPack/topics/<Topic>/questions.json`.
4. Render the page deterministically—no model or HTML prompt is involved:

```bash
# Render every topic that has all three JSON files
python3 SpeakingPack/prompt/render_topic_packs.py

# Validate and preview without writing
python3 SpeakingPack/prompt/render_topic_packs.py --dry-run

# Render one or more named topics
python3 SpeakingPack/prompt/render_topic_packs.py "Travel and Tourism"
```

The prompts strongly prefer 100+ headwords, 100+ reusable phrases, and 100+ ideas, with more for broad topics, but explicitly forbid padding to meet those targets. The renderer enforces only anti-thinness floors: 8 vocabulary sections, 80 headwords, 80 phrases, 8 idea categories, and 90 ideas. It also rejects mechanical quantity patterns when one headword, phrase-bank, or idea-category size dominates at least 60% of its sections, one collocation count dominates at least 75% of headwords, or headword and phrase totals are paired identically in at least 75% of sections. The resulting error asks for content-based regeneration rather than random count changes. Additional validation covers schema version 1, required fields, the topic name, two examples per headword, reusable phrase cores, and exactly four numbered questions per interview. It HTML-escapes all educational content and writes atomically. A new topic receives `<topic-slug>-toefl-speaking-topic-pack.html`; a topic with one historical top-level HTML file retains that filename. Multiple HTML files are treated as an ambiguity and are not touched. Missing, thin, mechanical, or invalid data never overwrites an existing page.

`Weather, Seasons, and Climate in Daily Life` is an intentional narrow-topic exception. Its filled prompts target roughly 55–75 headwords, 55–80 chunks, and 55–75 ideas, and the renderer applies floors of 6 sections, 50 headwords, 50 chunks, and 55 ideas only to that exact topic name. Do not generalize this exception or inflate Weather with marginal terminology and repeated answer angles.

Because every page is rebuilt from the shared `speaking-pack-template.html`, editing that template and rerunning the renderer updates all complete packs consistently.

## Local voice-practice library

Rendered packs load the shared `speaking-recorder.js` module. It adds 45-second microphone practice to every interview question and stores browser-compressed audio `Blob`s, metadata, and optional live transcripts in one origin-wide IndexedDB database. The browser chooses its native recording format, and each take is saved as one complete media blob. This means recordings from all topic packs share a library and appear under their original questions.

The interface reports estimated browser-storage use, requests persistent storage only after a user action, handles quota failures without deleting earlier takes, supports individual audio/transcript downloads, and exports or restores the whole library as a human-readable uncompressed ZIP. Imported recording IDs are deduplicated. Clearing the library requires two confirmations.

Microphone access and browser speech recognition depend on browser support and a secure context (`https:` or a local development origin). The Web Speech API cannot transcribe an existing audio file, so the user must enable **Create a transcript while I record** before starting a take. Transcripts remain editable afterward. Browser storage can still be cleared by the user or browser, so the page explicitly treats ZIP downloads as the durable backup.

The 45-second timer begins only after microphone permission, input setup, and the starting beep. At cutoff, audio capture stops immediately while transcript saving waits briefly for the recognition service's final buffered result; a timeout prevents a stalled recognition service from blocking the saved take.

## Reentrant synchronization and HTML locks

Topic numbers are stable identities. Rerunning the script applies title and subtopic edits, creates additions, renames changed topic directories, and removes managed topics deleted from `topics.txt`.

A topic directory becomes locked when it contains a top-level `.html` file. A locked directory is never renamed, regenerated, or removed by the script. If its taxonomy changes, the script prints a warning and keeps the directory untouched. Remove or relocate that generated HTML file explicitly, then rerun the script to authorize the pending change.

The shared HTML template in `SpeakingPack/prompt/` is not a generated pack and does not lock any topic. The obsolete per-topic `html.txt` assembly prompts are removed automatically.

Existing locked topics retain their historical prompt set until their generated HTML is removed; this is intentional protection, not a synchronization failure.

The script records only its managed topic mapping in `.topic-scaffolder-state.json`. Do not edit that file by hand.
