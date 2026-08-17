# Apps section update

## Main site files

- `index.html`
- `contents.html`
- `about.html`
- `word-of-the-day.html` (compatibility redirect to `WordOfTheDay/index.html`)
- `styles.css`
- `site.js`

## Add these files in the repository root

- `apps.html`
- `apps-data.js`
- `AGENTS.md` (repository-wide instructions for article, app, brand, and deployment work; it does not need to be public)

## Word of the Day files

The archive, registry, scripts, source JSON, and generated pages are all kept in
`WordOfTheDay/`. See `WordOfTheDay/README.md` and
`WordOfTheDay/README-ARCHIVE.md` for the publishing workflow.

## Add an app

Edit `apps-data.js`:

```js
{
  name: "Listen and Repeat Simulator",
  href: "Apps/ListenAndRepeat/index.html",
  description: "Practise TOEFL Listen and Repeat sets and review your recordings.",
  logo: "Apps/ListenAndRepeat/icon.png",
  featured: true
}
```

`logo` is optional. `featured: true` also places the app on the homepage.
