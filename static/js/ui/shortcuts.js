/* Keyboard shortcuts.

   Declared as data so the help overlay and the command palette both list the
   real bindings rather than a hand-written copy that drifts. */

export const BINDINGS = [
  { keys: ["/"], label: "Focus search", id: "search" },
  { keys: ["k"], modifier: "meta", label: "Command palette", id: "palette" },
  { keys: ["k"], modifier: "ctrl", label: "Command palette", id: "palette" },
  { keys: ["r"], label: "Refresh now", id: "refresh" },
  { keys: ["u"], label: "Toggle units", id: "units" },
  { keys: ["t"], label: "Toggle theme", id: "theme" },
  { keys: ["c"], label: "Copy report as text", id: "copy" },
  { keys: ["s"], label: "Save or unsave this place", id: "save" },
  { keys: ["l"], label: "Use my location", id: "locate" },
  { keys: ["p"], label: "Print sheet", id: "print" },
  { keys: ["d"], label: "Toggle density", id: "density" },
  { keys: ["?"], label: "Keyboard help", id: "help" },
  { keys: ["Escape"], label: "Close overlays", id: "escape" },
];

function isTypingTarget(target) {
  return target instanceof HTMLElement
    && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
}

export function installShortcuts(handlers) {
  document.addEventListener("keydown", (event) => {
    const typing = isTypingTarget(event.target);

    if (event.key === "Escape") {
      handlers.escape?.();
      return;
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      handlers.palette?.();
      return;
    }
    if (typing || event.metaKey || event.ctrlKey || event.altKey) return;

    const binding = BINDINGS.find((b) => !b.modifier && b.keys.includes(event.key));
    if (!binding) return;
    const handler = handlers[binding.id];
    if (!handler) return;
    event.preventDefault();
    handler();
  });
}
