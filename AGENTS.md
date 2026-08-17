# Kooshky's TOEFL Guides: repository instructions

These instructions apply to the entire repository. This is a static educational website hosted on GitHub Pages. Its current custom domain is `kooshkystoeflguides.ir`, but the domain may change.

## Deployment and path rules

- Keep the site compatible with static GitHub Pages hosting: do not require server-side code, runtime secrets, a database, or a build step unless the user explicitly requests one.
- Never hard-code `kooshkystoeflguides.ir`, a `github.io` hostname, or any other deployment hostname into site code.
- For a link to the site root, use a root-relative URL such as `/` when appropriate, or derive the current origin in JavaScript with `new URL("/", window.location.origin)`. Do not infer the root by counting directory levels.
- Preserve working relative paths to local audio, images, scripts, data, and downloads. Remember that URL paths are case-sensitive on GitHub Pages.
- Prefer portable static files that work both on the deployed site and, where practical, when opened locally. Do not break local use merely to simplify deployment.
- Do not impose a site-wide migration or rigid new folder structure for an isolated page change.
- Check `CNAME` and existing site conventions, but treat the domain as deployment configuration rather than an application constant.

## First determine the page type

Classify the requested work before implementing it:

- A **study article/guide** primarily presents educational content for reading. Follow "Article requirements."
- A **browser app** primarily asks the student to interact, practise, record, answer, generate, or track progress. Follow "App requirements."
- A **collection/section index** links several closely related guides, parts, packs, or practice files. Follow "Collection index requirements."
- A shared site page (home, contents, about, app directory, and similar) should follow the shared brand and repository conventions, but need not inherit article-only or app-only features.
- When modifying an existing file, preserve its substantive content, data, URLs, and working behavior unless the user explicitly asks otherwise.

## Site architecture and registries

The central site listings are data-driven. Treat these files as sources of truth; do not manually duplicate their entries in `index.html`, `contents.html`, or `apps.html`.

### `content-data.js`

- `window.KOOSHKY_SECTIONS` defines the valid content categories shown by the site.
- `window.KOOSHKY_CONTENT` supplies articles and collection landing pages to the homepage and All Contents page through `site.js`.
- Whenever adding, moving, renaming, or removing public educational content, update its registry entry in `content-data.js` in the same task.
- A content entry uses `title`, repository-root-relative `href` (without a hard-coded domain), a valid `section` ID from `KOOSHKY_SECTIONS`, `summary`, display `date`, optional ISO 8601 `publishAt` with an explicit timezone offset, and `featured`.
- `featured: true` makes a published entry eligible for the homepage; `featured: false` keeps it in the full contents listing without featuring it.
- Items with no `publishAt` are treated as published. Invalid values are hidden; future values stay hidden until their publication time.
- For a multi-part collection, normally register the collection's `index.html` as the public entry rather than registering every child page and cluttering the central listing. Register individual child pages only when they should also be independently discoverable.

### `apps-data.js`

- `window.KOOSHKY_APPS` supplies the apps directory and featured homepage apps through `site.js`; array order controls display order.
- Whenever adding, moving, renaming, or removing an app, update `apps-data.js` in the same task.
- Each entry requires `name`, repository-root-relative `href`, and `description`. `logo` and `featured` are optional. Use a square logo when available; the UI has a fallback when it is absent or fails.
- `featured: true` also exposes the app on the homepage.

After changing either registry, verify its consumers. If its `<script src>` has a cache-busting query such as `content-data.js?v=7` or `apps-data.js?v=1`, increment that version consistently in every HTML file that loads the changed registry. Verify that the referenced path exists, the registry remains valid JavaScript, scheduled visibility behaves as intended, and `site.js` renders the entry on every applicable page.

## Shared student-facing rules

- Produce complete, polished, student-facing work—not a mockup, fragment, or description of what could be built.
- Do not expose conversation references, instructions to the repository owner, generation notes, design rationale, developer notes, unfinished placeholders, or promotional filler in visible page content.
- Preserve substantive educational material. Improve organization, labels, examples, hierarchy, clarity, accessibility, and interactions without silently deleting explanations, exercises, answers, or sample responses.
- Use semantic HTML: meaningful heading levels and appropriate elements such as `header`, `nav`, `main`, `article`, `section`, `aside`, `footer`, `details`, `summary`, `button`, `a`, `label`, `fieldset`, `legend`, and `output`.
- Use links for navigation and buttons for actions. Every form control needs an accessible label.
- External links opened with `target="_blank"` must also use `rel="noopener noreferrer"`.
- Include `lang="en"`, a meaningful `<title>`, a useful meta description, and a responsive viewport meta tag.
- Use plain modern JavaScript unless existing code has a necessary dependency. Keep functions small, globals limited, and optional-feature failures isolated.
- Keep ordinary layout in document flow. Use Grid/Flexbox, `min-width: 0`, sensible wrapping, and constrained media to prevent horizontal overflow.
- Design desktop-first while ensuring full usability at approximately 360px wide. Account for long headings, labels, filenames, links, tables, and media controls.
- Support keyboard, pointer, and touch input as applicable. Use compact, high-contrast `:focus-visible` styling.
- Respect `prefers-reduced-motion`; transitions should be short and functional, generally 160–220ms.
- Fixed elements must remain within the viewport, respect safe-area insets, and avoid virtual keyboards and other fixed controls.
- Avoid unnecessary churn. Preserve filenames and paths unless changing them is part of the request.

## Brand: Kooshky Editorial Signal

The visual character is a modern academic field guide: serious, readable, editorial, restrained, and distinctive. It combines textbook clarity, academic-journal character, subtle annotated-research cues, and controlled saffron/teal accents. Avoid generic AI/SaaS styling.

Do not use purple-blue gradients, glassmorphism, glow effects, oversized shadows, excessive rounded cards or pills, a card around every paragraph, childish styling, giant marketing headings, decorative animation, or colors outside the system without a content-driven reason.

Define centralized CSS custom properties and use them instead of scattering raw colors through component rules:

```css
:root {
  --color-page: #F4F0E8;
  --color-surface: #FCFAF6;
  --color-text: #182027;
  --color-text-muted: #59636C;
  --color-border: #D7D0C3;
  --color-accent: #A9470D;
  --color-accent-secondary: #1E5B63;
  --color-accent-soft: #F3E2D3;
  --color-secondary-soft: #DDEAE8;
  --font-heading: "Literata", Georgia, "Times New Roman", serif;
  --font-body: "IBM Plex Sans", Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

[data-theme="dark"] {
  --color-page: #111417;
  --color-surface: #181D21;
  --color-text: #ECE7DD;
  --color-text-muted: #ADB4B8;
  --color-border: #30383E;
  --color-accent: #F28C45;
  --color-accent-secondary: #70B7B4;
  --color-accent-soft: #332219;
  --color-secondary-soft: #193033;
}
```

- Use Literata for titles and major headings; use IBM Plex Sans for body copy and controls. Google Fonts are allowed, but fallbacks must remain attractive and usable.
- Keep typography compact and editorial. Article measure should normally be about 68–74ch. Use `clamp()` where it helps long titles wrap safely.
- Use a coherent spacing scale (for example `.25rem`, `.5rem`, `.75rem`, `1rem`, `1.5rem`, `2rem`, `3rem`, `4.5rem`) and restrained radii (roughly 4px, 6px, and 10px).
- Cards use thin borders, little or no shadow, modest radii, and purposeful spacing.
- Saffron signal stripes indicate warnings, common errors, key exam notes, and high-priority information. Teal indicates definitions, explanations, strategies, and useful distinctions. Neutral borders suit examples and ordinary notes.
- Useful restrained labels include `COMMON ERROR`, `EXAMPLE`, `COMPARE`, `REMEMBER`, `STRATEGY`, `KEY POINT`, `SAMPLE ANSWER`, and `ANSWER KEY`.

## Shared identity and links

Collection name: **Kooshky's TOEFL Guides**  
Collected and compiled by: **Amir Kooshky**

Canonical social links:

- Telegram: `https://telegram.me/KooshkyTOEFL`
- Instagram: `https://instagram.com/kooshkytoefl`
- Direct Telegram message: `https://telegram.me/kooshkyTOEFL_pv`

Keep promotions restrained. Article heroes may briefly invite students to Telegram and Instagram; app interfaces must not turn social links into prominent banners. Repeat appropriate Home, Telegram, and Instagram links in the footer.

## Shared theme behavior

- Read `localStorage["kooshky-guides:theme:v1"]` before rendering when practical to avoid a wrong-theme flash.
- Exact value `dark` selects dark mode; exact value `light` selects light mode. Missing, unavailable, or invalid values default to light. Do not use the OS theme as fallback.
- Save `light` or `dark` immediately when the user changes the theme. Catch storage errors so they never break the page.
- Apply the theme consistently to `color-scheme`, favicon, images, controls, charts, feedback, and dialogs where relevant, and keep all states legible in both themes.
- Update accessible toggle state such as `aria-pressed` and an accurate accessible name.

# Article requirements

Unless explicitly requested otherwise, a new guide should be one standalone `.html` file with inline CSS and JavaScript. Do not require a framework, package manager, server, shared asset directory, or rigid folder structure. Structure code cleanly enough that tokens, components, and scripts could later be extracted.

## Article layout and content

- Include a clear but restrained branded hero near the top: collection name, guide title, concise subtitle/description, Amir Kooshky credit, social links, and a brief natural invitation to find more material.
- Use an editorial masthead label such as `KOOSHKY'S TOEFL GUIDES` with a thin saffron rule/marker.
- Major sections may use restrained automatic labels such as `CHAPTER 01`.
- Prefer comparison cards, definition lists, stacked rows, or responsive columns over wide tables. When a table is educationally necessary, wrap it in an accessible horizontal overflow container and keep text wrapping.
- Put examples in calm neutral panels and emphasize only the relevant language—not entire example paragraphs.
- Use responsive two-column comparisons on desktop and stack them on phones.
- Use compact rectangular vocabulary/collocation chips that allow long text to wrap.
- Separate exercises from answers. Use semantic `details`/`summary` for answers, explanations, sample responses, model answers, and optional expansions.
- Core educational content must remain readable if JavaScript fails.

## Article navigation

- Generate a table of contents from semantic headings with JavaScript. Create stable, unique heading IDs.
- Include major sections and nested levels. Each level is collapsible and all levels start collapsed.
- Where practical, mark the currently visible section. Style the TOC as an editorial chapter index, not a dashboard.
- The site name/logo and a clearly labelled `Home` link must both navigate to the current site root without opening a new tab.
- If navigation is sticky, give headings enough `scroll-margin-top` for anchor jumps.
- On desktop, use a restrained side panel, sticky index, or collapsible panel that does not dominate reading.
- On mobile, collapse navigation by default. Keep its open/reopen control visible while scrolling. Keep the drawer within the viewport; close it by button, outside press, and Escape; manage focus sensibly.

## Article interactive features

Include these unless the user explicitly opts out:

1. **Go to top:** show after meaningful scrolling; keep it tappable, keyboard accessible, safe-area aware, and clear of dialogs/menus. Coordinate overlap with a class, data attribute, or CSS variable rather than a fragile sibling selector.
2. **Telegram invitation:** near the document midpoint, show a restrained modal invitation once per guide—not an alert or bottom banner. It must close by button, backdrop, and Escape, restore focus, stay inside the viewport, and not reappear after dismissal or interaction. Store state safely at `kooshky-guides:{document-slug}:telegram-invite:v1`, deriving a stable slug from the title.
3. **Selection dictionary:** for a sensible selected word/short phrase in article content, offer Cambridge, Oxford Learner's Dictionaries, Merriam-Webster, and a Google meaning search. Encode selection with `encodeURIComponent()` and use these patterns:

```text
https://dictionary.cambridge.org/dictionary/english/{word}
https://www.oxfordlearnersdictionaries.com/definition/english/{word}?q={word}
https://www.merriam-webster.com/dictionary/{word}
https://www.google.com/search?q=meaning+of+{word}
```

Support `selectionchange`, `pointerup`, `touchend`, and keyboard-created selection where practical. Read delayed mobile selections safely; position from the range rectangle with a viewport-safe fallback; avoid selection handles. Ignore empty, punctuation-only, very long, or interface-control selections. Dismiss on outside interaction, scrolling, Escape, empty selection, or unrelated focus without prematurely clearing selected text.

Use a deliberate layering order for header/navigation, floating controls, selection menu, modal backdrop, and modal. Do not solve conflicts with arbitrary huge z-index values.

## Easily removable article promotion

Keep the creator name/credit independent from promotional links. Mark all optional promotional UI—including social-link groups and the Telegram invitation—with a consistent hook such as `[data-promotion]`.

Near the end of the inline script, include this clearly labelled, commented-out switch:

```js
// Set to true to remove promotional links and invitations while keeping creator credit.
const REMOVE_PROMOTIONS = false;
```

When true, remove or hide every `[data-promotion]` element and do not initialize or show the Telegram invitation. Add one short code comment explaining that the owner only needs to change `false` to `true`; do not put these owner instructions in visible page content.

## Article final audit

Before finishing, check: desktop and 360px layouts; long titles/headings/chips/links; no unexpected horizontal scrolling; mobile navigation close and reopen after scrolling; correct unobscured anchor jumps; go-to-top placement; Telegram open/close/focus/persistence; dictionary selection by mouse, touch, and keyboard plus all four links; both themes and reload persistence; `details` controls; reduced motion; and no viewport escape.

When asked to create the file, write the complete HTML into the repository and provide a clickable local file link in the response. Do not leave placeholders such as `<!-- Add the rest here -->`.

# Collection index requirements

When a directory contains several closely related content pages—such as a multipart grammar course, a set of topic packs, or a guide/workbook pair—create or maintain an `index.html` in that directory when a single landing page will make the collection easier to understand and navigate. Use `SpeakingPack/index.html` and `Grammar/RelativeClausesNew/index.html` as the primary visual and structural references.

An index is a concise map of the collection, not another full guide and not an app:

- Use the Kooshky Editorial Signal tokens, typography, light/dark theme behavior, skip link, sticky compact header, linked brand, `Home`, `All contents`, theme toggle, and restrained footer found in the reference indexes.
- Begin with a moderate editorial intro containing an eyebrow identifying the collection, one clear `h1`, a short explanation, and—when genuinely helpful—a teal-accented information/example box explaining purpose or use.
- Follow with a focused collection section: eyebrow, `h2`, brief orientation, then semantic resource groups and a simple single-column `.resource-list` in normal document flow.
- Represent each destination with an `article.resource-card`: a small uppercase number/stage/type label, linked `h3`, concise student-facing description, and explicit `Open … →` link. Use a thin teal left border for normal resources and saffron for a meaningfully different category such as practice.
- Keep cards in a deliberate learning order when sequence matters. Add a compact saffron `recommended-order` aside when students should follow that order; otherwise say that items may be studied independently.
- Separate genuinely different resource types into labelled groups, such as Study guides and Practice files. Do not create empty groups, visible placeholders, dummy links, or copy-this-card examples in finished output.
- Prefer the restrained vertical list used by the reference pages over a dense dashboard grid. Adding or removing a resource must not require CSS layout changes.
- Do not add article-only generated TOC, selection dictionary, mid-page Telegram modal, chapter markers, or go-to-top control unless the index becomes long enough to justify the last item.
- Use links that remain valid under GitHub Pages and the deployment rules above. Verify every child target and preserve intentional ordering.
- Make the collection index the directory's canonical entry point when appropriate. Link sibling pages back to it if doing so improves navigation and is within the requested scope.
- Register the collection index in `content-data.js` as described above. Usually the central registry should point to the index, while the index itself owns the list of its child pages.

Before finishing, check the index at desktop and 360px widths, theme persistence, keyboard focus, link validity, content order, long titles/descriptions, and absence of horizontal overflow. When adding a child page to an existing collection, also update the collection's `index.html` in the same task.

# App requirements

An app is not an article. Preserve all existing functionality and data while improving structure, styling, responsiveness, accessibility, and interaction quality.

Unless explicitly requested otherwise, deliver a new app as one standalone HTML file. If an existing app uses separate data, audio, image, or JavaScript files, preserve those files and relative paths rather than forcing everything inline.

## App shell

- Do not add an oversized hero, generated TOC, chapter numbering, mid-page Telegram invitation, text-selection dictionary, or long marketing copy.
- Use a compact site header, compact title area, the app interface as the visual priority, and a restrained footer.
- The title area contains only the app name, at most one short useful description, and relevant compact status/mode controls.
- Header: linked Kooshky's TOEFL Guides name/logo to the current site root, a `Home` link, and theme toggle.
- Footer: restrained Home, Telegram, and Instagram links; include direct-message link only when useful.

## App interaction and state

- Make the primary action obvious, current state and progress visible, feedback immediate and specific, disabled states readable, and reset/retry reliable.
- Keep buttons and inputs consistent in height, border, radius, typography, and focus treatment. Give every icon explicit dimensions; do not use enormous icons.
- Use `output` or a restrained live region for useful changing results. Use `dialog` or an accessible custom dialog only when warranted. Set `aria-expanded` and `aria-pressed` where appropriate.
- Avoid mouse-only event handling. Ensure controls are touch-friendly and keyboard operable.
- When storing user work, use a clear app-specific key prefixed `kooshky-apps:` with a version suffix, for example `kooshky-apps:dictation-practice:progress:v1`. Catch storage failures. Never overwrite the shared theme key with app data.

## Audio and recording apps

- Preserve relative audio paths. Show loading and plain-language failure states, disable unavailable controls, prevent overlapping playback, make replay/stop obvious, and handle rejected autoplay.
- Request microphone permission only when the student starts recording. Show recording state and elapsed time, allow early stopping, explain denial/failure clearly, and always clean up media tracks.
- Preserve or offer downloads of recordings only when the app is designed to do so.

## App final audit

Before finishing, check: desktop and 360px layouts; no horizontal scrolling; theme persistence; correct root navigation from the actual folder depth; keyboard and touch use; long labels, prompts, filenames, result text, audio controls, and progress labels; mobile menu close/reopen after scrolling if present; reset/retry/completion; and relevant audio errors, autoplay rejection, or microphone denial. Confirm that no article-only popup, TOC, dictionary, chapter numbering, or oversized hero was added.

Return or write the complete working app, not a partial fragment, and report the files changed plus the verification performed.
