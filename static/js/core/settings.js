/* Persisted preferences.

   Declared as a schema so the command palette, the settings panel and the
   import/export round trip all read the same definition instead of three
   hand-maintained lists. */

const KEY = "barograph.settings.v2";

export const SCHEMA = {
  theme: { default: "auto", options: ["auto", "cyanotype", "draft"], label: "Theme" },
  units: { default: "metric", options: ["metric", "imperial"], label: "Units" },
  temperature: { default: "c", options: ["c", "f"], label: "Temperature" },
  wind: { default: "kph", options: ["kph", "mph", "ms", "kn", "bft"], label: "Wind speed" },
  pressure: { default: "mb", options: ["mb", "inhg", "mmhg"], label: "Pressure" },
  precip: { default: "mm", options: ["mm", "in"], label: "Precipitation" },
  distance: { default: "km", options: ["km", "mi"], label: "Distance" },
  clock: { default: "24", options: ["24", "12"], label: "Clock" },
  density: { default: "comfortable", options: ["comfortable", "compact"], label: "Density" },
  contrast: { default: "normal", options: ["normal", "high"], label: "Contrast" },
  motion: { default: "system", options: ["system", "on", "off"], label: "Motion" },
  isobars: { default: "on", options: ["on", "off"], label: "Isobar field" },
  refresh: { default: "600", options: ["0", "300", "600", "1800"], label: "Auto refresh" },
  indoor: { default: "21", options: ["18", "19", "20", "21", "22", "23"], label: "Indoor temperature" },
};

const UNIT_PRESETS = {
  metric: { temperature: "c", wind: "kph", pressure: "mb", precip: "mm", distance: "km" },
  imperial: { temperature: "f", wind: "mph", pressure: "inhg", precip: "in", distance: "mi" },
};

function defaults() {
  return Object.fromEntries(Object.entries(SCHEMA).map(([key, spec]) => [key, spec.default]));
}

export function loadSettings() {
  const base = defaults();
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) || "{}");
    for (const [key, value] of Object.entries(stored)) {
      if (SCHEMA[key] && SCHEMA[key].options.includes(String(value))) base[key] = String(value);
    }
  } catch {
    /* Corrupt storage should reset preferences, not break the page. */
  }
  return base;
}

export function saveSettings(settings) {
  try {
    localStorage.setItem(KEY, JSON.stringify(settings));
  } catch {
    /* Private browsing can refuse writes; preferences are not worth failing over. */
  }
}

export function applyUnitPreset(settings, preset) {
  return { ...settings, units: preset, ...(UNIT_PRESETS[preset] || {}) };
}

/* "auto" is not a look, it is a deferral to the OS. Anything that needs to
   know what is actually on screen - the toggle, the button label - has to
   resolve it, or it will offer a switch to the theme already showing. */
export function systemAppearance() {
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "draft" : "cyanotype";
}

export function resolveAppearance(settings) {
  return settings.theme === "auto" ? systemAppearance() : settings.theme;
}

/* Only meaningful while theme is "auto"; the callback re-applies so the page
   follows an OS switch instead of waiting for a reload. */
export function watchSystemAppearance(onChange) {
  const query = window.matchMedia?.("(prefers-color-scheme: light)");
  if (!query) return () => {};
  const handler = () => onChange(systemAppearance());
  query.addEventListener("change", handler);
  return () => query.removeEventListener("change", handler);
}

export function applyToDocument(settings) {
  const root = document.documentElement;
  if (settings.theme === "auto") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", settings.theme);
  const appearance = resolveAppearance(settings);
  root.setAttribute("data-appearance", appearance);
  /* Two media-scoped theme-color tags handle "auto" with no JS. An explicit
     theme has to override both, or the browser chrome keeps following the OS. */
  const DARK = "#0a1a2f";
  const LIGHT = "#eef3f8";
  document.querySelectorAll('meta[name="theme-color"]').forEach((tag) => {
    const wantsLight = (tag.getAttribute("media") || "").includes("light");
    tag.setAttribute("content", settings.theme === "auto"
      ? (wantsLight ? LIGHT : DARK)
      : (appearance === "draft" ? LIGHT : DARK));
  });
  root.setAttribute("data-density", settings.density);
  root.setAttribute("data-contrast", settings.contrast);
  if (settings.motion === "system") root.removeAttribute("data-motion");
  else root.setAttribute("data-motion", settings.motion);
}

export function exportSettings(settings) {
  return JSON.stringify(settings, null, 2);
}

export function importSettings(text) {
  const parsed = JSON.parse(text);
  const base = defaults();
  for (const [key, value] of Object.entries(parsed)) {
    if (SCHEMA[key] && SCHEMA[key].options.includes(String(value))) base[key] = String(value);
  }
  return base;
}
