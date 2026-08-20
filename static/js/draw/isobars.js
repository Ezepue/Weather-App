/* The background isobar field.

   Real synoptic charts are mostly isobars, so the page draws its own from the
   forecast pressure range: closely spaced lines when the gradient is steep,
   open ones when it is slack. It sits behind everything at low opacity and is
   the one place the design lets weather touch the page furniture. */

import { svg } from "../ui/dom.js";

const LINE_COUNT = 9;

export function renderIsobars(host, report, { enabled = true } = {}) {
  host.replaceChildren();
  if (!enabled || !report) return;

  const pressures = (report.hourly || []).map((h) => h.pressure_mb).filter(Boolean);
  if (pressures.length < 2) return;

  const min = Math.min(...pressures);
  const max = Math.max(...pressures);
  const spread = Math.max(1, max - min);
  const current = report.current?.pressure_mb ?? (min + max) / 2;

  /* A tight pressure spread means a slack gradient, so the lines open out. */
  const tightness = Math.min(1, spread / 26);
  const wave = 40 + tightness * 70;
  const gap = 190 - tightness * 90;
  const drift = ((current - min) / spread - 0.5) * 40;

  const paths = [];
  for (let i = 0; i < LINE_COUNT; i += 1) {
    const base = i * gap - gap + drift;
    const phase = i * 0.7;
    const points = [];
    for (let x = -100; x <= 1700; x += 60) {
      const y = base
        + Math.sin(x / 340 + phase) * wave
        + Math.sin(x / 130 + phase * 2.3) * (wave * 0.28);
      points.push(`${x} ${y.toFixed(1)}`);
    }
    paths.push(svg("path", {
      d: `M${points.join("L")}`,
      fill: "none",
      stroke: "var(--isobar)",
      "stroke-width": i % 4 === 0 ? 1.4 : 0.8,
    }));
  }

  host.append(svg("svg", {
    viewBox: "0 0 1600 1000",
    preserveAspectRatio: "xMidYMid slice",
    width: "100%", height: "100%",
    "aria-hidden": "true",
  }, paths));
}
