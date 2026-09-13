short form: put the json in jsons/ then
$ python wotd_generator.py --input jsons --output-dir generated
$ python generate_pronunciation_audio.py --directory generated



## Queue new words for an agent

Use `word-queue.txt` when the words are known but their publication dates have not
been assigned. Enter exactly one headword per nonblank line, in the desired order:

```text
first word
second word
third word
```

Do not add dates, bullets, numbering, comments, or status labels. Blank lines are
ignored. New words should normally be appended at the bottom.

When asked to process the queue, an agent must:

1. Read this file, `README-ARCHIVE.md`, the JSON prompt and contract files, and the active generator code.
2. Process the requested number of words from the top without reordering them.
3. Find the latest valid ISO date in `word-data.js`. Assign its following calendar day to the first queued word, then continue one day at a time. The JSON uses a human-readable date such as `September 15th 2026`; the registry uses `2026-09-15`.
4. Create and validate `jsons/{slug}.json`, then generate `{slug}-extended.html`, `{slug}-extended.tex`, and `{slug}-telegram.txt` in `generated/`.
5. Generate and verify every required pronunciation MP3. Because the audio script scans a whole directory, use an isolated temporary staging directory or clean up any unrelated MP3s it creates.
6. Render the top of the finished HTML page with a local headless browser at a 1200 × 630 viewport. Save the code-rendered screenshot as `banners/{slug}-banner.png`; do not use AI image generation.
7. Add the scheduled entry to `word-data.js`, increment its cache-busting query consistently in every HTML consumer, and verify the archive link and publication date.
8. Remove a word's line from `word-queue.txt` only after all of its files and checks succeed. On any failure, keep that line and all later lines so the next session can resume safely.

The queue is intentionally consumed. Completed words remain recorded in the JSON
files, generated outputs, and `word-data.js`; the queue contains only pending work.

The `banners/` directory sits beside `generated/` and contains one 1200 × 630 PNG
per completed queued word. Each image is a browser screenshot of the page's top
section, so it stays visually consistent with the generated HTML and CSS.

# Kooshky TOEFL Word of the Day: JSON + Local Audio Pipeline

This package separates lexical content, page generation, and pronunciation-audio generation.

GPT returns only:

1. a ready-to-post Telegram message; and
2. one strict plain-text JSON object.

The local tools then create:

- a standalone responsive HTML file with CSS and JavaScript inlined;
- a simple LaTeX source file containing the same learning content;
- a Telegram `.txt` file; and
- local pronunciation MP3 files in an `audios/` folder.

**No PDF files are generated.** The HTML contains no print-to-PDF control, and the Python generator never runs LaTeX or any PDF compiler.

## Pronunciation design

Every generated HTML page has a pronunciation button at the top.

- For an ordinary word, the spoken text is the headword itself, such as `allocate`. The file becomes `audios/allocate.mp3`.
- For a word whose pronunciation changes, each meaning supplies a short contextual phrase. For example:
  - noun: `a record` → `audios/a-record.mp3`
  - verb: `to record` → `audios/to-record.mp3`

The page highlights pronunciation changes near the top and repeats the correct IPA and sound button inside every meaning.

Each pronunciation control is a normal link to the local MP3, so it still points to a usable file when enhancement JavaScript is unavailable. When JavaScript runs, it plays the MP3 inline. If the MP3 cannot be loaded, the page automatically uses the browser’s American-English speech synthesis as a fallback.

## Folder map

```text
kooshky_wotd_json_pipeline_v1_3/
├── wotd_generator.py
├── generate_pronunciation_audio.py
├── wotd_audio.py
├── requirements.txt
├── word-of-the-day-json-prompt.txt
├── telegram-template.txt
├── templates/
│   ├── word-page.html.j2
│   ├── word-style.css
│   ├── word-ui.js
│   └── telegram-post.txt.j2
├── resources/
│   ├── word-data-template.json
│   ├── optional-fields-reference.json
│   └── wotd.schema.json
├── examples/
│   ├── minimal-allocate.json
│   ├── notion.json
│   └── record.json
└── generated/
```

## 1. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

Edge-TTS needs an internet connection only while it creates MP3 files. Afterward, the HTML and audio are local and can be distributed together.

## Telegram channel automation

`publish_telegram.py` publishes the banner and generated Telegram text for the
entry whose ISO date matches the requested date. The banner caption is `full
explanation: URL`, with the public page URL derived from the repository's `CNAME`
and the entry's root-relative registry path. Without `--date`, the script uses the
current date in `Asia/Tehran`. It validates all required files before posting and
records each successful stage in `telegram-posted.json`, allowing a failed run to
resume without repeating a completed photo post. GitHub Actions restores and saves
this ledger through its cache, so the workflow needs only read access to repository
contents and does not create automated commits.

The workflow `.github/workflows/publish-word-of-the-day.yml` runs daily at 06:30
UTC, which is 10:00 in Tehran. It requires these GitHub Actions repository secrets:

- `TELEGRAM_BOT_TOKEN`: token for a dedicated bot created through BotFather
- `TELEGRAM_CHANNEL_ID`: the target channel username, such as `@KooshkyTOEFL`

The bot must be a channel administrator with permission to post messages. The
scheduled workflow posts live. A manually dispatched workflow defaults to dry-run
mode and accepts an optional `YYYY-MM-DD` date. Disable dry-run only for an
intentional live manual post; use force only when deliberately reposting a date.

Local validation never needs the secrets:

```bash
python publish_telegram.py --date 2026-09-15 --dry-run
```

Never commit or print the bot token. If it is exposed, revoke it through BotFather
and replace the repository secret immediately.

## 2. Ask GPT for the Telegram post and JSON

Attach:

- `resources/word-data-template.json`
- `resources/optional-fields-reference.json`
- `resources/wotd.schema.json`
- `telegram-template.txt`

Then use `word-of-the-day-json-prompt.txt`.

Save GPT’s second code block as a `.json` file beside `wotd_generator.py`.

## 3. Generate HTML, LaTeX, and Telegram files

Process every compatible JSON file beside the generator:

```bash
python wotd_generator.py
```

Outputs go to `generated/`:

```text
generated/allocate-extended.html
generated/allocate-extended.tex
generated/allocate-telegram.txt
```

Process one file:

```bash
python wotd_generator.py --input examples/record.json
```

Choose another output folder:

```bash
python wotd_generator.py --output-dir ./finished
```

The generator does not contact any dictionary or pronunciation service.

## 4. Generate the pronunciation MP3s

The audio script scans HTML files in the selected directory. It accepts:

```text
{word}-extended.html
{word}_extended.html
{word}.html
```

Run it against the generated folder:

```bash
python generate_pronunciation_audio.py --directory generated
```

It creates:

```text
generated/audios/<whole-phrase-as-a-filename>.mp3
```

Existing nonempty MP3 files are skipped automatically.

Useful commands:

```bash
# Preview discovered phrases and filenames without generating anything
python generate_pronunciation_audio.py --directory generated --dry-run

# Regenerate existing files
python generate_pronunciation_audio.py --directory generated --force

# Use another American English Edge voice
python generate_pronunciation_audio.py --directory generated --voice en-US-GuyNeural

# Speak slightly more slowly
python generate_pronunciation_audio.py --directory generated --rate=-8%
```

The default voice is `en-US-AriaNeural`.

## Heteronym JSON rule

When all meanings use one IPA, no audio phrase is necessary:

```json
"pronunciation": {
  "primary_ipa": "/ˈæləˌkeɪt/"
}
```

When IPA changes, every meaning must include a short phrase containing the exact headword:

```json
{
  "sense_title": "stored information",
  "part_of_speech": "countable noun",
  "ipa": "/ˈrɛkərd/",
  "audio_phrase": "a record",
  "definition": "...",
  "examples": ["...", "...", "...", "...", "..."]
}
```

The generator rejects a heteronym JSON file when one of its meanings lacks `audio_phrase`.

## Audio discovery behavior

Generated pages carry the phrase in a `data-pronunciation-phrase` attribute. The audio script extracts every unique phrase and creates the matching file.

For an older HTML file without these attributes, it tries to read the page’s `<h1 id="headword">`. If that is unavailable, it derives the word from the filename.

The script:

- scans one directory without recursing;
- deduplicates repeated phrases across pages;
- uses phrase-based filenames shared with the HTML generator;
- writes to a temporary `.part` file first;
- atomically moves a successful file into place;
- retries transient failures;
- skips existing nonempty MP3s unless `--force` is used; and
- reports created, skipped, and failed files separately.

## Schema 1.3

Required top-level fields:

- `document_type`
- `schema_version`
- `slug`
- `word`
- `date`
- `pronunciation.primary_ipa`
- `meanings`

Required fields for every meaning:

- `sense_title`
- `part_of_speech`
- `ipa`
- `definition`
- at least five `examples`

`audio_phrase` remains optional for normal words and becomes conditionally required only when the meanings contain more than one distinct IPA.

All other lexical sections remain optional and disappear cleanly when omitted.

## Creator identity

The templates permanently credit **Amir Kooshky** and include:

- Telegram channel: `https://t.me/KooshkyTOEFL`
- Instagram: `https://www.instagram.com/kooshkytoefl`
- Personal Telegram: `https://t.me/KooshkyTOEFL_pv`
