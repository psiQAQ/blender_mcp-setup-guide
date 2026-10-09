/* All downloads and installation instructions work without JavaScript. */
(() => {
  "use strict";
  const panels = [...document.querySelectorAll("[data-channel-panel]")];
  const buttons = [...document.querySelectorAll("[data-channel]")];
  const selector = document.querySelector(".channel-selector");
  const languageLink = document.querySelector(".language");
  let selectedChannel = document.body.dataset.initialChannel;
  const syncLanguageLink = () => {
    const selectedButton = buttons.find(button => button.dataset.channel === selectedChannel);
    if (!languageLink || !selectedButton) return;
    const target = new URL(selectedButton.dataset.languageUrl, location.href);
    target.hash = location.hash;
    languageLink.href = target.href;
  };
  const choose = (id, updateHash = false) => {
    if (!panels.some(panel => panel.id === id)) return;
    selectedChannel = id;
    panels.forEach(panel => { panel.hidden = panel.id !== id; });
    buttons.forEach(button => button.setAttribute("aria-pressed", String(button.dataset.channel === id)));
    if (updateHash) history.replaceState(null, "", `#${id}`);
    syncLanguageLink();
  };
  if (selector && panels.length) {
    selector.hidden = false;
    const hash = location.hash.slice(1);
    choose(panels.some(panel => panel.id === hash) ? hash : document.body.dataset.initialChannel);
    buttons.forEach(button => button.addEventListener("click", () => choose(button.dataset.channel, true)));
    window.addEventListener("hashchange", () => {
      choose(location.hash.slice(1));
      syncLanguageLink();
    });
  }
  const status = document.getElementById("copy-status");
  document.querySelectorAll("[data-copy-target]").forEach(button => {
    button.hidden = false;
    const originalLabel = button.textContent;
    let resetTimer;
    button.addEventListener("click", async () => {
      const input = document.getElementById(button.dataset.copyTarget);
      try {
        await navigator.clipboard.writeText(input.value);
        status.textContent = document.body.dataset.copySuccess;
        button.textContent = document.body.dataset.copySuccess;
        window.clearTimeout(resetTimer);
        resetTimer = window.setTimeout(() => { button.textContent = originalLabel; }, 2000);
      } catch {
        input.focus();
        input.select();
        status.textContent = document.body.dataset.copyFailure;
      }
    });
  });
})();
