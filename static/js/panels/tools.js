/* Panels the reader operates rather than reads: activities, places, compare,
   and preferences. */

import { el } from "../ui/dom.js";
import { datum, log, logRow } from "../ui/parts.js";
import { SCHEMA } from "../core/settings.js";
import { registerPanel } from "./registry.js";

const ACTIVITY_GLYPHS = {
  run: "▶", bike: "◉", laundry: "≋", stars: "✦",
  beach: "◠", plant: "❦", camera: "◧", kite: "◈",
};

registerPanel({
  id: "activities",
  title: "What today is good for",
  order: 160,
  span: 6,
  available: ({ report }) => Boolean(report.advice?.activities?.length),
  render({ report }) {
    const sorted = [...report.advice.activities].sort((a, b) => b.score - a.score);
    return el("div", { class: "activity" }, sorted.map((a) => el("div", {
      class: `activity__row tone-${a.tone}`,
    }, [
      el("span", { class: "num", text: ACTIVITY_GLYPHS[a.icon] || "•", "aria-hidden": "true" }),
      el("div", {}, [
        el("div", { class: "activity__name", text: a.label }),
        el("div", { class: "activity__reason", text: a.reason }),
      ]),
      el("div", { class: "activity__score", text: String(a.score) }),
      el("div", { class: "activity__bar" }, [el("span", { style: `width:${a.score}%` })]),
    ])));
  },
});

registerPanel({
  id: "places",
  title: "Saved places",
  order: 170,
  span: 6,
  render({ places, actions, report }) {
    const state = places.all();
    const current = report.place.label;

    const rows = state.saved.map((p) => el("div", { class: "log__row" }, [
      el("button", {
        class: "btn btn--ghost", type: "button", text: `${state.home === p.label ? "★ " : ""}${p.label}`,
        onclick: () => actions.load(p.query || p.label),
      }),
      el("div", { class: "row", style: "gap:.25rem" }, [
        el("button", { class: "btn btn--icon btn--ghost", type: "button", title: "Move up", text: "↑", onclick: () => actions.movePlace(p.label, -1) }),
        el("button", { class: "btn btn--icon btn--ghost", type: "button", title: "Move down", text: "↓", onclick: () => actions.movePlace(p.label, 1) }),
        el("button", { class: "btn btn--icon btn--ghost", type: "button", title: "Set as home", text: "★", onclick: () => actions.setHome(p.label) }),
        el("button", { class: "btn btn--icon btn--ghost", type: "button", title: "Remove", text: "✕", onclick: () => actions.removePlace(p.label) }),
      ]),
    ]));

    const recents = state.recent.filter((p) => p.label !== current).slice(0, 6);

    return el("div", { class: "stack" }, [
      el("button", {
        class: "btn", type: "button",
        text: places.isSaved(current) ? "★ Saved — remove this place" : "☆ Save this place",
        onclick: () => actions.toggleSave(),
      }),
      rows.length ? el("div", { class: "log" }, rows) : el("p", { class: "caption", text: "Nothing saved yet." }),
      recents.length ? el("div", {}, [
        el("span", { class: "label", text: "Recent" }),
        el("div", { class: "row row--wrap", style: "margin-top:.5rem" }, recents.map((p) => el("button", {
          class: "btn btn--ghost", type: "button", text: p.name || p.label,
          onclick: () => actions.load(p.query || p.label),
        }))),
      ]) : null,
      el("button", { class: "btn btn--ghost", type: "button", text: "Use my location", onclick: () => actions.locate() }),
    ]);
  },
});

registerPanel({
  id: "compare",
  title: "Compare",
  order: 180,
  span: 12,
  available: ({ comparison }) => Boolean(comparison?.length),
  render({ comparison, formatter, actions }) {
    const best = (key, pick) => {
      const values = comparison.map(pick);
      const target = key === "max" ? Math.max(...values) : Math.min(...values);
      return values.map((v) => v === target);
    };
    const warmest = best("max", (r) => r.current.temp_c);
    const comfiest = best("max", (r) => r.advice?.comfort.score ?? 0);

    return el("div", { class: "stack" }, [
      el("div", { class: "compare" }, comparison.map((r, i) => el("div", { class: "compare__col" }, [
        el("div", { class: "compare__name", text: r.place.name }),
        el("div", { class: `readout${warmest[i] ? " compare__win" : ""}`, style: "font-size:var(--step-3)", text: formatter.temp(r.current.temp_c) }),
        el("div", { class: "caption", text: r.current.condition.text }),
        log([
          logRow("Feels", formatter.temp(r.current.feels_c)),
          logRow("Comfort", `${r.advice?.comfort.score ?? "--"}${comfiest[i] ? " ★" : ""}`),
          logRow("Wind", formatter.text("wind", r.current.wind_kph)),
          logRow("Rain 24h", formatter.text("precip", r.advice?.precip_next_24h_mm ?? 0)),
          logRow("Local time", formatter.clock(r.place.localtime_epoch, r)),
        ]),
      ]))),
      el("button", { class: "btn btn--ghost", type: "button", text: "Clear comparison", onclick: () => actions.clearCompare() }),
    ]);
  },
});

registerPanel({
  id: "settings",
  title: "Preferences",
  order: 190,
  span: 6,
  render({ settings, actions, hiddenPanels, panels }) {
    const control = (key) => {
      const spec = SCHEMA[key];
      return el("label", { class: "stack", style: "gap:.25rem" }, [
        el("span", { class: "label", text: spec.label }),
        el("select", {
          class: "field",
          onchange: (e) => actions.setSetting(key, e.target.value),
        }, spec.options.map((option) => el("option", {
          value: option, selected: settings[key] === option, text: labelFor(key, option),
        }))),
      ]);
    };

    return el("div", { class: "stack" }, [
      el("div", { class: "datum-grid" }, Object.keys(SCHEMA).map(control)),
      el("div", { style: "border-top:1px solid var(--rule);padding-top:.75rem" }, [
        el("span", { class: "label", text: "Panels" }),
        el("div", { class: "row row--wrap", style: "margin-top:.5rem" }, panels.map((panel) => el("button", {
          class: "btn btn--ghost",
          type: "button",
          "aria-pressed": String(!hiddenPanels.includes(panel.id)),
          text: panel.title,
          onclick: () => actions.togglePanel(panel.id),
        }))),
      ]),
      el("div", { class: "row row--wrap", style: "border-top:1px solid var(--rule);padding-top:.75rem" }, [
        el("button", { class: "btn btn--ghost", type: "button", text: "Export settings", onclick: () => actions.exportSettings() }),
        el("button", { class: "btn btn--ghost", type: "button", text: "Import settings", onclick: () => actions.importSettings() }),
        el("button", { class: "btn btn--ghost", type: "button", text: "Reset", onclick: () => actions.resetSettings() }),
      ]),
    ]);
  },
});

const OPTION_LABELS = {
  theme: { cyanotype: "Cyanotype (dark)", draft: "Draft (light)" },
  units: { metric: "Metric", imperial: "Imperial" },
  temperature: { c: "Celsius", f: "Fahrenheit" },
  wind: { kph: "km/h", mph: "mph", ms: "m/s", kn: "knots", bft: "Beaufort" },
  pressure: { mb: "millibars", inhg: "inches Hg", mmhg: "mm Hg" },
  precip: { mm: "millimetres", in: "inches" },
  distance: { km: "kilometres", mi: "miles" },
  clock: { 24: "24 hour", 12: "12 hour" },
  density: { comfortable: "Comfortable", compact: "Compact" },
  contrast: { normal: "Normal", high: "High contrast" },
  motion: { system: "Match system", on: "Animate", off: "Reduce motion" },
  isobars: { on: "Show", off: "Hide" },
  refresh: { 0: "Off", 300: "Every 5 min", 600: "Every 10 min", 1800: "Every 30 min" },
  indoor: {},
};

function labelFor(key, option) {
  const table = OPTION_LABELS[key] || {};
  if (table[option]) return table[option];
  if (key === "indoor") return `${option}°C`;
  return option;
}
