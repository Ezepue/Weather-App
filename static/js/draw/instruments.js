/* Instruments drawn to synoptic-chart convention: a barometer dial, a wind
   rose carrying a real wind barb, a station plot, a moon disc and a comfort
   arc. These are the parts that make the page read as an instrument rather
   than a dashboard. */

import { svg } from "../ui/dom.js";
import { conditionSymbol } from "./symbols.js";

const TAU = Math.PI * 2;

function polar(cx, cy, r, deg) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

function arcPath(cx, cy, r, startDeg, endDeg) {
  const [x1, y1] = polar(cx, cy, r, startDeg);
  const [x2, y2] = polar(cx, cy, r, endDeg);
  const large = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  return `M${x1.toFixed(2)} ${y1.toFixed(2)}A${r} ${r} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
}

/* ---- barometer ------------------------------------------------------- */

const BARO_MIN = 950;
const BARO_MAX = 1050;
const BARO_SWEEP = 270;

export function barometer(pressureMb, trend, { size = 170 } = {}) {
  const c = size / 2;
  const r = c - 16;
  const clamped = Math.max(BARO_MIN, Math.min(BARO_MAX, pressureMb ?? 1013));
  const fraction = (clamped - BARO_MIN) / (BARO_MAX - BARO_MIN);
  const angle = -135 + fraction * BARO_SWEEP;

  const children = [
    svg("path", { class: "dial-face", d: arcPath(c, c, r, -135, 135) }),
  ];

  for (let mb = BARO_MIN; mb <= BARO_MAX; mb += 10) {
    const major = mb % 25 === 0;
    const a = -135 + ((mb - BARO_MIN) / (BARO_MAX - BARO_MIN)) * BARO_SWEEP;
    const [x1, y1] = polar(c, c, r - (major ? 8 : 4), a);
    const [x2, y2] = polar(c, c, r, a);
    children.push(svg("line", { class: major ? "dial-tick dial-tick--major" : "dial-tick", x1, y1, x2, y2 }));
    if (major) {
      const [tx, ty] = polar(c, c, r - 17, a);
      children.push(svg("text", { class: "dial-text", x: tx, y: ty + 3 }, [String(mb)]));
    }
  }

  const [nx, ny] = polar(c, c, r - 14, angle);
  const [bx, by] = polar(c, c, 9, angle + 180);
  children.push(
    svg("line", { class: "dial-needle", x1: bx, y1: by, x2: nx, y2: ny }),
    svg("circle", { cx: c, cy: c, r: 3.5, fill: "currentColor" }),
  );

  return svg("svg", {
    viewBox: `0 0 ${size} ${size}`, width: size, height: size,
    role: "img",
    "aria-label": `Barometer: ${Math.round(pressureMb ?? 0)} millibars, ${trend?.label || "unknown"} trend`,
  }, children);
}

/* ---- wind barb -------------------------------------------------------- */

/* Station-model notation: pennant = 50 kt, full barb = 10 kt, half = 5 kt.
   The shaft points along the direction the wind is coming FROM. */
export function windBarb(barb, { length = 34, x = 0, y = 0, angle = 0 } = {}) {
  const group = svg("g", { transform: `translate(${x} ${y}) rotate(${angle})` });

  if (!barb || barb.calm) {
    group.append(svg("circle", { cx: 0, cy: 0, r: 5, class: "station-circle" }));
    return group;
  }

  group.append(svg("line", { x1: 0, y1: 0, x2: 0, y2: -length, class: "barb-line" }));

  let offset = -length;
  const step = 5;
  for (let i = 0; i < barb.pennants; i += 1) {
    group.append(svg("path", {
      d: `M0 ${offset}L11 ${offset + 3.5}L0 ${offset + 7}Z`,
      class: "barb-flag",
    }));
    offset += 8;
  }
  for (let i = 0; i < barb.full; i += 1) {
    group.append(svg("line", { x1: 0, y1: offset, x2: 11, y2: offset - 3.5, class: "barb-line" }));
    offset += step;
  }
  if (barb.half) {
    group.append(svg("line", { x1: 0, y1: offset, x2: 5.5, y2: offset - 2, class: "barb-line" }));
  }
  return group;
}

export function windRose(dirDeg, speedKph, barb, { size = 160 } = {}) {
  const c = size / 2;
  const r = c - 22;
  const children = [svg("circle", { cx: c, cy: c, r, class: "dial-face" })];

  for (let i = 0; i < 16; i += 1) {
    const a = i * 22.5;
    const major = i % 4 === 0;
    const [x1, y1] = polar(c, c, r - (major ? 7 : 3), a);
    const [x2, y2] = polar(c, c, r, a);
    children.push(svg("line", { class: major ? "dial-tick dial-tick--major" : "dial-tick", x1, y1, x2, y2 }));
  }
  ["N", "E", "S", "W"].forEach((letter, i) => {
    const [tx, ty] = polar(c, c, r + 11, i * 90);
    children.push(svg("text", { class: "dial-text", x: tx, y: ty + 3.5 }, [letter]));
  });

  /* The arrow flies with the wind; the barb marks where it comes from. */
  const [tipX, tipY] = polar(c, c, r - 12, (dirDeg + 180) % 360);
  const [tailX, tailY] = polar(c, c, r - 12, dirDeg);
  children.push(
    svg("line", { x1: tailX, y1: tailY, x2: tipX, y2: tipY, stroke: "var(--accent)", "stroke-width": 2 }),
    svg("circle", { cx: tailX, cy: tailY, r: 3, fill: "var(--accent)" }),
  );
  children.push(windBarb(barb, { x: c, y: c, angle: dirDeg, length: r - 26 }));

  return svg("svg", {
    viewBox: `0 0 ${size} ${size}`, width: size, height: size,
    role: "img",
    "aria-label": `Wind from ${Math.round(dirDeg)} degrees at ${Math.round(speedKph)} kilometres per hour`,
  }, children);
}

/* ---- station plot ------------------------------------------------------ */

const CLOUD_FILL = [
  { max: 5, d: "" },
  { max: 30, d: "M0 -12A12 12 0 0 1 0 12Z" },
  { max: 55, d: "M-12 0H12" },
  { max: 80, d: "M0 -12A12 12 0 0 1 0 12Z M-12 0H0" },
  { max: 101, d: "full" },
];

/* The real station model: sky cover in the circle, temperature upper left,
   dew point lower left, pressure upper right, wind barb off the circle. */
export function stationPlot(current, formatter, { size = 230 } = {}) {
  const c = size / 2;
  const children = [];
  const cover = CLOUD_FILL.find((entry) => (current.cloud ?? 0) < entry.max) || CLOUD_FILL[4];

  children.push(svg("circle", { cx: c, cy: c, r: 12, class: "station-circle" }));
  if (cover.d === "full") {
    children.push(svg("circle", { cx: c, cy: c, r: 12, class: "station-fill" }));
  } else if (cover.d) {
    children.push(svg("path", { d: cover.d, class: "station-fill", transform: `translate(${c} ${c})`, stroke: "currentColor" }));
  }

  const barb = current.barb || {};
  children.push(windBarb(barb, { x: c, y: c, angle: current.wind_dir_deg ?? 0, length: 52 }));

  const temp = formatter.temp(current.temp_c);
  const dew = formatter.temp(current.dewpoint_c);
  const pressureCode = current.pressure_mb
    ? String(Math.round(current.pressure_mb * 10) % 1000).padStart(3, "0")
    : "---";

  children.push(
    svg("text", { class: "station-text", x: c - 20, y: c - 10, "text-anchor": "end" }, [temp]),
    svg("text", { class: "station-text", x: c - 20, y: c + 18, "text-anchor": "end", fill: "var(--precip)" }, [dew]),
    svg("text", { class: "station-text", x: c + 20, y: c - 10 }, [pressureCode]),
    svg("text", { class: "station-text", x: c + 20, y: c + 18, fill: "var(--ink-3)", "font-size": 10 }, [`${current.cloud}%`]),
  );

  const symbol = conditionSymbol(current.condition.slug, { isDay: current.is_day, size: 26 });
  const holder = svg("g", { transform: `translate(${c - 62} ${c - 13})`, color: "var(--ink-2)" });
  holder.append(symbol);
  children.push(holder);

  return svg("svg", {
    viewBox: `0 0 ${size} ${size}`, width: size, height: size,
    role: "img",
    "aria-label": `Station plot: ${current.condition.text}, ${temp}, dew point ${dew}, pressure ${current.pressure_mb} millibars`,
  }, children);
}

/* ---- moon -------------------------------------------------------------- */

export function moonDisc(illumination, waxing, { size = 96, phase = "" } = {}) {
  const c = size / 2;
  const r = c - 6;
  const fraction = Math.max(0, Math.min(100, illumination ?? 0)) / 100;
  const id = `moon-${Math.random().toString(36).slice(2, 9)}`;

  /* The terminator is an ellipse whose width tracks the illuminated fraction;
     its sign flips at half moon, which is what makes gibbous read correctly. */
  const offset = Math.cos(fraction * Math.PI) * r;
  const mask = svg("mask", { id }, [
    svg("rect", { x: 0, y: 0, width: size, height: size, fill: "black" }),
    svg("circle", { cx: c, cy: c, r, fill: "white" }),
    svg("ellipse", {
      cx: c, cy: c, rx: Math.abs(offset), ry: r,
      fill: fraction < 0.5 ? "black" : "white",
    }),
    svg("rect", {
      x: waxing ? 0 : c, y: 0, width: c, height: size, fill: "black",
    }),
  ]);

  return svg("svg", {
    viewBox: `0 0 ${size} ${size}`, width: size, height: size,
    role: "img", "aria-label": `${phase || "Moon"}, ${Math.round(illumination ?? 0)} percent illuminated`,
  }, [
    mask,
    svg("circle", { cx: c, cy: c, r, fill: "none", stroke: "var(--rule-strong)", "stroke-width": 1 }),
    svg("circle", { cx: c, cy: c, r, fill: "var(--ink-2)", mask: `url(#${id})` }),
  ]);
}

/* ---- comfort arc -------------------------------------------------------- */

export function comfortArc(score, tone, { size = 150 } = {}) {
  const c = size / 2;
  const r = c - 18;
  const sweep = 240;
  const start = -120;
  const end = start + (Math.max(0, Math.min(100, score)) / 100) * sweep;
  const colour = { ok: "var(--ok)", warn: "var(--warn)", bad: "var(--bad)" }[tone] || "var(--accent)";

  const ticks = [];
  for (let i = 0; i <= 10; i += 1) {
    const a = start + (i / 10) * sweep;
    const [x1, y1] = polar(c, c, r - (i % 5 === 0 ? 8 : 4), a);
    const [x2, y2] = polar(c, c, r, a);
    ticks.push(svg("line", { class: i % 5 === 0 ? "dial-tick dial-tick--major" : "dial-tick", x1, y1, x2, y2 }));
  }

  return svg("svg", {
    viewBox: `0 0 ${size} ${size}`, width: size, height: size,
    role: "img", "aria-label": `Comfort index ${score} out of 100`,
  }, [
    svg("path", { d: arcPath(c, c, r, start, start + sweep), class: "dial-face", "stroke-width": 6 }),
    score > 0 ? svg("path", {
      d: arcPath(c, c, r, start, end), fill: "none", stroke: colour, "stroke-width": 6,
    }) : null,
    ...ticks,
    svg("text", { class: "dial-value", x: c, y: c + 4, "font-size": 26 }, [String(score)]),
    svg("text", { class: "dial-text", x: c, y: c + 22 }, ["COMFORT"]),
  ].filter(Boolean));
}

/* ---- UV ladder ---------------------------------------------------------- */

export function uvLadder(uv, { width = 200, height = 54 } = {}) {
  const steps = 12;
  const gap = 3;
  const barWidth = (width - gap * (steps - 1)) / steps;
  const value = Math.max(0, Math.min(steps, uv ?? 0));
  const colourFor = (i) => {
    if (i < 3) return "var(--precip)";
    if (i < 6) return "var(--caution)";
    if (i < 8) return "var(--warm)";
    if (i < 11) return "var(--danger)";
    return "var(--violet)";
  };

  const bars = [];
  for (let i = 0; i < steps; i += 1) {
    const filled = i < Math.round(value);
    bars.push(svg("rect", {
      x: i * (barWidth + gap), y: 0, width: barWidth, height: height - 16,
      fill: filled ? colourFor(i) : "var(--field)",
      stroke: "var(--rule)", "stroke-width": 1,
    }));
  }
  for (let i = 0; i < steps; i += 3) {
    bars.push(svg("text", {
      class: "chart-label", x: i * (barWidth + gap), y: height - 4,
    }, [String(i)]));
  }

  return svg("svg", {
    viewBox: `0 0 ${width} ${height}`, width: "100%", height: null,
    preserveAspectRatio: "xMinYMid meet",
    role: "img", "aria-label": `UV index ${uv}`,
    style: `max-width:${width}px`,
  }, bars);
}

/* ---- thermometer column --------------------------------------------------- */

export function thermometer(current, min, max, { height = 130, width = 46 } = {}) {
  const span = Math.max(1, max - min);
  const ratio = Math.max(0, Math.min(1, (current - min) / span));
  const top = 10;
  const bottom = height - 18;
  const y = bottom - ratio * (bottom - top);

  return svg("svg", {
    viewBox: `0 0 ${width} ${height}`, width, height,
    role: "img", "aria-label": `Temperature ${current} between today's low ${min} and high ${max}`,
  }, [
    svg("rect", { x: width / 2 - 6, y: top, width: 12, height: bottom - top, fill: "var(--field)", stroke: "var(--rule)" }),
    svg("rect", {
      x: width / 2 - 6, y, width: 12, height: bottom - y,
      fill: "url(#thermo-grad)",
    }),
    svg("defs", {}, [
      svg("linearGradient", { id: "thermo-grad", x1: 0, y1: 1, x2: 0, y2: 0 }, [
        svg("stop", { offset: "0%", "stop-color": "var(--cold)" }),
        svg("stop", { offset: "100%", "stop-color": "var(--warm)" }),
      ]),
    ]),
    svg("line", { x1: width / 2 - 11, y1: y, x2: width / 2 + 11, y2: y, stroke: "var(--ink)", "stroke-width": 1.5 }),
    svg("text", { class: "chart-label", x: width / 2 + 13, y: top + 4 }, [String(Math.round(max))]),
    svg("text", { class: "chart-label", x: width / 2 + 13, y: bottom }, [String(Math.round(min))]),
  ]);
}
