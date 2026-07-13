# Kooshky's TOEFL Guides — Simple Site

This version keeps the homepage deliberately minimal and makes the article lists editable from one file.

## Files

- `index.html` — minimal homepage
- `contents.html` — automatically grouped article library
- `about.html` — Persian biography with an English toggle
- `articles.html` — redirects old links to `contents.html`
- `content-data.js` — the only file you normally edit when adding/removing guides
- `styles.css` — shared Kooshky Editorial Signal styling
- `site.js` — shared theme, menu, article rendering, search, and language toggle
- `images/` — your portrait and score reports

## Add your images

Put the files in `images/` using these exact names:

```text
images/amir-and-ostrich.jpg
images/gre-score-report.jpg
images/toefl-score-report.jpg
```

The page has visible placeholders until the images are added. The GRE report is displayed in a wide frame; the TOEFL report is displayed in a tall frame. Neither image is cropped.

Before publishing score reports, redact any information you do not want public, including candidate or registration numbers, addresses, birth dates, barcodes, QR codes, and account identifiers.

## Add a guide

Open `content-data.js`. Inside `window.KOOSHKY_CONTENT`, add an object:

```js
{
  title: "Developing Ideas in Academic Discussion",
  href: "academic-discussion-development.html",
  section: "writing",
  summary: "A practical guide to developing reasons, examples, and consequences.",
  date: "2026-07-13",
  featured: true
}
```

- `href` can point to an old standalone note; no redesign is required.
- `section` determines where it appears on `contents.html`.
- `featured: true` also places it on the homepage.
- `featured: false` keeps it only in All Contents.
- Delete the object to remove the guide from both lists.

Available section IDs:

```text
reading
listening
speaking
writing
vocabulary
grammar
strategy
resources
```

To rename or reorder sections, edit `window.KOOSHKY_SECTIONS` in the same file.

## Publish

Upload all files and the `images` folder to the root of your GitHub Pages repository. Keep the relative filenames unchanged.
