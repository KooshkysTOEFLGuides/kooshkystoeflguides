(() => {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const themeKey = "kooshky-guides:theme:v1";

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
      if (window.innerWidth > 760 && !panel.hidden) {
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

  const MAX_PUBLICATION_TIMEOUT = 2_147_000_000;
  const invalidPublishTimes = new Set();
  let publicationTimer = null;

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

    // Entries without publishAt are immediately available.
    if (timestamp === null) {
      return true;
    }

    // Invalid values remain hidden.
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
          `${item.title} ${item.summary || ""} ${section}`.toLowerCase()
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

    // The order remains the same as content-data.js.
    const items = getPublishedContent().filter(
      (item) => item.featured
    );

    if (!items.length) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No featured guides yet.</h3>
          <p>
            Add an item to <code>content-data.js</code>
            and set <code>featured: true</code>.
          </p>
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

    // The order remains the same as content-data.js.
    const items = getPublishedContent();
    const sections = window.KOOSHKY_SECTIONS || [];
    const searchWrap = document.querySelector("[data-search-wrap]");

    if (!items.length) {
      if (searchWrap) {
        searchWrap.hidden = true;
      }

      container.innerHTML = `
        <div class="empty-state empty-state-large">
          <h2>No guides have been listed yet.</h2>
          <p>Add entries to <code>content-data.js</code>.</p>
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
          <section
            class="content-group"
            data-content-group
          >
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
          <section
            class="content-group"
            data-content-group
          >
            <div class="group-heading">
              <h2>Other</h2>

              <span class="count">
                ${ungrouped.length}
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

    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
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
    });

    if (status) {
      status.textContent = `${items.length} total guides`;
    }
  }

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
    scheduleNextPublicationRefresh();
    initLanguageToggle();
    initImageFallbacks();
  });
})();