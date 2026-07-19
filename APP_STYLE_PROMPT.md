# Kooshky TOEFL App Styling Prompt

Turn the supplied app into a complete, polished HTML/CSS/JavaScript browser app.

Preserve all existing app functionality and data. Improve structure, styling, responsiveness, accessibility, and interaction quality without removing working features.

Unless I explicitly request otherwise, deliver the app as one standalone HTML file. When the app already relies on separate data, audio, image, or JavaScript files, preserve those relative paths and do not force everything into one file.

## Student-facing output

The finished app must be suitable for students to use directly.

Do not include:

- instructions addressed to me;
- references to our conversation;
- development notes in visible page content;
- unfinished placeholders;
- explanations of your design decisions;
- promotional filler.

Use clear, natural interface text.

## Brand and visual system

Use the **Kooshky Editorial Signal** visual identity.

Light palette:

- page: `#F4F0E8`
- surface: `#FCFAF6`
- text: `#182027`
- muted text: `#59636C`
- border: `#D7D0C3`
- saffron accent: `#A9470D`
- teal accent: `#1E5B63`
- saffron soft surface: `#F3E2D3`
- teal soft surface: `#DDEAE8`

Dark palette:

- page: `#111417`
- surface: `#181D21`
- text: `#ECE7DD`
- muted text: `#ADB4B8`
- border: `#30383E`
- saffron accent: `#F28C45`
- teal accent: `#70B7B4`
- saffron soft surface: `#332219`
- teal soft surface: `#193033`

Use centralized CSS variables. Do not scatter raw colors across component rules.

Use:

- **Literata** for app titles and major headings;
- **IBM Plex Sans** for interface text, instructions, buttons, inputs, and results.

The design should be restrained, academic, clear, and functional. Avoid gradients, glassmorphism, oversized shadows, excessive pill shapes, giant illustrations, and decorative animation.

## App-specific layout

This is an app, not a study article.

Do **not** create:

- a large hero section;
- an automatically generated table of contents;
- a mid-page Telegram popup;
- a text-selection dictionary popup;
- chapter numbering;
- long marketing copy.

Use a compact app shell:

1. A site header.
2. A compact app title area.
3. The actual app interface as the visual priority.
4. A restrained footer.

The title area should contain only:

- the app name;
- one short description if useful;
- compact status or mode controls when relevant.

Do not waste vertical space before the functional interface.

## Header and site links

Include a compact header containing:

- a clickable Kooshky’s TOEFL Guides name or logo linking back to the site root;
- `Home` (find the domain using js and add a / instead of the current path);
- the theme toggle.

Repeat the important site links in a restrained footer. Include:

- Home;
- Telegram;
- Instagram.

Use these social links:

- Telegram: `https://telegram.me/KooshkyTOEFL`
- Instagram: `https://instagram.com/kooshkytoefl`
- Direct message: `https://telegram.me/kooshkyTOEFL_pv`

Do not turn social links into giant banners.

## Theme preference

Before rendering, check:

`localStorage["kooshky-guides:theme:v1"]`

Rules:

- `dark` → open in dark mode;
- `light` → open in light mode;
- missing, unavailable, or invalid → default to light mode;
- do not use the operating-system theme as the fallback.

Whenever the user changes the theme, immediately save either `light` or `dark` to the same key.

Apply the theme to the document, `color-scheme`, favicon, app controls, charts, feedback states, dialogs, and any theme-dependent images.

Avoid a flash of the wrong theme.

## Interface design

Use semantic controls:

- `<button>` for actions;
- `<a>` for navigation;
- `<label>` with every form control;
- `<fieldset>` and `<legend>` for grouped options where appropriate;
- `<output>` or live regions for changing results;
- `<dialog>` or accessible custom dialogs only when truly needed.

Prioritize:

- obvious primary actions;
- visible current state;
- clear progress;
- immediate and specific feedback;
- keyboard operation;
- touch-friendly controls;
- readable disabled states;
- reliable reset and retry behavior.

Keep buttons and inputs consistent in height, border, radius, typography, and focus treatment.

Do not use the browser’s large default blue focus halo. Provide a visible, compact, theme-colored `:focus-visible` outline with sufficient contrast.

Do not make icons enormous. Give every icon an explicit width and height.

## Responsive behavior

Design for desktop first, but make the interface work properly around `360px` wide.

Use Grid and Flexbox. Keep ordinary layout in document flow.

Prevent horizontal overflow from:

- long filenames;
- long prompts;
- result text;
- audio controls;
- tables;
- buttons;
- progress labels.

Use `min-width: 0`, wrapping, and responsive stacking where needed.

Fixed controls must respect:

- `env(safe-area-inset-bottom)`;
- phone viewport edges;
- the mobile menu;
- virtual keyboards.

Do not rely only on mouse events. Use pointer, touch, keyboard, and appropriate form events.

## App data and persistence

When the app stores user work locally:

- use clear, app-specific `localStorage` or IndexedDB keys;
- prefix keys with `kooshky-apps:`;
- include a version suffix;
- catch storage errors;
- do not let storage failure break the app.

Example:

`kooshky-apps:dictation-practice:progress:v1`

Do not overwrite the shared theme key.

## Audio and recording apps

When the app uses audio:

- preserve relative audio paths;
- show clear loading and error states;
- disable controls while an action is unavailable;
- avoid overlapping playback;
- make replay and stop controls obvious;
- handle rejected autoplay gracefully.

When the app records audio:

- request microphone permission only when the user starts recording;
- explain errors plainly;
- show recording state and elapsed time;
- allow stopping early;
- clean up media tracks after recording;
- preserve or download recordings only when the app is designed to do so.

## Accessibility and motion

Include:

- a meaningful `<title>`;
- a useful meta description;
- `lang="en"`;
- a viewport meta tag;
- a skip-to-app link;
- logical headings;
- accessible names;
- visible `:focus-visible` styling;
- suitable contrast in both themes;
- keyboard-accessible menus and dialogs;
- `aria-live` only for useful updates;
- `aria-expanded` and `aria-pressed` where appropriate.

Respect `prefers-reduced-motion`. Use only short, functional transitions.

## Code quality

Use plain modern JavaScript unless the existing app already depends on something else.

Organize JavaScript into small functions. Avoid unnecessary globals. Catch failures around optional features so one failure does not disable the entire app.

Keep:

- design tokens together;
- reusable components grouped;
- app-specific styles clearly separated;
- event listeners deliberate;
- filenames and relative paths unchanged unless I request changes.

## Final audit

Before output, check:

1. Desktop layout.
2. A `360px` phone viewport.
3. Mobile menu opening, closing, and reopening after scrolling.
4. Theme persistence through `kooshky-guides:theme:v1`.
5. Correct root links from the app’s actual folder depth.
6. Keyboard-only use.
7. Touch controls.
8. Long labels and long filenames.
9. Audio loading and failure states, when applicable.
10. Recording permission denial, when applicable.
11. Reset, retry, and completion states.
12. No unexpected horizontal scrolling.
13. No popup, table of contents, or oversized hero has been added.

Return the complete working app, not a mockup or partial fragment.
