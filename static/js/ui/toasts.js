/* Transient messages. Announced politely so screen readers get them too. */

import { el } from "./dom.js";

let host = null;

function ensureHost() {
  if (host) return host;
  host = el("div", { class: "toasts", role: "status", "aria-live": "polite" });
  document.body.append(host);
  return host;
}

export function toast(message, { tone = "neutral", timeout = 4200, action } = {}) {
  const node = el("div", { class: "toast" }, [
    el("span", { class: tone !== "neutral" ? `tone-${tone}` : null, text: message }),
    action ? el("button", {
      class: "btn btn--ghost", type: "button", text: action.label,
      onclick: () => { action.run(); node.remove(); },
    }) : null,
  ]);
  ensureHost().append(node);
  if (timeout) setTimeout(() => node.remove(), timeout);
  return node;
}
