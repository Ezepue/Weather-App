/* Charts drawn on ruled graph paper, annotated the way a drawing is: dashed
   leader lines into callouts rather than floating tooltips. */

import { svg } from "../ui/dom.js";

const NICE_STEPS = [1, 2, 2.5, 5, 10, 20, 25, 50];

function niceStep(span, target = 5) {
  const raw = span / target;
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(raw, 1e-6)));
  const normalised = raw / magnitude;
  const step = NICE_STEPS.find((s) => s >= normalised) ?? 10;
  return step * magnitude;
}

function linePath(points) {
  return points.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join("");
}

/* ---- meteogram ---------------------------------------------------------- */

export function meteogram(hours, { formatter, report, nowEpoch, height = 290, width = 960 } = {}) {
  const pad = { top: 26, right: 14, bottom: 34, left: 38 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  if (!hours.length) {
    return svg("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart" }, [
      svg("text", { class: "chart-label", x: width / 2, y: height / 2, "text-anchor": "middle" }, ["No hourly data"]),
    ]);
  }

  const t0 = hours[0].t;
  const t1 = hours[hours.length - 1].t;
  const spanT = Math.max(1, t1 - t0);
  const x = (t) => pad.left + ((t - t0) / spanT) * plotW;

  const temps = hours.flatMap((h) => [h.temp_c, h.feels_c]).filter((v) => v !== null);
  const rawMin = Math.min(...temps);
  const rawMax = Math.max(...temps);
  const step = niceStep(Math.max(4, rawMax - rawMin));
  const yMin = Math.floor(rawMin / step) * step - step * 0.5;
  const yMax = Math.ceil(rawMax / step) * step + step * 0.5;
  const y = (v) => pad.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

  const maxPrecip = Math.max(1.5, ...hours.map((h) => h.precip_mm || 0));
  const precipH = plotH * 0.32;
  const yPrecip = (mm) => pad.top + plotH - (mm / maxPrecip) * precipH;

  const layers = [];

  /* Night bands first, so everything else sits on top of them. */
  let runStart = null;
  hours.forEach((h, i) => {
    if (!h.is_day && runStart === null) runStart = h.t;
    const ends = h.is_day || i === hours.length - 1;
    if (runStart !== null && ends) {
      layers.push(svg("rect", {
        class: "chart-night", x: x(runStart), y: pad.top,
        width: Math.max(1, x(h.t) - x(runStart)), height: plotH,
      }));
      runStart = null;
    }
  });

  /* Ruled grid with temperature labels. */
  const grid = svg("g", { class: "chart-grid" });
  for (let v = Math.ceil(yMin / step) * step; v <= yMax; v += step) {
    grid.append(svg("line", { x1: pad.left, y1: y(v), x2: width - pad.right, y2: y(v) }));
    layers.push(svg("text", {
      class: "chart-axis", x: pad.left - 6, y: y(v) + 3, "text-anchor": "end", fill: "var(--ink-3)",
      "font-family": "var(--font-num)", "font-size": 9,
    }, [formatter.temp(v)]));
  }
  layers.unshift(grid);

  /* Hour ticks every three hours, plus a date change marker. */
  hours.forEach((h) => {
    const local = new Date((h.t + (report?.place?.utc_offset_hours ?? 0) * 3600) * 1000);
    const hour = local.getUTCHours();
    if (hour % 3 !== 0) return;
    grid.append(svg("line", { x1: x(h.t), y1: pad.top, x2: x(h.t), y2: pad.top + plotH }));
    layers.push(svg("text", {
      class: "chart-axis", x: x(h.t), y: height - 18, "text-anchor": "middle",
      fill: "var(--ink-3)", "font-family": "var(--font-num)", "font-size": 9,
    }, [formatter.hourLabel(h.t, report)]));
    if (hour === 0) {
      layers.push(svg("text", {
        class: "chart-axis", x: x(h.t), y: height - 6, "text-anchor": "middle",
        fill: "var(--ink-2)", "font-family": "var(--font-num)", "font-size": 9,
      }, [formatter.dayName(h.t, report)]));
    }
  });

  /* Precipitation bars against their own scale at the foot of the plot. */
  const barWidth = Math.max(2, (plotW / hours.length) * 0.62);
  hours.forEach((h) => {
    if (!h.precip_mm) return;
    const top = yPrecip(h.precip_mm);
    layers.push(svg("rect", {
      class: "chart-precip", x: x(h.t) - barWidth / 2, y: top,
      width: barWidth, height: pad.top + plotH - top,
    }));
  });

  layers.push(svg("path", { class: "chart-feels", d: linePath(hours.map((h) => [x(h.t), y(h.feels_c)])) }));
  layers.push(svg("path", { class: "chart-temp", d: linePath(hours.map((h) => [x(h.t), y(h.temp_c)])) }));

  /* Drafting callouts on the extremes: dashed leader into a label. */
  const warmest = hours.reduce((a, b) => (b.temp_c > a.temp_c ? b : a));
  const coldest = hours.reduce((a, b) => (b.temp_c < a.temp_c ? b : a));
  [[warmest, -14, "var(--warm)"], [coldest, 18, "var(--cold)"]].forEach(([point, dy, colour]) => {
    const px = x(point.t);
    const py = y(point.temp_c);
    const anchor = px > width - 90 ? "end" : "start";
    const tx = anchor === "end" ? px - 6 : px + 6;
    layers.push(
      svg("circle", { cx: px, cy: py, r: 2.5, fill: colour }),
      svg("path", { class: "leader", d: `M${px} ${py}L${px} ${py + dy}` }),
      svg("text", {
        class: "callout", x: tx, y: py + dy + (dy < 0 ? -2 : 9), "text-anchor": anchor,
        fill: colour, "font-family": "var(--font-num)", "font-size": 10,
      }, [`${formatter.temp(point.temp_c)} ${formatter.clock(point.t, report)}`]),
    );
  });

  /* Sunrise and sunset gnomons. */
  (report?.daily || []).forEach((day) => {
    [["sunrise_epoch", "▲"], ["sunset_epoch", "▼"]].forEach(([key, glyph]) => {
      const t = day[key];
      if (!t || t < t0 || t > t1) return;
      layers.push(svg("text", {
        class: "chart-label", x: x(t), y: pad.top - 8, "text-anchor": "middle",
        fill: "var(--caution)", "font-size": 9,
      }, [glyph]));
    });
  });

  /* Now. */
  if (nowEpoch >= t0 && nowEpoch <= t1) {
    layers.push(
      svg("line", { class: "chart-marker", x1: x(nowEpoch), y1: pad.top - 4, x2: x(nowEpoch), y2: pad.top + plotH }),
      svg("text", {
        class: "chart-label", x: x(nowEpoch) + 4, y: pad.top - 8,
        fill: "var(--accent)", "font-size": 9,
      }, ["NOW"]),
    );
  }

  layers.push(svg("rect", {
    x: pad.left, y: pad.top, width: plotW, height: plotH,
    fill: "none", stroke: "var(--rule-strong)", "stroke-width": 1,
  }));

  return svg("svg", {
    viewBox: `0 0 ${width} ${height}`, class: "chart",
    role: "img",
    "aria-label": `Hourly temperature and precipitation. Range ${formatter.temp(coldest.temp_c)} to ${formatter.temp(warmest.temp_c)}.`,
  }, layers);
}

/* ---- sun path ------------------------------------------------------------- */

export function sunPath(astro, { formatter, report, nowEpoch, width = 460, height = 150 } = {}) {
  const path = astro?.sun_path || [];
  if (!path.length) return svg("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart" });

  const pad = { top: 14, right: 12, bottom: 22, left: 12 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const t0 = path[0].t;
  const t1 = path[path.length - 1].t;
  const maxElev = Math.max(20, ...path.map((p) => p.elevation));
  const minElev = Math.min(-20, ...path.map((p) => p.elevation));

  const x = (t) => pad.left + ((t - t0) / (t1 - t0)) * plotW;
  const y = (e) => pad.top + plotH - ((e - minElev) / (maxElev - minElev)) * plotH;

  const horizon = y(0);
  const layers = [
    svg("rect", { x: pad.left, y: horizon, width: plotW, height: pad.top + plotH - horizon, fill: "var(--ground-sunk)" }),
    svg("line", { x1: pad.left, y1: horizon, x2: width - pad.right, y2: horizon, stroke: "var(--rule-strong)", "stroke-width": 1 }),
    svg("path", {
      d: linePath(path.map((p) => [x(p.t), y(p.elevation)])),
      fill: "none", stroke: "var(--caution)", "stroke-width": 2,
    }),
  ];

  [["sunrise_epoch", "rise"], ["sunset_epoch", "set"]].forEach(([key, label]) => {
    const t = astro[key];
    if (!t || t < t0 || t > t1) return;
    layers.push(
      svg("line", { class: "leader", x1: x(t), y1: pad.top, x2: x(t), y2: horizon }),
      svg("text", { class: "chart-label", x: x(t), y: height - 8, "text-anchor": "middle" },
        [`${label} ${formatter.clock(t, report)}`]),
    );
  });

  const current = path.reduce((a, b) => (Math.abs(b.t - nowEpoch) < Math.abs(a.t - nowEpoch) ? b : a));
  layers.push(svg("circle", {
    cx: x(current.t), cy: y(current.elevation), r: 5,
    fill: current.elevation > 0 ? "var(--caution)" : "var(--ink-3)",
    stroke: "var(--ground-2)", "stroke-width": 2,
  }));
  layers.push(svg("text", {
    class: "chart-label", x: pad.left, y: pad.top - 2,
    fill: "var(--ink-2)",
  }, [`Sun ${astro.solar_elevation > 0 ? "+" : ""}${Math.round(astro.solar_elevation)}° elevation, bearing ${Math.round(astro.solar_azimuth)}°`]));

  return svg("svg", {
    viewBox: `0 0 ${width} ${height}`, class: "chart",
    role: "img", "aria-label": `Sun path. Currently ${Math.round(astro.solar_elevation)} degrees elevation.`,
  }, layers);
}

/* ---- pollutants ------------------------------------------------------------- */

const POLLUTANT_LABELS = { pm2_5: "PM2.5", pm10: "PM10", o3: "O₃", no2: "NO₂", so2: "SO₂", co: "CO" };
const POLLUTANT_REFERENCE = { pm2_5: 25, pm10: 50, o3: 100, no2: 40, so2: 40, co: 4000 };

export function pollutantBars(air, { width = 420, rowHeight = 26 } = {}) {
  const entries = Object.entries(air?.pollutants || {});
  if (!entries.length) return svg("svg", { viewBox: `0 0 ${width} ${rowHeight}` });

  const labelW = 54;
  const valueW = 66;
  const barW = width - labelW - valueW;
  const height = entries.length * rowHeight;
  const layers = [];

  entries.forEach(([key, value], i) => {
    const reference = POLLUTANT_REFERENCE[key] || 100;
    const ratio = Math.min(1.4, value / reference);
    const y = i * rowHeight + 6;
    const over = ratio > 1;
    layers.push(
      svg("text", { class: "chart-label", x: 0, y: y + 10, fill: "var(--ink-2)" }, [POLLUTANT_LABELS[key] || key]),
      svg("rect", { x: labelW, y: y + 2, width: barW, height: 10, fill: "var(--field)", stroke: "var(--rule)" }),
      svg("rect", {
        x: labelW, y: y + 2, width: Math.max(1, Math.min(1, ratio) * barW), height: 10,
        fill: over ? "var(--danger)" : "var(--precip)",
      }),
      /* The guideline tick is the reference limit, so a bar can be read against it. */
      svg("line", {
        x1: labelW + barW, y1: y, x2: labelW + barW, y2: y + 14,
        stroke: "var(--ink-3)", "stroke-width": 1, "stroke-dasharray": "2 2",
      }),
      svg("text", {
        class: "chart-label", x: width, y: y + 11, "text-anchor": "end",
        fill: over ? "var(--danger)" : "var(--ink-2)", "font-family": "var(--font-num)",
      }, [`${value}`]),
    );
  });

  return svg("svg", {
    viewBox: `0 0 ${width} ${height}`, class: "chart",
    role: "img", "aria-label": "Pollutant concentrations against reference limits, micrograms per cubic metre",
  }, layers);
}

/* ---- sparkline ----------------------------------------------------------------- */

export function sparkline(values, { width = 120, height = 30, colour = "var(--accent)" } = {}) {
  const clean = values.filter((v) => typeof v === "number");
  if (clean.length < 2) return svg("svg", { viewBox: `0 0 ${width} ${height}` });
  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const span = max - min || 1;
  const points = clean.map((v, i) => [
    (i / (clean.length - 1)) * width,
    height - ((v - min) / span) * (height - 4) - 2,
  ]);
  return svg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, "aria-hidden": "true" }, [
    svg("path", { d: linePath(points), fill: "none", stroke: colour, "stroke-width": 1.5 }),
  ]);
}
