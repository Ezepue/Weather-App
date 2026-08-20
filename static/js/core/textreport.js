/* A plain-text rendering of the report, for the clipboard and for anyone who
   would rather read the numbers than the drawing. */

export function textReport(report, formatter) {
  const c = report.current;
  const a = report.advice;
  const lines = [];
  const rule = "-".repeat(52);

  lines.push(`BAROGRAPH — ${report.place.label}`);
  lines.push(`${report.place.localtime_iso.replace("T", " ")} local · ${report.place.lat.toFixed(3)}, ${report.place.lon.toFixed(3)}`);
  lines.push(rule);
  lines.push(`${formatter.text("temperature", c.temp_c)}  ${c.condition.text}`);
  lines.push(`Feels ${formatter.text("temperature", c.feels_c)} (${c.feels_basis})`);
  lines.push(`Wind ${formatter.text("wind", c.wind_kph)} ${c.wind_dir_16}, gusting ${formatter.text("wind", c.wind_gust_kph)}`);
  lines.push(`Humidity ${c.humidity}%  Dew point ${formatter.text("temperature", c.dewpoint_c)}`);
  lines.push(`Pressure ${formatter.text("pressure", c.pressure_mb)} ${a?.pressure_trend?.label || ""}`.trim());
  lines.push(`Cloud ${c.cloud}%  Visibility ${formatter.text("distance", c.vis_km)}  UV ${c.uv}`);

  if (report.air) {
    lines.push(rule);
    lines.push(`Air quality: US AQI ${report.air.aqi_us} — ${report.air.category.label}`);
  }

  if (a) {
    lines.push(rule);
    lines.push(`Comfort ${a.comfort.score}/100 — ${a.comfort.band}`);
    lines.push(`Umbrella: ${a.umbrella.verdict}. ${a.umbrella.detail}`);
    lines.push(`Wear: ${a.outfit.headline}`);
    if (a.outfit.extras.length) lines.push(`  plus ${a.outfit.extras.join(", ")}`);
    lines.push(`Best for: ${a.best_activity.label} (${a.best_activity.score}) — ${a.best_activity.reason}`);
  }

  if (report.daily?.length) {
    lines.push(rule);
    report.daily.forEach((d, i) => {
      const name = i === 0 ? "Today" : formatter.dayName(d.date_epoch, report, { long: true });
      lines.push(`${name.padEnd(10)} ${formatter.temp(d.mintemp_c).padStart(5)} → ${formatter.temp(d.maxtemp_c).padStart(5)}  ${d.condition.text} (${d.chance_rain}% rain)`);
    });
  }

  if (report.alerts?.length) {
    lines.push(rule);
    report.alerts.forEach((alert) => lines.push(`! ${alert.event.toUpperCase()}: ${alert.headline}`));
  }

  lines.push(rule);
  lines.push(`Source: ${report.meta.provider}${report.meta.provider === "demo" ? " (modelled demo data)" : ""}`);
  return lines.join("\n");
}
