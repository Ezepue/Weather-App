/* Air, sky and sea. */

import { el } from "../ui/dom.js";
import { badge, datum, log, logRow, noData } from "../ui/parts.js";
import { pollutantBars, sunPath } from "../draw/charts.js";
import { moonDisc } from "../draw/instruments.js";
import { registerPanel } from "./registry.js";

registerPanel({
  id: "alerts",
  title: "Warnings in force",
  order: 5,
  span: 12,
  available: ({ report }) => (report.alerts || []).length > 0,
  render({ report, formatter }) {
    return el("div", {}, (report.alerts || []).map((alert) => el("div", {
      class: `alert tone-${alert.tone}`,
    }, [
      el("div", { class: "alert__head" }, [
        el("span", { class: "alert__event", text: `${alert.event} · ${alert.severity}` }),
        alert.expires_epoch
          ? el("span", { class: "label label--quiet", text: `until ${formatter.clock(alert.expires_epoch, report)}` })
          : null,
      ]),
      el("div", { class: "alert__headline", text: alert.headline }),
      alert.description ? el("div", { class: "alert__body", text: alert.description }) : null,
      alert.areas ? el("div", { class: "label label--quiet", text: alert.areas }) : null,
    ])));
  },
});

registerPanel({
  id: "air",
  title: "Air quality",
  order: 120,
  span: 6,
  available: ({ report }) => Boolean(report.air),
  render({ report }) {
    const air = report.air;
    return el("div", { class: "stack" }, [
      el("div", { class: "row row--between row--wrap" }, [
        datum("US AQI", String(air.aqi_us ?? "--"), air.category.label, { large: true, tone: air.category.tone }),
        datum("Dominant", (air.dominant || "--").replace("pm2_5", "PM2.5").replace("pm10", "PM10")),
        air.defra_index ? datum("UK DEFRA", `${air.defra_index}/10`, air.defra_label) : null,
      ]),
      el("p", { class: "caption", text: air.category.advice }),
      pollutantBars(air),
      el("p", { class: "label label--quiet", text: `Dashed tick = reference limit · ${air.basis}` }),
    ]);
  },
});

registerPanel({
  id: "sun",
  title: "Sun",
  order: 130,
  span: 6,
  available: ({ report }) => Boolean(report.astro),
  render({ report, formatter }) {
    const a = report.astro;
    const delta = a.daylight_delta_minutes;
    return el("div", { class: "stack" }, [
      sunPath(a, { formatter, report, nowEpoch: report.meta.now_epoch }),
      el("div", { class: "datum-grid" }, [
        datum("Sunrise", formatter.clock(a.sunrise_epoch, report)),
        datum("Sunset", formatter.clock(a.sunset_epoch, report)),
        datum("Daylight", formatter.duration(a.daylight_minutes),
          delta === null || delta === undefined ? null : `${formatter.signed(delta, 0)} min vs yesterday`),
        datum("Solar noon", formatter.clock(a.solar_noon_epoch, report)),
        datum("Golden hour", a.golden_evening_start_epoch ? `from ${formatter.clock(a.golden_evening_start_epoch, report)}` : "--"),
        datum("Civil dusk", formatter.clock(a.dusk_epoch, report)),
      ]),
    ]);
  },
});

registerPanel({
  id: "moon",
  title: "Moon",
  order: 75,
  span: 4,
  available: ({ report }) => Boolean(report.astro),
  render({ report, formatter }) {
    const a = report.astro;
    return el("div", { class: "instrument" }, [
      moonDisc(a.moon_illumination, a.moon_waxing, { size: 104, phase: a.moon_phase }),
      el("div", { class: "datum__value", text: a.moon_phase }),
      el("div", { class: "caption", text: `${Math.round(a.moon_illumination)}% lit · ${a.moon_age_days} days old` }),
      a.moonrise_epoch || a.moonset_epoch
        ? el("div", { class: "caption", text: `Rise ${formatter.clock(a.moonrise_epoch, report)} · Set ${formatter.clock(a.moonset_epoch, report)}` })
        : null,
    ]);
  },
});

registerPanel({
  id: "marine",
  title: "Sea state",
  order: 150,
  span: 6,
  available: ({ report }) => Boolean(report.marine),
  render({ report, formatter }) {
    const m = report.marine;
    return log([
      logRow("Wave height", m.wave_m !== null ? `${m.wave_m} m` : "--"),
      logRow("Period", m.wave_period_s !== null ? `${m.wave_period_s} s` : "--"),
      logRow("Swell direction", m.swell_dir_deg !== null ? `${Math.round(m.swell_dir_deg)}°` : "--"),
      logRow("Water", formatter.text("temperature", m.water_temp_c)),
    ]);
  },
});
