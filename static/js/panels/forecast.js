/* Forecast panels: the meteogram, the hour strip, days, and rain windows. */

import { el } from "../ui/dom.js";
import { datum, log, logRow, noData } from "../ui/parts.js";
import { meteogram } from "../draw/charts.js";
import { conditionSymbol } from "../draw/symbols.js";
import { registerPanel } from "./registry.js";

const HOURS_AHEAD = 48;

function upcoming(report, count = HOURS_AHEAD) {
  const now = report.meta.now_epoch;
  return (report.hourly || []).filter((h) => h.t >= now - 3600).slice(0, count);
}

registerPanel({
  id: "meteogram",
  title: "Meteogram",
  order: 80,
  span: 12,
  note: "48 hours",
  available: ({ report }) => (report.hourly || []).length > 1,
  render({ report, formatter }) {
    return el("div", {}, [
      meteogram(upcoming(report), { formatter, report, nowEpoch: report.meta.now_epoch }),
      el("div", { class: "row row--wrap", style: "gap:1rem;margin-top:.5rem" }, [
        el("span", { class: "label label--quiet", text: "── temperature" }),
        el("span", { class: "label label--quiet", text: "┈┈ feels like" }),
        el("span", { class: "label label--quiet", text: "▮ precipitation" }),
        el("span", { class: "label label--quiet", text: "▲▼ sunrise / sunset" }),
        el("span", { class: "label label--quiet", text: "shaded = night" }),
      ]),
    ]);
  },
});

registerPanel({
  id: "hourly",
  title: "Next hours",
  order: 90,
  span: 12,
  available: ({ report }) => (report.hourly || []).length > 1,
  render({ report, formatter }) {
    const now = report.meta.now_epoch;
    const hours = upcoming(report, 24);
    return el("div", { class: "strip" }, hours.map((h, i) => el("div", {
      class: "strip__cell",
      dataset: { now: String(i === 0), night: String(!h.is_day) },
    }, [
      el("span", { class: "strip__hour", text: i === 0 ? "Now" : formatter.hourLabel(h.t, report) }),
      conditionSymbol(h.condition.slug, { isDay: h.is_day, size: 22, title: h.condition.text }),
      el("span", { class: "strip__temp", text: formatter.temp(h.temp_c) }),
      el("span", {
        class: "strip__precip",
        text: h.chance_rain >= 20 ? `${h.chance_rain}%` : "",
      }),
    ])));
  },
});

registerPanel({
  id: "days",
  title: "Days ahead",
  order: 100,
  span: 6,
  available: ({ report }) => (report.daily || []).length > 0,
  render({ report, formatter }) {
    const days = report.daily || [];
    const lows = days.map((d) => d.mintemp_c);
    const highs = days.map((d) => d.maxtemp_c);
    const floor = Math.min(...lows);
    const ceiling = Math.max(...highs);
    const span = Math.max(1, ceiling - floor);

    return el("div", { class: "days" }, days.map((d, i) => el("div", { class: "day" }, [
      el("div", {}, [
        el("div", { class: "day__name", text: i === 0 ? "Today" : formatter.dayName(d.date_epoch, report, { long: true }) }),
        el("div", { class: "day__date", text: formatter.dayDate(d.date_epoch, report) }),
      ]),
      conditionSymbol(d.condition.slug, { size: 22, title: d.condition.text }),
      el("div", {}, [
        el("div", { class: "day__cond", text: d.condition.text }),
        el("div", { class: "day__date", text: `${d.chance_rain}% rain · ${formatter.text("precip", d.totalprecip_mm)} · UV ${d.uv}` }),
      ]),
      el("div", { class: "day__range" }, [
        el("span", { text: formatter.temp(d.mintemp_c) }),
        el("div", { class: "day__track" }, [
          el("div", {
            class: "day__span",
            style: `left:${((d.mintemp_c - floor) / span) * 100}%;width:${Math.max(2, ((d.maxtemp_c - d.mintemp_c) / span) * 100)}%`,
          }),
        ]),
        el("span", { text: formatter.temp(d.maxtemp_c) }),
      ]),
    ])));
  },
});

registerPanel({
  id: "windows",
  title: "Timing",
  order: 110,
  span: 6,
  available: ({ report }) => Boolean(report.advice),
  render({ report, formatter }) {
    const { rain_windows: rain, dry_windows: dry, extremes } = report.advice;
    const rows = [];

    if (rain.length) {
      rain.slice(0, 3).forEach((w) => rows.push(logRow(
        `Rain ${formatter.clock(w.start, report)}–${formatter.clock(w.end, report)}`,
        `${w.total_mm} mm · peak ${w.peak_chance}%`,
        "warn",
      )));
    } else {
      rows.push(logRow("Rain", "None in the next 30 hours", "ok"));
    }

    dry.slice(0, 3).forEach((w) => rows.push(logRow(
      `Dry ${formatter.clock(w.start, report)}–${formatter.clock(w.end, report)}`,
      `${w.hours}h clear`,
      "ok",
    )));

    if (extremes?.warmest) {
      rows.push(logRow("Warmest", `${formatter.temp(extremes.warmest.temp_c)} at ${formatter.clock(extremes.warmest.t, report)}`));
      rows.push(logRow("Coldest", `${formatter.temp(extremes.coldest.temp_c)} at ${formatter.clock(extremes.coldest.t, report)}`));
      rows.push(logRow("24h swing", `${extremes.swing_c}°`));
    }
    rows.push(logRow("Rain next 24h", formatter.text("precip", report.advice.precip_next_24h_mm)));

    return rows.length ? log(rows) : noData();
  },
});
