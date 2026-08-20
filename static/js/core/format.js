/* Display conversion. The API always speaks metric; this is the only place
   that turns those numbers into whatever the reader asked for. */

const CONVERT = {
  temperature: {
    c: (v) => v,
    f: (v) => v * 9 / 5 + 32,
  },
  wind: {
    kph: (v) => v,
    mph: (v) => v * 0.621371,
    ms: (v) => v / 3.6,
    kn: (v) => v * 0.539957,
    bft: (v) => beaufort(v),
  },
  pressure: {
    mb: (v) => v,
    inhg: (v) => v * 0.02953,
    mmhg: (v) => v * 0.750062,
  },
  precip: {
    mm: (v) => v,
    in: (v) => v / 25.4,
  },
  distance: {
    km: (v) => v,
    mi: (v) => v * 0.621371,
  },
};

const SUFFIX = {
  temperature: { c: "°C", f: "°F" },
  wind: { kph: "km/h", mph: "mph", ms: "m/s", kn: "kn", bft: "Bft" },
  pressure: { mb: "mb", inhg: "inHg", mmhg: "mmHg" },
  precip: { mm: "mm", in: "in" },
  distance: { km: "km", mi: "mi" },
};

const PRECISION = {
  temperature: { c: 0, f: 0 },
  wind: { kph: 0, mph: 0, ms: 1, kn: 0, bft: 0 },
  pressure: { mb: 0, inhg: 2, mmhg: 0 },
  precip: { mm: 1, in: 2 },
  distance: { km: 0, mi: 0 },
};

const BEAUFORT_LIMITS = [1, 6, 12, 20, 29, 39, 50, 62, 75, 89, 103, 118];

function beaufort(kph) {
  for (let i = 0; i < BEAUFORT_LIMITS.length; i += 1) {
    if (kph < BEAUFORT_LIMITS[i]) return i;
  }
  return 12;
}

export function createFormatter(settings) {
  const unitFor = (kind) => settings[kind] || Object.keys(CONVERT[kind])[0];

  function value(kind, metric, { decimals } = {}) {
    if (metric === null || metric === undefined || Number.isNaN(metric)) return null;
    const unit = unitFor(kind);
    const converted = CONVERT[kind][unit](metric);
    const places = decimals ?? PRECISION[kind][unit] ?? 0;
    return Number(converted.toFixed(places));
  }

  function text(kind, metric, options = {}) {
    const v = value(kind, metric, options);
    if (v === null) return "--";
    const unit = options.bare ? "" : ` ${SUFFIX[kind][unitFor(kind)]}`;
    return `${v}${unit}`;
  }

  function temp(metric, { bare = true } = {}) {
    const v = value("temperature", metric);
    if (v === null) return "--";
    return bare ? `${v}°` : `${v}${SUFFIX.temperature[unitFor("temperature")]}`;
  }

  const zoneFor = (report) => {
    const offset = report?.place?.utc_offset_hours ?? 0;
    return offset * 3600;
  };

  /* Times are rendered in the place's local zone, not the reader's, so a
     forecast for Tokyo reads as Tokyo sees it. */
  function clock(epoch, report) {
    if (!epoch) return "--";
    const shifted = new Date((epoch + zoneFor(report)) * 1000);
    const h = shifted.getUTCHours();
    const m = String(shifted.getUTCMinutes()).padStart(2, "0");
    if (settings.clock === "12") {
      const suffix = h < 12 ? "am" : "pm";
      const hour = h % 12 === 0 ? 12 : h % 12;
      return `${hour}:${m}${suffix}`;
    }
    return `${String(h).padStart(2, "0")}:${m}`;
  }

  function hourLabel(epoch, report) {
    if (!epoch) return "--";
    const shifted = new Date((epoch + zoneFor(report)) * 1000);
    const h = shifted.getUTCHours();
    if (settings.clock === "12") {
      const suffix = h < 12 ? "a" : "p";
      return `${h % 12 === 0 ? 12 : h % 12}${suffix}`;
    }
    return `${String(h).padStart(2, "0")}`;
  }

  function dayName(epoch, report, { long = false } = {}) {
    if (!epoch) return "--";
    const shifted = new Date((epoch + zoneFor(report)) * 1000);
    return shifted.toLocaleDateString(undefined, {
      weekday: long ? "long" : "short",
      timeZone: "UTC",
    });
  }

  function dayDate(epoch, report) {
    if (!epoch) return "--";
    const shifted = new Date((epoch + zoneFor(report)) * 1000);
    return shifted.toLocaleDateString(undefined, { day: "numeric", month: "short", timeZone: "UTC" });
  }

  function relative(epoch, nowEpoch) {
    if (!epoch) return "--";
    const seconds = Math.round((epoch - nowEpoch));
    const abs = Math.abs(seconds);
    if (abs < 60) return seconds >= 0 ? "now" : "just now";
    const minutes = Math.round(abs / 60);
    if (minutes < 60) return seconds > 0 ? `in ${minutes} min` : `${minutes} min ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 36) return seconds > 0 ? `in ${hours}h` : `${hours}h ago`;
    return `${Math.round(hours / 24)}d ${seconds > 0 ? "away" : "ago"}`;
  }

  function duration(minutes) {
    if (minutes === null || minutes === undefined) return "--";
    const h = Math.floor(minutes / 60);
    const m = Math.round(minutes % 60);
    return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
  }

  function signed(n, digits = 0) {
    if (n === null || n === undefined) return "--";
    const v = Number(n.toFixed(digits));
    return v > 0 ? `+${v}` : `${v}`;
  }

  return {
    settings, value, text, temp, clock, hourLabel, dayName, dayDate,
    relative, duration, signed,
    unitFor,
    suffix: (kind) => SUFFIX[kind][unitFor(kind)],
  };
}
