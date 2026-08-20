/* Command palette. Commands are supplied by the shell, so this file knows how
   to filter and choose, and nothing about what the commands do. */

import { clear, el } from "./dom.js";

export function createPalette({ backdrop, input, list, getCommands }) {
  let filtered = [];
  let active = 0;

  function draw() {
    clear(list);
    filtered.forEach((command, i) => {
      list.append(el("li", {
        class: "palette__item",
        role: "option",
        "aria-selected": String(i === active),
        onmousedown: (event) => { event.preventDefault(); choose(i); },
        onmouseenter: () => { active = i; draw(); },
      }, [
        el("span", {}, [
          el("span", { text: command.label }),
          command.detail ? el("span", { class: "palette__hint", text: `  ${command.detail}` }) : null,
        ]),
        command.hint ? el("span", { class: "palette__hint", text: command.hint }) : null,
      ]));
    });
    if (!filtered.length) {
      list.append(el("li", { class: "palette__item palette__hint", text: "No matching command" }));
    }
  }

  function filter(term) {
    const needle = term.trim().toLowerCase();
    const commands = getCommands();
    filtered = needle
      ? commands.filter((c) => `${c.label} ${c.detail || ""} ${c.keywords || ""}`.toLowerCase().includes(needle))
      : commands;
    active = 0;
    draw();
  }

  function open() {
    backdrop.hidden = false;
    input.value = "";
    filter("");
    input.focus();
  }

  function close() {
    backdrop.hidden = true;
  }

  function choose(index) {
    const command = filtered[index];
    if (!command) return;
    close();
    command.run();
  }

  input.addEventListener("input", () => filter(input.value));

  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      active = (active + 1) % Math.max(1, filtered.length);
      draw();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      active = (active - 1 + filtered.length) % Math.max(1, filtered.length);
      draw();
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(active);
    } else if (event.key === "Escape") {
      close();
    }
  });

  backdrop.addEventListener("mousedown", (event) => {
    if (event.target === backdrop) close();
  });

  return { open, close, isOpen: () => !backdrop.hidden };
}
