/* Persisted preferences.

   Declared as a schema so the command palette, the settings panel and the
   import/export round trip all read the same definition instead of three
   hand-maintained lists. */

const KEY = "barograph.settings.v2";

export const SCHEMA = {
  theme: { default: "cyanotype", options: ["cyanotype", "draft"], label: "Theme" },
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
  /* Nothing stored yet means a first visit, so start from the OS preference
     rather than imposing dark on someone running a light desktop. */
  let seeded = false;
  try {
    const raw = localStorage.getItem(KEY);
    seeded = raw !== null;
    const stored = JSON.parse(raw || "{}");
    for (const [key, value] of Object.entries(stored)) {
      if (SCHEMA[key] && SCHEMA[key].options.includes(String(value))) base[key] = String(value);
    }
  } catch {
    /* Corrupt storage should reset preferences, not break the page. */
  }
  if (!seeded) base.theme = systemAppearance();
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

export function systemAppearance() {
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "draft" : "cyanotype";
}

/* The theme is exactly what is stored: two states, no third that resolves to
   one of the other two depending on the machine. */
export function resolveAppearance(settings) {
  return settings.theme === "draft" ? "draft" : "cyanotype";
}

export function applyToDocument(settings) {
  const root = document.documentElement;
  const appearance = resolveAppearance(settings);
  root.setAttribute("data-theme", appearance);
  root.setAttribute("data-appearance", appearance);
  /* Both media-scoped tags get the chosen colour, or browser chrome keeps
     following the OS after an explicit choice. */
  const chrome = appearance === "draft" ? "#eef3f8" : "#0a1a2f";
  document.querySelectorAll('meta[name="theme-color"]').forEach(
    (tag) => tag.setAttribute("content", chrome));
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
