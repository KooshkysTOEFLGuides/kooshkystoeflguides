# Speaking Pack agent instructions

These instructions apply to `SpeakingPack/` and supplement the repository-wide `AGENTS.md`. If they conflict, follow the repository-wide instructions unless this file is more specific about the Speaking Pack pipeline.

## Purpose and page type

The Speaking Pack is a topic-based TOEFL Speaking collection. Each modern topic pack combines:

- a study guide containing vocabulary, definitions, examples, collocations, reusable chunks, and an idea bank;
- corpus-calibrated four-question interview practice;
- a browser app for recording, transcribing, saving, exporting, and restoring voice responses.

Treat `SpeakingPack/index.html` as the collection index. Treat a rendered topic page as a study article with an embedded recording app. Preserve both sides when changing the shared template.

## Read this first

Before generating or changing a topic, read completely:

1. `prompt/README.md`
2. the relevant files under `topics/<Topic>/prompts/`
3. `prompt/render_topic_packs.py`
4. `prompt/speaking-pack-template.html` and `prompt/speaking-recorder.js` only when changing presentation or recording behavior

Always inspect `git status --short` before doing work. Existing modifications and generated topic files belong to the user or a previous session; do not overwrite, remove, or fold them into unrelated work without understanding them.

## Sources of truth

- `prompt/topics.txt` is the taxonomy source of truth: stable topic number, directory title, and seed subtopics.
- `prompt/words.txt`, `prompt/ideas.txt`, and `prompt/questions.txt` are the master prompt templates.
- `topics/<Topic>/prompts/` contains the filled prompts for that topic.
- `topics/<Topic>/words.json`, `ideas.json`, and `questions.json` are the educational-content sources of truth for a completed modern pack.
- `prompt/speaking-pack-template.html` is the shared page shell.
- `prompt/speaking-recorder.js` is the shared recording/transcription app.
- `prompt/render_topic_packs.py` is the only normal way to assemble modern topic HTML.
- `SpeakingPack/index.html` is the public list of available packs.
- `prompt/.topic-scaffolder-state.json` is managed state. Never edit it manually.

Do not hand-edit a generated modern topic HTML file to change educational content or shared layout. Change its JSON source or the shared template/script, then rerender. Historical packs without the three JSON files may remain standalone until explicitly migrated.

## Resume and status audit

At the start of a new session:

```bash
git status --short
python3 SpeakingPack/prompt/generate_topic_prompts.py --dry-run
python3 SpeakingPack/prompt/render_topic_packs.py --dry-run
```

Then inspect the requested topic directory. A topic may be:

- **prompt-only:** it has `prompts/` but no three JSON files; run all content stages;
- **partially generated:** preserve valid existing stages and continue only after checking that later files are not based on stale earlier data;
- **complete:** it has three JSON files and one HTML file; validate before deciding whether regeneration is needed;
- **historical:** it has standalone HTML or old text outputs but no modern JSON pipeline; do not silently replace it;
- **locked:** any top-level HTML file causes the prompt scaffolder to protect that topic from taxonomy-driven rename, removal, or prompt regeneration.

Do not mistake a scaffolder lock for a renderer lock. The renderer is expected to rebuild a complete topic's HTML from its JSON sources.

## Taxonomy and prompt scaffolding

Run the reentrant scaffolder from the repository root:

```bash
python3 SpeakingPack/prompt/generate_topic_prompts.py
```

Preview first when taxonomy or master prompts may have changed:

```bash
python3 SpeakingPack/prompt/generate_topic_prompts.py --dry-run
```

The scaffolder creates or synchronizes:

```text
topics/<Topic>/prompts/
├── words.txt
├── ideas.txt
└── questions.txt
```

Locks are intentional safeguards. Never remove a topic HTML file merely to bypass a warning unless the user explicitly authorizes that content migration. For an intentional master-prompt format migration, use:

```bash
python3 SpeakingPack/prompt/generate_topic_prompts.py --refresh-locked-prompts
```

Use that option only after reviewing the shared prompt change and understanding that it refreshes prompts, not JSON content or HTML.

If a generic prompt has a structural flaw, fix the appropriate master prompt first, regenerate or refresh topic prompts as appropriate, and then regenerate the affected JSON stage and all dependent stages. Do not patch only one filled topic prompt when the fix should apply to future topics.

## Full topic-generation pipeline

Run the stages in order. The output of an earlier stage is an input and constraint for later stages.

### Stage 1: vocabulary

Use `topics/<Topic>/prompts/words.txt`. Save one valid UTF-8 JSON object, with no Markdown fence or commentary, as:

```text
topics/<Topic>/words.json
```

The JSON must conform exactly to schema version 1 described in the prompt.

### Stage 2: idea bank

Use `topics/<Topic>/prompts/ideas.txt` together with the approved `words.json`. Save the exact JSON response as:

```text
topics/<Topic>/ideas.json
```

Do not create ideas independently of the vocabulary coverage, but do add genuinely useful answer angles that vocabulary organization alone does not capture.

### Stage 3: interview sets

Use `topics/<Topic>/prompts/questions.txt`, the approved `words.json`, `ideas.json`, and:

```text
prompt/references/real-toefl-speaking-corpus.txt
```

Save the exact schema-version-1 JSON response as:

```text
topics/<Topic>/questions.json
```

The corpus is for task calibration. Ignore its Listen and Repeat content. Do not copy transcription errors or force every small subtopic into its own interview.

### Stage 4: deterministic rendering

Validate without writing first:

```bash
python3 SpeakingPack/prompt/render_topic_packs.py "<Topic>" --dry-run
```

Then render:

```bash
python3 SpeakingPack/prompt/render_topic_packs.py "<Topic>"
```

Run the dry run again. A completed topic must report `CURRENT`, not `WOULD RENDER` or an error.

Never invent a separate HTML-generation prompt. HTML is deliberately deterministic so shared template improvements can be applied to every complete topic.

## Content quality requirements

The renderer's minimums are safety floors, not content targets. Follow the stronger requirements in the prompts.

An individual filled topic prompt may intentionally define a narrower target than the master prompt. Respect a documented topic-specific renderer exception rather than padding that topic back to global size. As of this file, `Weather, Seasons, and Climate in Daily Life` is the only such exception; its rationale and exact floors are documented in `prompt/README.md` and `render_topic_packs.py`.

### Vocabulary and chunks

- Prefer 100+ useful headwords and 100+ reusable chunks when the topic genuinely supports them.
- Use enough distinct thematic sections to cover the topic naturally; broad topics normally need about 10–18.
- Treat seed subtopics as minimum coverage, not a closed or mechanically copied taxonomy.
- Vary section sizes according to lexical richness. Do not give every section the same number of cards or chunks.
- Vary collocation counts word by word. Do not give every headword exactly four or five collocations.
- Include only natural, topic-relevant collocations. Never add weak items merely to alter a count.
- Give every headword an accurate B1–B2-friendly definition and two distinct, concrete, idiomatic examples.
- Do not recycle one example frame by swapping in a different headword. Read examples as educational content, not schema filler.
- When the same spelling has multiple useful parts of speech or relevant senses, create separate cards with separate definitions, examples, and collocations. For example, a useful noun and verb should not be merged as `noun/verb`.
- Add related word-family forms only when independently common and useful. Do not manufacture complete families.
- Prefer active B1–B2 speaking language, with restrained upper-B2/C1 upgrades. Avoid obscure, literary, technical, or essay-only vocabulary.
- A phrase's `reusable_core` must be a non-empty exact substring occurring exactly once in its `text`.

### Idea bank

- Prefer 100+ genuinely distinct, reusable answer ideas when the topic supports them.
- Vary category depth based on the number of useful mechanisms and perspectives.
- Include personal, practical, social, educational, balanced, negative, and broader angles only when relevant.
- Make each context explain, qualify, illustrate, or apply its heading. Do not repeat the heading in longer words.
- Do not split one mechanism into superficial synonyms or pad the bank with generic claims.
- Avoid repeated context templates. A bank of machine-readable entries still needs polished, individually meaningful content.

### Interview questions and sample answers

- Every interview set has exactly four numbered questions and one answer per question.
- Question 1 is normally accessible and personal; later questions may broaden, compare, explain, advise, or evaluate without requiring specialist knowledge.
- Use generic prerecorded-interviewer transitions. Check capitalization and grammar after transitions.
- Sample answers should normally be 65–90 words, about 4–6 short sentences, and plausible in roughly 45 seconds.
- Write realistic B1–B2 speech: answer directly, give one main reason, add a concrete example or consequence, and stop naturally.
- Prefer ordinary connectors and contractions. Avoid essay framing, compressed sophistication, abstract noun chains, and forced two-sided conclusions.
- Do not repeat a fixed answer scaffold, bridge sentence, opening, or ending across the bank.
- Read every answer aloud mentally. Rewrite sentences that are too long for one breath or sound like edited writing.
- Regenerating `words.json` makes `ideas.json` and `questions.json` potentially stale. Regenerating `ideas.json` makes `questions.json` potentially stale. Rebuild dependent stages unless careful review proves they remain aligned.

## Mechanical-pattern and integrity audit

Before rendering, calculate and inspect:

- vocabulary section count;
- headwords per section and total;
- phrases per section and total;
- collocations per headword;
- idea categories, ideas per category, and total;
- interview set and question totals;
- sample-answer word and sentence ranges;
- duplicate `(term, part_of_speech)` pairs;
- duplicate or near-duplicate ideas, questions, answer openings, and endings.

The renderer rejects several dominant-count patterns, but passing the renderer does not prove quality. Do not evade a rejection through random deletion, arbitrary splitting, or filler. Reassess content depth.

Validate each JSON file directly as well:

```bash
python3 -m json.tool "SpeakingPack/topics/<Topic>/words.json" >/dev/null
python3 -m json.tool "SpeakingPack/topics/<Topic>/ideas.json" >/dev/null
python3 -m json.tool "SpeakingPack/topics/<Topic>/questions.json" >/dev/null
```

## Shared template and voice-practice rules

Every modern generated page inherits `prompt/speaking-pack-template.html` and loads `prompt/speaking-recorder.js`.

Preserve these recording behaviors unless the user requests a change:

- microphone permission is requested only after the student presses Record;
- the 45-second timer starts only after permission, microphone setup, and the beep;
- students may stop early, and capture stops automatically at 45 seconds;
- transcription is enabled by default but may be turned off before recording;
- Web Speech recognition runs live alongside recording and cannot transcribe an existing saved blob;
- transcript finalization briefly waits for the recognizer's buffered final result without extending the audio duration;
- recordings, editable transcripts, and metadata are stored in IndexedDB, not `localStorage`;
- all topics share one origin-wide local voice library, keyed back to the original topic/set/question;
- students can download individual audio and transcript files;
- whole-library export is a human-readable ZIP with a manifest, and loading that ZIP restores saves without duplicating IDs;
- storage estimates, persistence requests, quota failures, backup warnings, and destructive confirmations remain clear;
- clearing all voice data requires two confirmations;
- microphone tracks, audio contexts, timers, and object URLs are cleaned up.

The site's own code does not upload recordings. Browser speech recognition may use the browser provider's online service, so retain the visible privacy warning.

If `speaking-recorder.js` changes, increment its cache-busting `?v=` in the shared template and rerender every complete modern pack. Validate recording behavior in both Chrome and Firefox where possible. Do not replace compressed browser-native recording with large WAV storage unless the user explicitly accepts the storage tradeoff.

## Navigation and registries

When a new topic HTML file is ready:

1. Add one polished `article.resource-card` to `SpeakingPack/index.html` in deliberate order.
2. Use the next visible Speaking Pack number.
3. Link to the exact case-sensitive repository path under `SpeakingPack/topics/`.
4. Verify both the title link and `Open … →` link target the existing file.
5. Do not leave visible templates, dummy links, or placeholder cards in the finished index.

The central `content-data.js` should normally contain one public entry for `SpeakingPack/index.html`, not one entry per child topic. Do not add every topic to the central registry unless the user wants those child pages independently discoverable. If the collection index is newly added, moved, renamed, or removed, update `content-data.js` and its cache-busting versions according to the repository-wide instructions.

Use portable root-relative public navigation and never hard-code a deployment hostname. Preserve case-sensitive local asset paths. The canonical social links are defined in the repository-wide instructions.

## Final verification

For a generated topic, run at minimum:

```bash
python3 -m json.tool "SpeakingPack/topics/<Topic>/words.json" >/dev/null
python3 -m json.tool "SpeakingPack/topics/<Topic>/ideas.json" >/dev/null
python3 -m json.tool "SpeakingPack/topics/<Topic>/questions.json" >/dev/null
python3 SpeakingPack/prompt/render_topic_packs.py "<Topic>" --dry-run
python3 SpeakingPack/prompt/generate_topic_prompts.py --dry-run
node --check SpeakingPack/prompt/speaking-recorder.js
git diff --check
git status --short
```

Also verify:

- the HTML file exists and contains the expected topic title;
- the index links resolve to that file;
- favicon and shared script paths are correct at the actual directory depth;
- light and dark modes remain legible;
- the generated TOC, collapsed sample answers, dictionary menu, Telegram invitation, social links, and go-to-top control still work;
- recording controls appear under every question;
- default transcription, permission timing, cutoff, playback, editing, individual downloads, ZIP export/import, deletion, and storage messaging remain usable;
- layout remains usable at desktop size and approximately 360px without horizontal overflow.

Report exact content totals, output path, validation results, and whether changes are committed. Do not commit or push unless the user asks.

## Commit boundaries

Keep commits focused. A normal new-topic commit may include:

- the topic's three JSON files;
- its rendered HTML;
- its `SpeakingPack/index.html` card.

Do not include unrelated working-tree changes. Shared prompt, renderer, template, or recorder changes should usually be a separate commit because they affect multiple current and future packs.
