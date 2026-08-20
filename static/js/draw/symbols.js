/* Condition glyphs, drawn as line art rather than pictorial icons so they sit
   inside a technical drawing without looking pasted in. */

import { svg } from "../ui/dom.js";

const CLOUD = "M7 17.5h9.2a3.4 3.4 0 0 0 .3-6.8 5.2 5.2 0 0 0-9.9-1.4A3.9 3.9 0 0 0 7 17.5Z";

function stroke(d, extra = {}) {
  return svg("path", {
    d,
    fill: "none",
    stroke: "currentColor",
    "stroke-width": 1.4,
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
    ...extra,
  });
}

function sun(cx = 12, cy = 11, r = 4) {
  const rays = [];
  for (let i = 0; i < 8; i += 1) {
    const a = (i * Math.PI) / 4;
    const x1 = cx + Math.cos(a) * (r + 2);
    const y1 = cy + Math.sin(a) * (r + 2);
    const x2 = cx + Math.cos(a) * (r + 4);
    const y2 = cy + Math.sin(a) * (r + 4);
    rays.push(stroke(`M${x1.toFixed(1)} ${y1.toFixed(1)}L${x2.toFixed(1)} ${y2.toFixed(1)}`));
  }
  return [svg("circle", { cx, cy, r, fill: "none", stroke: "currentColor", "stroke-width": 1.4 }), ...rays];
}

function moon() {
  return [stroke("M17 14.5A6.5 6.5 0 0 1 9.5 7a6.5 6.5 0 1 0 7.5 7.5Z")];
}

function drops(count, y = 19) {
  const out = [];
  for (let i = 0; i < count; i += 1) {
    const x = 9 + i * 3.2;
    out.push(stroke(`M${x} ${y}l-1 2.6`));
  }
  return out;
}

function flakes(count) {
  const out = [];
  for (let i = 0; i < count; i += 1) {
    const x = 9.5 + i * 3.4;
    out.push(stroke(`M${x} 19v3M${x - 1.3} 19.8l2.6 1.4M${x + 1.3} 19.8l-2.6 1.4`, { "stroke-width": 1.1 }));
  }
  return out;
}

function bolt() {
  return [stroke("M13 17.5l-2.6 4h3l-1.2 3.2", { "stroke-width": 1.4 })];
}

const RECIPES = {
  clear: () => sun(),
  "clear-night": () => moon(),
  "mostly-clear": () => [...sun(9.5, 9, 3.2), stroke(CLOUD)],
  "partly-cloudy": () => [...sun(8.5, 8, 3), stroke(CLOUD)],
  cloudy: () => [stroke(CLOUD), stroke("M5.5 12.5a3.2 3.2 0 0 1 3-4.4")],
  overcast: () => [stroke(CLOUD), stroke("M4.5 13.5h3M4.5 10.5h2")],
  mist: () => [stroke("M4 9h16M4 12.5h16M7 16h13M4 19.5h12", { "stroke-dasharray": "5 3" })],
  fog: () => [stroke(CLOUD), stroke("M5 20.5h14M7 23h10", { "stroke-dasharray": "4 3" })],
  drizzle: () => [stroke(CLOUD), ...drops(2)],
  "rain-light": () => [stroke(CLOUD), ...drops(2)],
  rain: () => [stroke(CLOUD), ...drops(3)],
  "rain-heavy": () => [stroke(CLOUD), ...drops(4), stroke("M8 19l-1 3.4")],
  sleet: () => [stroke(CLOUD), ...drops(1), ...flakes(1)],
  "snow-light": () => [stroke(CLOUD), ...flakes(1)],
  snow: () => [stroke(CLOUD), ...flakes(2)],
  "snow-heavy": () => [stroke(CLOUD), ...flakes(3)],
  blizzard: () => [stroke(CLOUD), ...flakes(2), stroke("M3 20h5M3 23h8", { "stroke-dasharray": "3 2" })],
  hail: () => [stroke(CLOUD), stroke("M10 20.5l1.3 2.2h-2.6zM14 20.5l1.3 2.2h-2.6z")],
  thunder: () => [stroke(CLOUD), ...bolt()],
  "thunder-rain": () => [stroke(CLOUD), ...bolt(), ...drops(1)],
};

export function conditionSymbol(slug, { isDay = true, size = 28, title = "" } = {}) {
  const key = slug === "clear" && !isDay ? "clear-night" : slug;
  const recipe = RECIPES[key] || RECIPES["partly-cloudy"];
  const node = svg("svg", {
    viewBox: "0 0 26 26",
    width: size,
    height: size,
    role: title ? "img" : "presentation",
    "aria-hidden": title ? null : "true",
    "aria-label": title || null,
    focusable: "false",
  }, recipe());
  if (title) node.append(svg("title", {}, [title]));
  return node;
}

export const SYMBOL_SLUGS = Object.keys(RECIPES);
