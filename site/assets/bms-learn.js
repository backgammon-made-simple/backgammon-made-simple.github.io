(function () {
  "use strict";

  function initializeAnswerChoices() {
    document.querySelectorAll(".bms-decision-prompt").forEach(function (prompt) {
      const panelId = prompt.dataset.answerPanel;
      const panel = panelId ? document.getElementById(panelId) : null;
      const buttons = Array.from(
        prompt.querySelectorAll(".bms-answer-choice")
      );
      const status = prompt.querySelector(".bms-choice-status");

      buttons.forEach(function (button) {
        button.addEventListener("click", function () {
          buttons.forEach(function (candidate) {
            candidate.setAttribute("aria-pressed", "false");
            candidate.classList.remove("is-selected");
          });

          button.setAttribute("aria-pressed", "true");
          button.classList.add("is-selected");

          if (status) {
            status.textContent =
              "Selected: " +
              button.textContent.trim() +
              ". The working answer is open below; correctness remains unverified.";
          }

          if (panel instanceof HTMLDetailsElement) {
            panel.open = true;
          }
        });
      });
    });
  }

  function initializeLazyAnalyzerFrames() {
    document
      .querySelectorAll("details.bms-analyzer-embed")
      .forEach(function (details) {
        details.addEventListener("toggle", function () {
          if (!details.open) {
            return;
          }

          const iframe = details.querySelector("iframe[data-src]");

          if (!iframe || iframe.getAttribute("src")) {
            return;
          }

          const source = iframe.dataset.src;

          if (!source) {
            return;
          }

          const status = details.querySelector(".bms-analyzer-status");

          if (status) {
            status.textContent = "Loading the analyzer…";
          }

          iframe.addEventListener(
            "load",
            function () {
              if (status) {
                status.textContent = "Analyzer loaded.";
              }
            },
            { once: true }
          );

          iframe.setAttribute("src", source);
          iframe.removeAttribute("data-src");
        });
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initializeAnswerChoices();
    initializeLazyAnalyzerFrames();
  });
})();
