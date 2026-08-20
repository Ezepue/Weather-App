/* Panel registry.

   Panels declare themselves; the shell only knows how to lay out whatever is
   registered. Adding a panel is one file and one call - nothing central needs
   editing, which is the same reason the backend's scorers are a registry. */

const PANELS = [];

export function registerPanel(spec) {
  if (!spec.id || typeof spec.render !== "function") {
    throw new Error(`Panel "${spec.id}" needs an id and a render function`);
  }
  PANELS.push({ span: 4, group: "main", available: () => true, ...spec });
  PANELS.sort((a, b) => a.order - b.order);
  return spec;
}

export function allPanels() {
  return PANELS.slice();
}

export function visiblePanels(context, hidden = []) {
  return PANELS.filter((panel) => !hidden.includes(panel.id) && panel.available(context));
}

export function findPanel(id) {
  return PANELS.find((panel) => panel.id === id);
}
