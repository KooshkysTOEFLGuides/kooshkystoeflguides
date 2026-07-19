(() => {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const themeKey = "kooshky-guides:theme:v1";
  const MAX_PUBLICATION_TIMEOUT = 2_147_000_000;

  const invalidPublishTimes = new Set();
  let publicationTimer = null;

  const safeStorage = {
    get(key) {
      try {
        return localStorage.getItem(key);
      } catch (_) {
        return null;
      }
    },

    set(key, value) {
      try {
        localStorage.setItem(key, value);
      } catch (_) {}
    }
  };

  function updateThemeAssets(theme) {
    const dark = theme === "dark";

    document.querySelectorAll("[data-favicon]").forEach((link) => {
      link.href = dark
        ? link.dataset.darkHref
        : link.dataset.lightHref;
    });

    const themeColor = document.querySelector('meta[name="theme-color"]');

    if (themeColor) {
      themeColor.content = dark ? "#111417" : "#F4F0E8";
    }
  }

  function setTheme(theme, { save = true } = {}) {
    const normalized = theme === "dark" ? "dark" : "light";

    root.dataset.theme = normalized;
    root.style.colorScheme = normalized;

    if (save) {
      safeStorage.set(themeKey, normalized);
    }

    updateThemeAssets(normalized);

    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      const dark = normalized === "dark";

      button.setAttribute("aria-pressed", String(dark));
      button.setAttribute(
        "aria-label",
        dark ? "Use light theme" : "Use dark theme"
      );

      const text = button.querySelector("[data-theme-label]");

      if (text) {
        text.textContent = dark ? "Light" : "Dark";
      }
    });

    window.dispatchEvent(
      new CustomEvent("kooshkythemechange", {
        detail: {
          theme: normalized,
          storageKey: themeKey
        }
      })
    );
  }

  function initTheme() {
    const saved = safeStorage.get(themeKey);

    // A missing or invalid value defaults to light mode.
    setTheme(saved === "dark" ? "dark" : "light", {
      save: saved === "light" || saved === "dark"
    });

    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        setTheme(
          root.dataset.theme === "dark"
            ? "light"
            : "dark"
        );
      });
    });

    window.addEventListener("storage", (event) => {
      if (
        event.key === themeKey &&
        (event.newValue === "light" || event.newValue === "dark")
      ) {
        setTheme(event.newValue, { save: false });
      }
    });
  }

  window.KOOSHKY_THEME = {
    storageKey: themeKey,

    get: () =>
      safeStorage.get(themeKey) ||
      root.dataset.theme ||
      "light",

    set: (theme) => setTheme(theme)
  };

  function initMenu() {
    const button = document.querySelector("[data-menu-toggle]");
    const panel = document.querySelector("[data-mobile-nav]");
    const backdrop = document.querySelector("[data-nav-backdrop]");

    if (!button || !panel || !backdrop) {
      return;
    }

    const close = () => {
      panel.hidden = true;
      backdrop.hidden = true;
      button.setAttribute("aria-expanded", "false");
      body.classList.remove("menu-open");
    };

    const open = () => {
      panel.hidden = false;
      backdrop.hidden = false;
      button.setAttribute("aria-expanded", "true");
      body.classList.add("menu-open");
      panel.querySelector("a")?.focus();
    };

    button.addEventListener("click", () => {
      panel.hidden ? open() : close();
    });

    backdrop.addEventListener("click", close);

    panel.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", close);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !panel.hidden) {
        close();
        button.focus();
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 920 && !panel.hidden) {
        close();
      }
    });
  }

  function escapeHTML(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function normalizeSearchText(value) {
    return String(value || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("en")
      .trim();
  }

  function formatDate(value) {
    if (!value) {
      return "";
    }

    const date = new Date(`${value}T12:00:00`);

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat("en", {
      year: "numeric",
      month: "short",
      day: "numeric"
    }).format(date);
  }

  // ---------------------------------------------------------------------------
  // Scheduled article publication
  // ---------------------------------------------------------------------------

  function getPublishTimestamp(item) {
    if (!item.publishAt) {
      return null;
    }

    const timestamp = Date.parse(item.publishAt);

    if (Number.isNaN(timestamp)) {
      const identifier =
        item.title ||
        item.href ||
        String(item.publishAt);

      if (!invalidPublishTimes.has(identifier)) {
        invalidPublishTimes.add(identifier);

        console.warn(
          `Hidden item because publishAt is invalid: ${identifier}`,
          item.publishAt
        );
      }

      return Number.NaN;
    }

    return timestamp;
  }

  function isPublished(item, now = Date.now()) {
    const timestamp = getPublishTimestamp(item);

    if (timestamp === null) {
      return true;
    }

    if (Number.isNaN(timestamp)) {
      return false;
    }

    return timestamp <= now;
  }

  function getPublishedContent(now = Date.now()) {
    return (window.KOOSHKY_CONTENT || []).filter((item) =>
      isPublished(item, now)
    );
  }

  function getNextPublicationTime(now = Date.now()) {
    let next = Infinity;

    for (const item of window.KOOSHKY_CONTENT || []) {
      const timestamp = getPublishTimestamp(item);

      if (
        timestamp !== null &&
        !Number.isNaN(timestamp) &&
        timestamp > now &&
        timestamp < next
      ) {
        next = timestamp;
      }
    }

    return Number.isFinite(next) ? next : null;
  }

  function scheduleNextPublicationRefresh() {
    if (publicationTimer !== null) {
      clearTimeout(publicationTimer);
      publicationTimer = null;
    }

    const now = Date.now();
    const next = getNextPublicationTime(now);

    if (next === null) {
      return;
    }

    const delay = Math.min(
      Math.max(next - now + 250, 250),
      MAX_PUBLICATION_TIMEOUT
    );

    publicationTimer = window.setTimeout(() => {
      if (Date.now() >= next) {
        window.location.reload();
      } else {
        scheduleNextPublicationRefresh();
      }
    }, delay);
  }

  window.KOOSHKY_PUBLICATION = {
    isPublished,
    getPublishedContent,
    next: () => getNextPublicationTime(),
    now: () => new Date()
  };

  // ---------------------------------------------------------------------------
  // Guides
  // ---------------------------------------------------------------------------

  function articleMarkup(item) {
    const sections = window.KOOSHKY_SECTIONS || [];

    const section =
      sections.find((entry) => entry.id === item.section)?.label ||
      item.section ||
      "Guide";

    return `
      <article
        class="article-entry"
        data-search-text="${escapeHTML(
          normalizeSearchText(
            `${item.title} ${item.summary || ""} ${section}`
          )
        )}"
      >
        <div class="article-meta">
          <span>${escapeHTML(section)}</span>

          ${
            item.date
              ? `
                <time datetime="${escapeHTML(item.date)}">
                  ${escapeHTML(formatDate(item.date))}
                </time>
              `
              : ""
          }
        </div>

        <h3>
          <a href="${escapeHTML(item.href)}">
            ${escapeHTML(item.title)}
          </a>
        </h3>

        ${
          item.summary
            ? `<p>${escapeHTML(item.summary)}</p>`
            : ""
        }

        <a class="text-link" href="${escapeHTML(item.href)}">
          Open guide <span aria-hidden="true">→</span>
        </a>
      </article>
    `;
  }

  function initFeatured() {
    const container = document.querySelector("[data-featured-list]");

    if (!container) {
      return;
    }

    const items = getPublishedContent().filter(
      (item) => item.featured
    );

    if (!items.length) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No featured guides yet.</h3>
        </div>
      `;

      return;
    }

    container.innerHTML = items.map(articleMarkup).join("");
  }

  function initContents() {
    const container = document.querySelector("[data-content-library]");

    if (!container) {
      return;
    }

    const items = getPublishedContent();
    const sections = window.KOOSHKY_SECTIONS || [];
    const searchWrap = document.querySelector("[data-search-wrap]");

    if (!items.length) {
      if (searchWrap) {
        searchWrap.hidden = true;
      }

      container.innerHTML = `
        <div class="empty-state empty-state-large">
          <h2>No guides have been published yet.</h2>
        </div>
      `;

      return;
    }

    const html = sections
      .map((section) => {
        const group = items.filter(
          (item) => item.section === section.id
        );

        if (!group.length) {
          return "";
        }

        return `
          <section class="content-group" data-content-group>
            <div class="group-heading">
              <h2>${escapeHTML(section.label)}</h2>
              <span class="count">
                ${group.length}
                ${group.length === 1 ? "guide" : "guides"}
              </span>
            </div>

            <div class="article-list">
              ${group.map(articleMarkup).join("")}
            </div>
          </section>
        `;
      })
      .join("");

    const ungrouped = items.filter(
      (item) =>
        !sections.some(
          (section) => section.id === item.section
        )
    );

    container.innerHTML =
      html +
      (ungrouped.length
        ? `
          <section class="content-group" data-content-group>
            <div class="group-heading">
              <h2>Other</h2>
              <span class="count">
                ${ungrouped.length}
                ${ungrouped.length === 1 ? "guide" : "guides"}
              </span>
            </div>

            <div class="article-list">
              ${ungrouped.map(articleMarkup).join("")}
            </div>
          </section>
        `
        : "");

    const input = document.querySelector("[data-content-search]");
    const status = document.querySelector("[data-search-status]");

    if (!input) {
      return;
    }

    const applySearch = () => {
      const query = normalizeSearchText(input.value);
      let visible = 0;

      document
        .querySelectorAll(".article-entry[data-search-text]")
        .forEach((entry) => {
          const match =
            !query ||
            entry.dataset.searchText.includes(query);

          entry.hidden = !match;

          if (match) {
            visible += 1;
          }
        });

      document
        .querySelectorAll("[data-content-group]")
        .forEach((group) => {
          group.hidden = !group.querySelector(
            ".article-entry:not([hidden])"
          );
        });

      if (status) {
        status.textContent = query
          ? `${visible} matching ${
              visible === 1 ? "guide" : "guides"
            }`
          : `${items.length} total guides`;
      }
    };

    input.addEventListener("input", applySearch);
    applySearch();
  }

  // ---------------------------------------------------------------------------
  // Apps
  // ---------------------------------------------------------------------------

  function normalizeApps(rawApps) {
    const valid = [];

    (Array.isArray(rawApps) ? rawApps : []).forEach((raw, index) => {
      const name = String(raw?.name || "").trim();
      const href = String(raw?.href || "").trim();
      const description = String(raw?.description || "").trim();
      const logo = String(raw?.logo || "").trim();

      if (!name || !href || !description) {
        console.warn(`Skipped invalid app at index ${index}.`, raw);
        return;
      }

      valid.push({
        name,
        href,
        description,
        logo,
        featured: raw.featured === true,
        searchText: normalizeSearchText(`${name} ${description}`)
      });
    });

    return valid;
  }

  function appLogoMarkup(item) {
    if (!item.logo) {
      return `
        <div class="app-card-icon" aria-hidden="true">
          <span class="app-default-logo"></span>
        </div>
      `;
    }

    return `
      <div class="app-card-icon" aria-hidden="true">
        <img
          src="${escapeHTML(item.logo)}"
          alt=""
          data-app-logo
        >
        <span class="app-default-logo" data-app-logo-fallback hidden></span>
      </div>
    `;
  }

  function appMarkup(item) {
    return `
      <article
        class="app-card"
        data-app-entry
        data-search-text="${escapeHTML(item.searchText)}"
      >
        ${appLogoMarkup(item)}

        <h3>
          <a href="${escapeHTML(item.href)}">
            ${escapeHTML(item.name)}
          </a>
        </h3>

        <p>${escapeHTML(item.description)}</p>

        <a class="text-link" href="${escapeHTML(item.href)}">
          Open app <span aria-hidden="true">→</span>
        </a>
      </article>
    `;
  }

  function activateAppLogoFallbacks(scope = document) {
    scope.querySelectorAll("img[data-app-logo]").forEach((image) => {
      const showFallback = () => {
        image.hidden = true;
        const fallback = image.parentElement?.querySelector(
          "[data-app-logo-fallback]"
        );

        if (fallback) {
          fallback.hidden = false;
        }
      };

      image.addEventListener("error", showFallback, { once: true });

      if (
        image.complete &&
        image.naturalWidth === 0
      ) {
        showFallback();
      }
    });
  }

  function initFeaturedApps() {
    const container = document.querySelector("[data-featured-apps]");

    if (!container) {
      return;
    }

    const items = normalizeApps(window.KOOSHKY_APPS).filter(
      (item) => item.featured
    );

    if (!items.length) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No featured apps yet.</h3>
        </div>
      `;

      return;
    }

    container.innerHTML = items.map(appMarkup).join("");
    activateAppLogoFallbacks(container);
  }

  function initAppsLibrary() {
    const container = document.querySelector("[data-app-library]");

    if (!container) {
      return;
    }

    const items = normalizeApps(window.KOOSHKY_APPS);
    const searchWrap = document.querySelector("[data-app-search-wrap]");
    const input = document.querySelector("[data-app-search]");
    const status = document.querySelector("[data-app-search-status]");

    if (!items.length) {
      if (searchWrap) {
        searchWrap.hidden = true;
      }

      container.innerHTML = `
        <div class="empty-state empty-state-large">
          <h2>No apps have been added yet.</h2>
        </div>
      `;

      return;
    }

    container.innerHTML = items.map(appMarkup).join("");
    activateAppLogoFallbacks(container);

    const applySearch = () => {
      const query = normalizeSearchText(input?.value);
      let visible = 0;

      container
        .querySelectorAll("[data-app-entry]")
        .forEach((entry) => {
          const match =
            !query ||
            entry.dataset.searchText.includes(query);

          entry.hidden = !match;

          if (match) {
            visible += 1;
          }
        });

      if (status) {
        status.textContent = query
          ? `${visible} matching ${
              visible === 1 ? "app" : "apps"
            }`
          : `${items.length} total ${
              items.length === 1 ? "app" : "apps"
            }`;
      }
    };

    input?.addEventListener("input", applySearch);
    applySearch();
  }

  // ---------------------------------------------------------------------------
  // Homepage Word of the Day
  // ---------------------------------------------------------------------------

  function parseISODate(value) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(
      String(value || "")
    );

    if (!match) {
      return null;
    }

    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const date = new Date(Date.UTC(year, month - 1, day));

    if (
      date.getUTCFullYear() !== year ||
      date.getUTCMonth() !== month - 1 ||
      date.getUTCDate() !== day
    ) {
      return null;
    }

    return {
      iso: `${match[1]}-${match[2]}-${match[3]}`,
      year,
      month,
      day,
      date,
      dayKey: year * 10000 + month * 100 + day
    };
  }

  function getWotdSettings() {
    return {
      timeZone: "Asia/Tehran",
      publishHour: 10,
      ...(window.KOOSHKY_WOTD_SETTINGS || {})
    };
  }

  function getZonedNow(timeZone) {
    const formatter = new Intl.DateTimeFormat(
      "en-US-u-ca-gregory-nu-latn",
      {
        timeZone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hourCycle: "h23"
      }
    );

    const parts = Object.fromEntries(
      formatter
        .formatToParts(new Date())
        .filter((part) => part.type !== "literal")
        .map((part) => [part.type, Number(part.value)])
    );

    return {
      ...parts,
      dayKey:
        parts.year * 10000 +
        parts.month * 100 +
        parts.day
    };
  }

  function getLatestPublishedWord() {
    const settings = getWotdSettings();
    const now = getZonedNow(settings.timeZone);
    const valid = [];

    (Array.isArray(window.KOOSHKY_WORDS)
      ? window.KOOSHKY_WORDS
      : []
    ).forEach((raw, index) => {
      const word = String(raw?.word || "").trim();
      const href = String(raw?.href || "").trim();
      const parsedDate = parseISODate(raw?.date);

      if (!word || !href || !parsedDate) {
        console.warn(
          `Skipped invalid homepage Word of the Day entry at index ${index}.`,
          raw
        );
        return;
      }

      const published =
        parsedDate.dayKey < now.dayKey ||
        (
          parsedDate.dayKey === now.dayKey &&
          now.hour >= Number(settings.publishHour)
        );

      if (published) {
        valid.push({
          word,
          href,
          date: parsedDate.iso,
          parsedDate
        });
      }
    });

    valid.sort((a, b) => {
      const dateOrder = b.date.localeCompare(a.date);

      if (dateOrder !== 0) {
        return dateOrder;
      }

      return a.word.localeCompare(
        b.word,
        "en",
        { sensitivity: "base" }
      );
    });

    return valid[0] || null;
  }

  function renderHomeWord() {
    const container = document.querySelector("[data-home-wotd]");

    if (!container) {
      return;
    }

    const item = getLatestPublishedWord();

    if (!item) {
      container.innerHTML = `
        <span class="home-wotd-label">Word of the Day</span>
        <span class="home-wotd-empty">No published word yet.</span>
        <a class="home-wotd-open" href="word-of-the-day.html">
          Open archive →
        </a>
      `;

      return;
    }

    const formattedDate = new Intl.DateTimeFormat("en", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
      timeZone: "UTC"
    }).format(item.parsedDate.date);

    container.innerHTML = `
      <span class="home-wotd-label">Word of the Day</span>

      <p class="home-wotd-word">
        <a href="${escapeHTML(item.href)}">
          ${escapeHTML(item.word)}
        </a>
      </p>

      <time
        class="home-wotd-date"
        datetime="${escapeHTML(item.date)}"
      >
        ${escapeHTML(formattedDate)}
      </time>

      <a class="home-wotd-open" href="word-of-the-day.html">
        Full archive →
      </a>
    `;
  }

  function initHomeWord() {
    if (!document.querySelector("[data-home-wotd]")) {
      return;
    }

    renderHomeWord();

    window.setInterval(renderHomeWord, 60_000);

    window.addEventListener("focus", renderHomeWord);

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        renderHomeWord();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // About page and generic image fallbacks
  // ---------------------------------------------------------------------------

  function initLanguageToggle() {
    const button = document.querySelector(
      "[data-language-toggle]"
    );

    const fa = document.querySelector(
      "[data-language-panel='fa']"
    );

    const en = document.querySelector(
      "[data-language-panel='en']"
    );

    const header = document.querySelector(
      "[data-about-header]"
    );

    const title = document.querySelector(
      "[data-about-title]"
    );

    const intro = document.querySelector(
      "[data-about-intro]"
    );

    if (
      !button ||
      !fa ||
      !en ||
      !header ||
      !title ||
      !intro
    ) {
      return;
    }

    const copy = {
      en: {
        title: "About Me",
        intro:
          "My scores, academic background, and how I ended up teaching English.",
        button: "فارسی",
        buttonLabel: "Read this page in Persian"
      },

      fa: {
        title: "درباره من",
        intro:
          "نمره‌ها، سابقه دانشگاهی و مسیری که باعث شد تدریس زبان را شروع کنم.",
        button: "Read in English",
        buttonLabel: "Read this page in English"
      }
    };

    function show(language) {
      const persian = language === "fa";

      en.hidden = persian;
      fa.hidden = !persian;

      header.lang = language;
      header.dir = persian ? "rtl" : "ltr";

      title.textContent = copy[language].title;
      intro.textContent = copy[language].intro;

      button.textContent = copy[language].button;

      button.setAttribute(
        "aria-label",
        copy[language].buttonLabel
      );

      button.setAttribute(
        "aria-pressed",
        String(persian)
      );

      button.dataset.currentLanguage = language;
    }

    show("en");

    button.addEventListener("click", () => {
      show(
        button.dataset.currentLanguage === "en"
          ? "fa"
          : "en"
      );
    });
  }

  function initImageFallbacks() {
    document
      .querySelectorAll("img[data-fallback]")
      .forEach((image) => {
        const showFallback = () => {
          image.hidden = true;

          const fallback = document.getElementById(
            image.dataset.fallback
          );

          if (fallback) {
            fallback.hidden = false;
          }
        };

        image.addEventListener(
          "error",
          showFallback,
          { once: true }
        );

        if (
          image.complete &&
          image.naturalWidth === 0
        ) {
          showFallback();
        }
      });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initMenu();
    initFeatured();
    initContents();
    initFeaturedApps();
    initAppsLibrary();
    initHomeWord();
    scheduleNextPublicationRefresh();
    initLanguageToggle();
    initImageFallbacks();
  });
})();
