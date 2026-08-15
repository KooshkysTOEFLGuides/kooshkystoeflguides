# Word of the Day section

The public archive is self-contained in `WordOfTheDay/`:

- `index.html`
- `word-data.js`
- `word-of-the-day.js`
- `word-of-the-day.css`
- `schedule-preview-7c4a91e2f6.html`

The root `word-of-the-day.html` is intentionally retained as a small redirect so
old bookmarks and external links keep working. The archive reuses the site's
existing `styles.css`, `site.js`, and `images/` files one directory above it.

## Add a word

Edit `word-data.js` and add an object inside `window.KOOSHKY_WORDS`:

```js
{
  word: "Meticulous",
  date: "2026-07-17",
  href: "WordOfTheDay/generated/meticulous-extended.html",
  partOfSpeech: "adjective",
  summary: "Very careful and attentive to small details."
}
```

Every word page belongs in `generated/` and uses the filename format
`word-extended.html`. Separate entries with commas. Dates may be skipped. The
archive groups whatever exists by month.

Registry paths are root-relative strings because the same `word-data.js` also
drives the homepage card. The archive and schedule pages apply their `../`
prefix when rendering those links.

## Publication timing

The public page reveals an entry at 10:00 AM in `Asia/Tehran` on its date. It rechecks once a minute, when the tab becomes active, and when the browser window regains focus.

## Private preview limitation

The preview page is not linked anywhere and asks search engines not to index it. However, GitHub Pages is a static site. If `word-data.js` is deployed publicly, a technically knowledgeable visitor can inspect that file and see scheduled entries. Client-side JavaScript can hide future words from the normal interface, but it cannot make public source data truly secret.
