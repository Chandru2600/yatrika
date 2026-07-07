/**
 * AI Travel Planner — Main JavaScript
 */

"use strict";

/* ── Dark Mode Toggle ─────────────────────────────────────────────── */
(function initTheme() {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeIcon(saved);
})();

function updateThemeIcon(theme) {
  const icon = document.getElementById("themeIcon");
  if (!icon) return;
  icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
}

document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("themeToggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      const next    = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
      updateThemeIcon(next);
    });
  }

  // Auto-dismiss flash messages after 5 seconds
  document.querySelectorAll(".alert-toast").forEach(el => {
    setTimeout(() => {
      const bs = bootstrap.Alert.getOrCreateInstance(el);
      bs.close();
    }, 5000);
  });

  // Activate style/transport card selection
  document.querySelectorAll(".style-card, .transport-card").forEach(card => {
    card.addEventListener("click", function () {
      const group = this.closest(".style-grid, .transport-grid");
      if (group) group.querySelectorAll(".style-card, .transport-card").forEach(c => c.classList.remove("selected"));
      this.classList.add("selected");
    });
  });

  // Interest / requirement chip toggle
  document.querySelectorAll(".interest-chip, .req-chip").forEach(chip => {
    chip.addEventListener("click", function (e) {
      e.preventDefault();
      const input = this.querySelector("input[type='checkbox']");
      const isSelected = this.classList.toggle("selected");
      if (input) {
        input.checked = isSelected;
        // Dispatch change event so any listeners pick it up
        input.dispatchEvent(new Event("change"));
      }
    });
  });
});

/* ── Utility: Toggle Password Visibility ─────────────────────────── */
function togglePwd(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isPassword = input.type === "password";
  input.type = isPassword ? "text" : "password";
  const icon = btn.querySelector("i");
  if (icon) icon.className = isPassword ? "bi bi-eye-slash" : "bi bi-eye";
}

/* ── Print Itinerary ─────────────────────────────────────────────── */
function printItinerary() {
  window.print();
}
