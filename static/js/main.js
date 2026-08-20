/* Application shell.

   Owns state, wiring and side effects. Panels stay pure functions of the
   report; everything that touches the network, storage, the URL or the clock
   lives here. */

import { api } from "./core/api.js";
import { createFormatter } from "./core/format.js";
import { places } from "./core/places.js";
import {
  SCHEMA, applyToDocument, applyUnitPreset, exportSettings, importSettings,
  loadSettings, resolveAppearance, saveSettings,
} from "./core/settings.js";
import { createStore } from "./core/store.js";
import { textReport } from "./core/textreport.js";
import { renderIsobars } from "./draw/isobars.js";
import { clear, el, mount } from "./ui/dom.js";
import { createPalette } from "./ui/palette.js";
import { createSearch } from "./ui/search.js";
import { BINDINGS, installShortcuts } from "./ui/shortcuts.js";
import { toast } from "./ui/toasts.js";
import { allPanels, visiblePanels } from "./panels/registry.js";

import "./panels/core.js";
import "./panels/forecast.js";
import "./panels/environment.js";
import "./panels/tools.js";

const HIDDEN_KEY = "barograph.hidden-panels.v2";

const dom = {
  placeName: document.getElementById("place-name"),
  placeMeta: document.getElementById("place-meta"),
  notices: document.getElementById("notices"),
  grid: document.getElementById("panel-grid"),
  titleblock: document.getElementById("titleblock"),
  isobars: document.getElementById("isobar-field"),
  status: document.getElementById("live-status"),
  searchInput: document.getElementById("search-input"),
  searchResults: document.getElementById("search-results"),
  refresh: document.getElementById("btn-refresh"),
  help: document.getElementById("help-overlay"),
  paletteBackdrop: document.getElementById("palette"),
  paletteInput: document.getElementById("palette-input"),
  paletteList: document.getElementById("palette-list"),
};

function readHidden() {
  try {
    const parsed = JSON.parse(localStorage.getItem(HIDDEN_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function bootstrapReport() {
  const node = document.getElementById("initial-report");
  if (!node?.textContent?.trim()) return null;
  try {
    return JSON.parse(node.textContent);
  } catch {
    return null;
  }
}

const store = createStore({
  report: bootstrapReport(),
  comparison: null,
  settings: loadSettings(),
  hidden: readHidden(),
  loading: false,
  error: null,
  offline: !navigator.onLine,
  query: new URLSearchParams(location.search).get("q") || "",
});

let formatter = createFormatter(store.get().settings);
let refreshTimer = null;

/* ---- actions -------------------------------------------------------- */

const actions = {
  async load(query, { push = true, quiet = false } = {}) {
    if (!query) return;
    store.set({ loading: true, error: null });
    if (!quiet) announce(`Loading weather for ${query}`);
    try {
      const report = await api.report(query);
      store.set({ report, query, loading: false });
      places.pushRecent({
        label: report.place.label,
        name: report.place.name,
        query,
      });
      if (push) {
        const url = new URL(location.href);
        url.searchParams.set("q", query);
        history.pushState({ q: query }, "", url);
      }
      announce(report.advice?.summary || `Weather for ${report.place.name}`);
    } catch (error) {
      if (error.name === "AbortError") return;
      store.set({ loading: false, error });
      toast(error.message, { tone: "bad", action: { label: "Retry", run: () => actions.load(query, { push: false }) } });
    }
  },

  refresh() {
    const { report, query } = store.get();
    actions.load(query || report?.place?.name || "London", { push: false });
    toast("Refreshing", { timeout: 1500 });
  },

  locate() {
    if (!navigator.geolocation) return toast("This browser cannot share a location", { tone: "warn" });
    toast("Finding you…", { timeout: 2000 });
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        actions.load(`${latitude.toFixed(4)},${longitude.toFixed(4)}`);
      },
      (error) => toast(
        error.code === error.PERMISSION_DENIED ? "Location permission denied" : "Could not get a location fix",
        { tone: "warn" },
      ),
      { timeout: 9000, maximumAge: 300000 },
    );
  },

  toggleSave() {
    const { report } = store.get();
    if (!report) return;
    places.toggle({ label: report.place.label, name: report.place.name, query: report.place.name });
    render();
    toast(places.isSaved(report.place.label) ? "Place saved" : "Place removed");
  },

  removePlace(label) { places.remove(label); render(); },
  movePlace(label, delta) { places.move(label, delta); render(); },
  setHome(label) { places.setHome(label); render(); toast("Home place updated"); },

  async compareWith(query) {
    const { report } = store.get();
    if (!report) return;
    try {
      const payload = await api.compare([report.place.name, query]);
      store.set({ comparison: payload.reports });
      announce(`Comparing ${payload.reports.map((r) => r.place.name).join(" and ")}`);
    } catch (error) {
      toast(error.message, { tone: "bad" });
    }
  },

  clearCompare() { store.set({ comparison: null }); },

  setSetting(key, value) {
    if (!SCHEMA[key]) return;
    let next = { ...store.get().settings, [key]: value };
    if (key === "units") next = applyUnitPreset(next, value);
    commitSettings(next);
  },

  togglePanel(id) {
    const hidden = store.get().hidden;
    const next = hidden.includes(id) ? hidden.filter((x) => x !== id) : [...hidden, id];
    localStorage.setItem(HIDDEN_KEY, JSON.stringify(next));
    store.set({ hidden: next });
  },

  toggleUnits() {
    const current = store.get().settings.units;
    actions.setSetting("units", current === "metric" ? "imperial" : "metric");
    toast(`Units: ${current === "metric" ? "imperial" : "metric"}`, { timeout: 1600 });
  },

  toggleTheme() {
    const next = resolveAppearance(store.get().settings) === "draft" ? "cyanotype" : "draft";
    actions.setSetting("theme", next);
    toast(next === "draft" ? "Draft (light)" : "Cyanotype (dark)", { timeout: 1600 });
  },

  toggleDensity() {
    const current = store.get().settings.density;
    actions.setSetting("density", current === "compact" ? "comfortable" : "compact");
  },

  async copyReport() {
    const { report } = store.get();
    if (!report) return;
    const text = textReport(report, formatter);
    try {
      await navigator.clipboard.writeText(text);
      toast("Report copied as text");
    } catch {
      /* Clipboard access can be refused; showing the text still lets them copy it. */
      window.prompt("Copy the report:", text.replace(/\n/g, " | "));
    }
  },

  async share() {
    const url = location.href;
    const { report } = store.get();
    const title = report ? `Weather in ${report.place.name}` : "Barograph";
    if (navigator.share) {
      try {
        await navigator.share({ title, text: report?.advice?.summary, url });
        return;
      } catch {
        /* Cancelled share is not an error worth reporting. */
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      toast("Link copied");
    } catch {
      toast("Copy the address bar to share", { tone: "warn" });
    }
  },

  print() { window.print(); },

  exportSettings() {
    const text = exportSettings(store.get().settings);
    navigator.clipboard?.writeText(text).then(
      () => toast("Settings copied to clipboard"),
      () => window.prompt("Settings JSON:", text),
    );
  },

  importSettings() {
    const text = window.prompt("Paste settings JSON:");
    if (!text) return;
    try {
      commitSettings(importSettings(text));
      toast("Settings imported");
    } catch {
      toast("That is not valid settings JSON", { tone: "bad" });
    }
  },

  resetSettings() {
    commitSettings(Object.fromEntries(
      Object.entries(SCHEMA).map(([key, spec]) => [key, spec.default]),
    ));
    toast("Preferences reset");
  },

  toggleHelp() {
    dom.help.hidden = !dom.help.hidden;
  },
};

function commitSettings(next) {
  saveSettings(next);
  applyToDocument(next);
  syncThemeButton(next);
  formatter = createFormatter(next);
  store.set({ settings: next });
  scheduleRefresh();
}

function announce(message) {
  if (dom.status) dom.status.textContent = message;
}

/* ---- rendering -------------------------------------------------------- */

function renderMasthead(report) {
  dom.placeName.textContent = report.place.name;
  const meta = [
    report.place.label,
    `${report.place.lat.toFixed(2)}, ${report.place.lon.toFixed(2)}`,
    `Local ${formatter.clock(report.place.localtime_epoch, report)}`,
    report.place.tz_id,
  ];
  mount(dom.placeMeta, meta.filter(Boolean).map((text) => el("span", { class: "label label--quiet", text })));
  document.title = `${formatter.temp(report.current.temp_c)} ${report.current.condition.text} — ${report.place.name} · Barograph`;
}

function renderNotices(state) {
  const { report, offline, error } = state;
  const notices = [];

  if (offline) {
    notices.push(el("div", { class: "notice tone-warn" }, [
      el("span", { text: "You are offline. Showing the last data this device stored." }),
    ]));
  }
  if (error) {
    notices.push(el("div", { class: "notice tone-bad" }, [
      el("span", { text: error.message }),
      el("button", { class: "btn btn--ghost", type: "button", text: "Retry", onclick: () => actions.refresh() }),
    ]));
  }
  (report?.meta?.notices || []).forEach((text) => {
    notices.push(el("div", { class: "notice" }, [el("span", { text })]));
  });
  if (report?.meta?.stale) {
    notices.push(el("div", { class: "notice tone-warn" }, [
      el("span", { text: `Data is ${Math.round(report.meta.age_seconds / 60)} minutes old.` }),
    ]));
  }
  mount(dom.notices, notices);
}

function renderPanels(state) {
  const context = {
    report: state.report,
    comparison: state.comparison,
    settings: state.settings,
    hiddenPanels: state.hidden,
    panels: allPanels(),
    formatter,
    places,
    actions,
  };

  const nodes = visiblePanels(context, state.hidden).map((panel, index) => {
    let body;
    try {
      body = panel.render(context);
    } catch (error) {
      /* One broken panel must not take the sheet down with it. */
      console.error(`Panel "${panel.id}" failed`, error);
      body = el("div", { class: "no-data" }, [el("span", { text: "This panel could not be drawn" })]);
    }
    return el("section", {
      class: `panel span-${panel.span}`,
      id: `panel-${panel.id}`,
      "aria-labelledby": `panel-${panel.id}-title`,
    }, [
      el("header", { class: "panel__head" }, [
        el("span", { class: "panel__index", text: String(index + 1).padStart(2, "0") }),
        el("h2", { class: "panel__title label", id: `panel-${panel.id}-title`, text: panel.title }),
        panel.note ? el("span", { class: "panel__note", text: panel.note }) : null,
      ]),
      body,
    ]);
  });

  mount(dom.grid, nodes);
}

function renderTitleblock(report) {
  const meta = report.meta;
  const cells = [
    ["Sheet", `${report.place.name} · ${report.meta.forecast_days}-day`],
    ["Coordinates", `${report.place.lat.toFixed(4)}, ${report.place.lon.toFixed(4)}`],
    ["Time zone", `${report.place.tz_id} (UTC${report.place.utc_offset_hours >= 0 ? "+" : ""}${report.place.utc_offset_hours})`],
    ["Source", meta.provider === "demo" ? "Modelled demo data" : "WeatherAPI"],
    ["Issued", formatter.clock(meta.generated_epoch, report)],
    ["Cache", meta.cached ? `hit · ${Math.round(meta.age_seconds)}s old` : "miss · fresh"],
    ["Revision", `v${meta.version}`],
  ];
  mount(dom.titleblock, cells.map(([label, value]) => el("div", { class: "titleblock__cell" }, [
    el("span", { class: "label", text: label }),
    el("div", { class: "titleblock__value", text: value }),
  ])));
}

/* Masonry packing.

   A 12-column grid with panels of unequal height either leaves holes (start
   aligned) or dead space inside short panels (stretched). Measuring each
   panel and giving it a matching row span avoids both, and degrades to a
   normal grid if this never runs. */
const ROW = 4;

function layoutMasonry() {
  if (!dom.grid) return;
  const styles = getComputedStyle(dom.grid);
  const gap = parseFloat(styles.rowGap) || 16;
  const single = styles.gridTemplateColumns.split(" ").length <= 1;

  if (single) {
    dom.grid.removeAttribute("data-masonry");
    Array.from(dom.grid.children).forEach((panel) => { panel.style.gridRowEnd = ""; });
    return;
  }

  dom.grid.dataset.masonry = "on";
  const panels = Array.from(dom.grid.children);
  panels.forEach((panel) => {
    panel.style.gridRowEnd = "";
    const height = panel.getBoundingClientRect().height;
    const span = Math.max(1, Math.ceil((height + gap) / (ROW + gap)));
    panel.style.gridRowEnd = `span ${span}`;
  });
  renumber(panels);
}

/* Dense packing reorders panels on screen. A drawing's sheet numbers must read
   in the order the eye travels, so they are assigned after layout, not before. */
function renumber(panels) {
  panels
    .map((panel) => ({ panel, box: panel.getBoundingClientRect() }))
    .sort((a, b) => (Math.abs(a.box.top - b.box.top) > 8 ? a.box.top - b.box.top : a.box.left - b.box.left))
    .forEach(({ panel }, i) => {
      const index = panel.querySelector(".panel__index");
      if (index) index.textContent = String(i + 1).padStart(2, "0");
    });
}

let layoutQueued = false;
function queueLayout() {
  if (layoutQueued) return;
  layoutQueued = true;
  requestAnimationFrame(() => {
    layoutQueued = false;
    layoutMasonry();
  });
}

/* Observing the grid itself would loop: assigning row spans changes its own
   height. Only a change in available width can change the packing. */
let lastWidth = 0;
function observeWidth(node) {
  new ResizeObserver((entries) => {
    const width = Math.round(entries[0].contentRect.width);
    if (width === lastWidth) return;
    lastWidth = width;
    queueLayout();
  }).observe(node);
}

function render() {
  const state = store.get();
  if (!state.report) return;
  renderMasthead(state.report);
  renderNotices(state);
  renderPanels(state);
  renderTitleblock(state.report);
  renderIsobars(dom.isobars, state.report, { enabled: state.settings.isobars === "on" });
  document.body.dataset.loading = String(state.loading);
  queueLayout();
}

/* ---- commands ---------------------------------------------------------- */

function commands() {
  const state = store.get();
  const list = [
    { label: "Refresh now", hint: "R", run: actions.refresh },
    { label: "Use my location", hint: "L", run: actions.locate },
    { label: "Copy report as text", hint: "C", run: actions.copyReport },
    { label: "Share this view", run: actions.share },
    { label: "Print sheet", hint: "P", run: actions.print },
    { label: "Toggle units", hint: "U", detail: state.settings.units, run: actions.toggleUnits },
    { label: "Toggle light / dark", hint: "T", keywords: "theme cyanotype draft",
      detail: resolveAppearance(state.settings), run: actions.toggleTheme },
    { label: "Toggle density", hint: "D", detail: state.settings.density, run: actions.toggleDensity },
    { label: "Toggle high contrast", run: () => actions.setSetting("contrast", state.settings.contrast === "high" ? "normal" : "high") },
    { label: "Toggle isobar field", run: () => actions.setSetting("isobars", state.settings.isobars === "on" ? "off" : "on") },
    { label: "Keyboard shortcuts", hint: "?", run: actions.toggleHelp },
  ];

  places.all().saved.forEach((place) => list.push({
    label: `Go to ${place.label}`, keywords: "place saved", run: () => actions.load(place.query || place.label),
  }));
  places.all().recent.forEach((place) => list.push({
    label: `Recent: ${place.label}`, keywords: "place recent", run: () => actions.load(place.query || place.label),
  }));
  places.all().saved.forEach((place) => list.push({
    label: `Compare with ${place.name}`, keywords: "compare", run: () => actions.compareWith(place.query || place.label),
  }));

  allPanels().forEach((panel) => list.push({
    label: `${state.hidden.includes(panel.id) ? "Show" : "Hide"} panel: ${panel.title}`,
    keywords: "panel layout",
    run: () => actions.togglePanel(panel.id),
  }));

  return list;
}

/* ---- refresh scheduling -------------------------------------------------- */

function scheduleRefresh() {
  clearInterval(refreshTimer);
  const seconds = Number(store.get().settings.refresh);
  if (!seconds) return;
  refreshTimer = setInterval(() => {
    if (document.visibilityState === "visible" && navigator.onLine) {
      actions.load(store.get().query || store.get().report?.place?.name, { push: false, quiet: true });
    }
  }, seconds * 1000);
}

/* ---- help overlay --------------------------------------------------------- */

function renderHelp() {
  const body = document.getElementById("help-body");
  if (!body) return;
  const seen = new Set();
  const rows = BINDINGS.filter((b) => !seen.has(b.id) && seen.add(b.id)).map((b) => el("div", { class: "log__row" }, [
    el("span", { class: "log__key", text: b.label }),
    el("kbd", { class: "kbd", text: b.modifier ? `${b.modifier === "meta" ? "⌘" : "Ctrl"}+${b.keys[0]}` : b.keys[0] }),
  ]));
  mount(body, [el("div", { class: "log" }, rows)]);
}

/* ---- boot ------------------------------------------------------------------ */

function syncThemeButton(settings) {
  const button = document.getElementById("btn-theme");
  if (!button) return;
  const showing = resolveAppearance(settings);
  const other = showing === "draft" ? "dark" : "light";
  button.textContent = showing === "draft" ? "Light" : "Dark";
  button.setAttribute("aria-label", `Theme: ${showing}. Switch to ${other}.`);
  button.title = `Showing ${showing}. Click for ${other} (T)`;
  button.dataset.appearance = showing;
}

function boot() {
  applyToDocument(store.get().settings);
  syncThemeButton(store.get().settings);

  const palette = createPalette({
    backdrop: dom.paletteBackdrop,
    input: dom.paletteInput,
    list: dom.paletteList,
    getCommands: commands,
  });

  createSearch({
    input: dom.searchInput,
    results: dom.searchResults,
    onSelect: (item) => {
      const query = item.lat !== null && item.lat !== undefined
        ? `${item.lat},${item.lon}`
        : item.name;
      actions.load(query);
    },
  });

  document.getElementById("search-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = dom.searchInput.value.trim();
    if (value) actions.load(value);
  });

  dom.refresh?.addEventListener("click", () => actions.refresh());
  document.getElementById("btn-palette")?.addEventListener("click", () => palette.open());
  document.getElementById("btn-theme")?.addEventListener("click", () => actions.toggleTheme());
  document.getElementById("btn-units")?.addEventListener("click", () => actions.toggleUnits());
  document.getElementById("btn-share")?.addEventListener("click", () => actions.share());
  document.getElementById("btn-help")?.addEventListener("click", () => actions.toggleHelp());
  document.getElementById("help-close")?.addEventListener("click", () => actions.toggleHelp());

  installShortcuts({
    search: () => dom.searchInput.focus(),
    palette: () => palette.open(),
    refresh: () => actions.refresh(),
    units: () => actions.toggleUnits(),
    theme: () => actions.toggleTheme(),
    density: () => actions.toggleDensity(),
    copy: () => actions.copyReport(),
    save: () => actions.toggleSave(),
    locate: () => actions.locate(),
    print: () => actions.print(),
    help: () => actions.toggleHelp(),
    escape: () => {
      palette.close();
      dom.help.hidden = true;
    },
  });

  window.addEventListener("popstate", () => {
    const query = new URLSearchParams(location.search).get("q");
    if (query) actions.load(query, { push: false });
  });

  window.addEventListener("online", () => {
    store.set({ offline: false });
    toast("Back online", { tone: "ok", timeout: 2000 });
    actions.refresh();
  });
  window.addEventListener("offline", () => {
    store.set({ offline: true });
    toast("Offline — showing stored data", { tone: "warn" });
  });

  store.subscribe(render);
  renderHelp();
  render();

  /* Fonts settle after first paint and change panel heights. */
  document.fonts?.ready.then(queueLayout);
  observeWidth(dom.grid);
  scheduleRefresh();

  /* A home place beats the server's default on a bare visit. */
  const saved = places.all();
  const bare = !new URLSearchParams(location.search).get("q");
  if (bare && saved.home) actions.load(saved.home, { push: false, quiet: true });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* Offline support is an enhancement; failing to register is survivable. */
    });
  }
}

boot();
