/* Shared building blocks so panels stay declarative. */

import { el } from "./dom.js";

export function datum(label, value, note, { tone, large } = {}) {
  return el("div", { class: "datum" }, [
    el("span", { class: "label", text: label }),
    el("span", {
      class: `datum__value${large ? " datum__value--lg" : ""}${tone ? ` tone-${tone}` : ""}`,
      text: value ?? "--",
    }),
    note ? el("span", { class: "datum__note", text: note }) : null,
  ]);
}

export function logRow(key, value, tone) {
  return el("div", { class: "log__row" }, [
    el("span", { class: "log__key", text: key }),
    el("span", { class: `log__value${tone ? ` tone-${tone}` : ""}`, text: value ?? "--" }),
  ]);
}

export function log(rows) {
  return el("div", { class: "log" }, rows.filter(Boolean));
}

export function meter(fraction, { tone = "accent", low = "", high = "" } = {}) {
  const colour = tone === "accent" ? "var(--accent)" : `var(--${tone})`;
  return el("div", { class: "meter" }, [
    el("div", { class: "meter__track" }, [
      el("div", {
        class: "meter__fill",
        style: `width:${Math.max(0, Math.min(1, fraction)) * 100}%;background:${colour}`,
      }),
    ]),
    low || high ? el("div", { class: "meter__scale" }, [
      el("span", { text: low }), el("span", { text: high }),
    ]) : null,
  ]);
}

export function badge(text, tone) {
  return el("span", { class: `badge${tone ? ` tone-${tone}` : ""}`, text });
}

export function noData(message = "No data for this location") {
  return el("div", { class: "no-data" }, [el("span", { text: message })]);
}

export function chipRow(items) {
  return el("div", { class: "row row--wrap" }, items.filter(Boolean));
}
