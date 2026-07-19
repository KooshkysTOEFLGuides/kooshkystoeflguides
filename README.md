# Apps section update

## Replace these files in the repository root

- `index.html`
- `contents.html`
- `about.html`
- `word-of-the-day.html`
- `styles.css`
- `site.js`

## Add these files in the repository root

- `apps.html`
- `apps-data.js`
- `APP_STYLE_PROMPT.md` (reference prompt; it does not need to be public)

## Put this script inside `WordOfTheDay/`

- `generate_word_audio.py`

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
