/* Place search with type-ahead. Full keyboard control: arrows move, Enter
   accepts, Escape closes without changing the field. */

import { api } from "../core/api.js";
import { clear, el } from "./dom.js";

const DEBOUNCE_MS = 180;

export function createSearch({ input, results, onSelect }) {
  let items = [];
  let active = -1;
  let timer = null;

  function close() {
    clear(results);
    items = [];
    active = -1;
    input.setAttribute("aria-expanded", "false");
  }

  function highlight(index) {
    active = index;
    Array.from(results.children).forEach((node, i) => {
      node.setAttribute("aria-selected", String(i === index));
      if (i === index) node.scrollIntoView({ block: "nearest" });
    });
    input.setAttribute("aria-activedescendant", index >= 0 ? `search-option-${index}` : "");
  }

  function choose(index) {
    const item = items[index];
    if (!item) return;
    input.value = item.name;
    close();
    onSelect(item);
  }

  function draw(rows) {
    clear(results);
    items = rows;
    rows.forEach((row, i) => {
      results.append(el("li", {
        class: "search__option",
        id: `search-option-${i}`,
        role: "option",
        "aria-selected": "false",
        onmousedown: (event) => { event.preventDefault(); choose(i); },
        onmouseenter: () => highlight(i),
      }, [
        el("span", {}, [
          el("strong", { text: row.name }),
          row.region || row.country
            ? el("span", { class: "caption", text: ` ${[row.region, row.country].filter(Boolean).join(", ")}` })
            : null,
        ]),
        row.lat !== null && row.lat !== undefined
          ? el("span", { class: "coords", text: `${Number(row.lat).toFixed(2)}, ${Number(row.lon).toFixed(2)}` })
          : null,
      ]));
    });
    input.setAttribute("aria-expanded", rows.length ? "true" : "false");
    highlight(rows.length ? 0 : -1);
  }

  async function run(query) {
    if (query.trim().length < 2) return close();
    try {
      const payload = await api.search(query);
      draw(payload.results || []);
    } catch (error) {
      if (error.name !== "AbortError") close();
    }
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => run(input.value), DEBOUNCE_MS);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" && items.length) {
      event.preventDefault();
      highlight((active + 1) % items.length);
    } else if (event.key === "ArrowUp" && items.length) {
      event.preventDefault();
      highlight((active - 1 + items.length) % items.length);
    } else if (event.key === "Enter") {
      if (active >= 0 && items.length) {
        event.preventDefault();
        choose(active);
      }
    } else if (event.key === "Escape") {
      close();
      input.blur();
    }
  });

  input.addEventListener("blur", () => setTimeout(close, 120));

  return { close };
}
