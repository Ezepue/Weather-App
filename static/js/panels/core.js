/* Current-conditions panels. */

import { el } from "../ui/dom.js";
import { badge, datum, log, logRow, meter } from "../ui/parts.js";
import { barometer, comfortArc, stationPlot, thermometer, uvLadder, windRose } from "../draw/instruments.js";
import { conditionSymbol } from "../draw/symbols.js";
import { registerPanel } from "./registry.js";

registerPanel({
  id: "now",
  title: "Current conditions",
  order: 10,
  span: 8,
  render({ report, formatter }) {
    const c = report.current;
    const day = report.daily?.[0];
    const advice = report.advice;
    const feelsDelta = c.feels_c - c.temp_c;

    return el("div", { class: "hero" }, [
      el("div", {}, [
        el("div", { class: "hero__temp" }, [
          el("span", { class: "readout readout--hero", text: formatter.temp(c.temp_c) }),
          el("span", { class: "unit", text: formatter.suffix("temperature") }),
        ]),
        el("div", { class: "row", style: "gap:.5rem;margin-top:.25rem" }, [
          conditionSymbol(c.condition.slug, { isDay: c.is_day, size: 26, title: c.condition.text }),
          el("span", { class: "hero__condition", text: c.condition.text }),
        ]),
        el("p", { class: "hero__feels" }, [
          `Feels ${formatter.temp(c.feels_c)} `,
          el("span", { class: "label label--quiet", text: `${c.feels_basis} · ${formatter.signed(feelsDelta, 1)}°` }),
        ]),
        el("div", { class: "hero__badges" }, [
          day ? badge(`H ${formatter.temp(day.maxtemp_c)} · L ${formatter.temp(day.mintemp_c)}`) : null,
          advice ? badge(advice.comfort.band, advice.comfort.tone) : null,
          advice?.umbrella?.needed ? badge("Rain due", advice.umbrella.tone) : null,
          c.is_day ? null : badge("Night", "neutral"),
        ]),
      ]),
      el("div", { class: "instrument" }, [
        stationPlot(c, formatter, { size: 230 }),
        el("span", { class: "label label--quiet", text: "Station plot · temp / dew / pressure / barb" }),
      ]),
    ]);
  },
});

registerPanel({
  id: "instruments",
  title: "Instruments",
  order: 20,
  span: 4,
  render({ report, formatter }) {
    const c = report.current;
    const day = report.daily?.[0];
    const trend = report.advice?.pressure_trend;
    return el("div", { class: "stack" }, [
      el("div", { class: "instrument-row" }, [
        el("div", { class: "instrument" }, [
          barometer(c.pressure_mb, trend, { size: 170 }),
          el("div", { class: "instrument__caption" }, [
            el("div", { class: "datum__value", text: formatter.text("pressure", c.pressure_mb) }),
            trend ? el("div", {
              class: `caption tone-${trend.direction === "falling" ? "warn" : "ok"}`,
              text: `${{ rising: "▲", falling: "▼", steady: "▬" }[trend.direction] || ""} ${trend.label}`,
            }) : null,
          ]),
        ]),
        day ? el("div", { class: "instrument" }, [
          thermometer(c.temp_c, day.mintemp_c, day.maxtemp_c, { height: 150 }),
          el("span", { class: "label label--quiet", text: "Range today" }),
        ]) : null,
      ]),
      trend?.note ? el("p", { class: "caption", text: trend.note }) : null,
    ]);
  },
});

registerPanel({
  id: "wind",
  title: "Wind",
  order: 30,
  span: 4,
  render({ report, formatter }) {
    const c = report.current;
    const gustDelta = (c.wind_gust_kph ?? c.wind_kph) - c.wind_kph;
    return el("div", { class: "stack" }, [
      el("div", { class: "row", style: "gap:1rem;align-items:center" }, [
        windRose(c.wind_dir_deg, c.wind_kph, c.barb, { size: 150 }),
        el("div", { class: "stack grow" }, [
          datum("Speed", formatter.text("wind", c.wind_kph), `${c.wind_dir_16} · ${Math.round(c.wind_dir_deg)}°`, { large: true }),
          datum("Gusts", formatter.text("wind", c.wind_gust_kph), gustDelta > 20 ? "Squally" : null),
          datum("Beaufort", `${c.beaufort_force} · ${c.beaufort_name}`),
        ]),
      ]),
      el("p", { class: "caption", text: `Barb reads ${c.barb?.knots ?? 0} knots from the ${c.wind_dir_16}.` }),
    ]);
  },
});

registerPanel({
  id: "comfort",
  title: "Comfort",
  order: 40,
  span: 4,
  available: ({ report }) => Boolean(report.advice),
  render({ report, formatter }) {
    const { comfort, outfit } = report.advice;
    return el("div", { class: "stack" }, [
      el("div", { class: "row", style: "gap:1rem" }, [
        comfortArc(comfort.score, comfort.tone, { size: 140 }),
        el("div", { class: "stack grow" }, [
          el("span", { class: `datum__value datum__value--lg tone-${comfort.tone}`, text: comfort.band }),
          comfort.detractors.length
            ? el("div", { class: "stack", style: "gap:.35rem" },
                comfort.detractors.map((d) =>
                  el("div", { class: "caption", text: `${d.cause} costs ${d.cost} points` })))
            : el("p", { class: "caption", text: "Nothing is working against you." }),
        ]),
      ]),
      el("div", { style: "border-top:1px solid var(--rule);padding-top:.75rem" }, [
        el("span", { class: "label", text: "Wear" }),
        el("p", { style: "margin:.25rem 0", text: outfit.headline }),
        el("p", { class: "caption", text: outfit.layers.join(" · ") }),
        outfit.extras.length ? el("p", { class: "caption tone-warn", text: outfit.extras.join(" · ") }) : null,
      ]),
    ]);
  },
});

registerPanel({
  id: "verdict",
  title: "Answers",
  order: 50,
  span: 4,
  available: ({ report }) => Boolean(report.advice),
  render({ report, formatter }) {
    const { umbrella, sunscreen, best_activity: best, air_out: airOut, frost } = report.advice;
    return el("div", { class: "stack" }, [
      el("div", {}, [
        el("span", { class: "label", text: "Umbrella?" }),
        el("p", { class: `datum__value tone-${umbrella.tone}`, text: umbrella.verdict }),
        el("p", { class: "caption", text: umbrella.detail }),
      ]),
      el("div", {}, [
        el("span", { class: "label", text: "Sunscreen?" }),
        el("p", { class: `datum__value tone-${sunscreen.tone}`, text: sunscreen.needed ? "Yes" : "No" }),
        el("p", { class: "caption", text: sunscreen.verdict }),
      ]),
      el("div", {}, [
        el("span", { class: "label", text: "Best use of today" }),
        el("p", { class: "datum__value", text: `${best.label} · ${best.score}` }),
        el("p", { class: "caption", text: best.reason }),
      ]),
      airOut ? el("div", {}, [
        el("span", { class: "label", text: "Open the windows" }),
        el("p", { class: "caption", text: `${formatter.clock(airOut.t, report)} — ${formatter.temp(airOut.temp_c)} outside, dry` }),
      ]) : null,
      frost?.risk ? el("p", { class: "caption tone-warn", text: frost.note }) : null,
    ]);
  },
});

registerPanel({
  id: "uv",
  title: "Ultraviolet",
  order: 60,
  span: 4,
  render({ report, formatter }) {
    const c = report.current;
    const advice = report.advice;
    return el("div", { class: "stack" }, [
      el("div", { class: "row row--between" }, [
        datum("Now", String(c.uv), c.uv_band?.label, { large: true }),
        datum("Peak today", String(advice?.uv_max_today ?? "--"),
          advice?.sunscreen?.peak_at ? formatter.clock(advice.sunscreen.peak_at, report) : null),
      ]),
      uvLadder(c.uv),
      advice?.sunscreen?.burn_minutes
        ? el("p", { class: "caption", text: `Fair skin burns in roughly ${advice.sunscreen.burn_minutes} minutes at today's peak.` })
        : el("p", { class: "caption", text: "No burn risk today." }),
    ]);
  },
});

registerPanel({
  id: "readings",
  title: "Full reading",
  order: 70,
  span: 4,
  render({ report, formatter }) {
    const c = report.current;
    const trend = report.advice?.pressure_trend;
    return log([
      logRow("Temperature", formatter.text("temperature", c.temp_c)),
      logRow("Feels like", formatter.text("temperature", c.feels_c)),
      logRow("Dew point", formatter.text("temperature", c.dewpoint_c)),
      logRow("Humidity", `${c.humidity}%`),
      logRow("Pressure", `${formatter.text("pressure", c.pressure_mb)}${trend?.delta_3h ? ` (${formatter.signed(trend.delta_3h, 1)}/3h)` : ""}`),
      logRow("Wind", `${formatter.text("wind", c.wind_kph)} ${c.wind_dir_16}`),
      logRow("Gusts", formatter.text("wind", c.wind_gust_kph)),
      logRow("Cloud cover", `${c.cloud}%`),
      logRow("Visibility", formatter.text("distance", c.vis_km)),
      logRow("Precipitation", formatter.text("precip", c.precip_mm)),
      c.heat_index_c !== null ? logRow("Heat index", formatter.text("temperature", c.heat_index_c)) : null,
      c.wind_chill_c !== null ? logRow("Wind chill", formatter.text("temperature", c.wind_chill_c)) : null,
      c.humidex_c !== null ? logRow("Humidex", formatter.text("temperature", c.humidex_c)) : null,
    ]);
  },
});
