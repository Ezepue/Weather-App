/* A minimal observable store. One source of truth; panels subscribe to it. */

export function createStore(initial = {}) {
  let state = { ...initial };
  const subscribers = new Set();

  return {
    get() {
      return state;
    },
    set(patch) {
      const next = typeof patch === "function" ? patch(state) : patch;
      const changed = Object.keys(next).some((key) => state[key] !== next[key]);
      if (!changed) return state;
      state = { ...state, ...next };
      subscribers.forEach((fn) => fn(state));
      return state;
    },
    subscribe(fn) {
      subscribers.add(fn);
      return () => subscribers.delete(fn);
    },
  };
}
