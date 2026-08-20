/* Saved places, recents and the home pin, persisted locally. */

const KEY = "barograph.places.v2";
const MAX_RECENT = 8;

function read() {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || "{}");
    return {
      saved: Array.isArray(parsed.saved) ? parsed.saved : [],
      recent: Array.isArray(parsed.recent) ? parsed.recent : [],
      home: typeof parsed.home === "string" ? parsed.home : null,
    };
  } catch {
    return { saved: [], recent: [], home: null };
  }
}

function write(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* Storage refusal must not break navigation. */
  }
  return state;
}

export const places = {
  all: read,

  isSaved(label) {
    return read().saved.some((p) => p.label === label);
  },

  toggle(place) {
    const state = read();
    const index = state.saved.findIndex((p) => p.label === place.label);
    if (index >= 0) state.saved.splice(index, 1);
    else state.saved.push(place);
    return write(state);
  },

  remove(label) {
    const state = read();
    state.saved = state.saved.filter((p) => p.label !== label);
    if (state.home === label) state.home = null;
    return write(state);
  },

  move(label, delta) {
    const state = read();
    const index = state.saved.findIndex((p) => p.label === label);
    const target = index + delta;
    if (index < 0 || target < 0 || target >= state.saved.length) return state;
    const [item] = state.saved.splice(index, 1);
    state.saved.splice(target, 0, item);
    return write(state);
  },

  setHome(label) {
    const state = read();
    state.home = state.home === label ? null : label;
    return write(state);
  },

  pushRecent(place) {
    const state = read();
    state.recent = [place, ...state.recent.filter((p) => p.label !== place.label)].slice(0, MAX_RECENT);
    return write(state);
  },

  clearRecent() {
    const state = read();
    state.recent = [];
    return write(state);
  },
};
