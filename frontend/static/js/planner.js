/**
 * AI Travel Planner — Planner Form JavaScript
 * Multi-step form with live preview and weather fetch
 */

"use strict";

let currentStep = 1;

/* ── Step Navigation ──────────────────────────────────────────────── */
function nextStep(n) {
  if (!validateStep(currentStep)) return;
  goToStep(n);
}

function prevStep(n) {
  goToStep(n);
}

function goToStep(n) {
  document.getElementById(`step-${currentStep}`).classList.add("d-none");
  document.getElementById(`step-${currentStep}`).classList.remove("active");

  currentStep = n;
  const stepEl = document.getElementById(`step-${n}`);
  stepEl.classList.remove("d-none");
  stepEl.classList.add("active");

  updateStepper();
  if (n === 4) renderTripSummary();
}

function updateStepper() {
  document.querySelectorAll(".planner-stepper .step").forEach((el, idx) => {
    const stepNum = idx + 1;
    el.classList.remove("active", "done");
    if (stepNum === currentStep) el.classList.add("active");
    else if (stepNum < currentStep) el.classList.add("done");
  });
}

/* ── Step Validation ──────────────────────────────────────────────── */
function validateStep(step) {
  if (step === 1) {
    const dest  = document.getElementById("destinationInput").value.trim();
    const start = document.getElementById("startDate").value;
    const end   = document.getElementById("endDate").value;
    if (!dest) { showAlert("Please enter a destination."); return false; }
    if (!start) { showAlert("Please select a start date."); return false; }
    if (!end)   { showAlert("Please select an end date."); return false; }
    if (start > end) { showAlert("End date must be after start date."); return false; }
  }
  return true;
}

function showAlert(msg) {
  const container = document.querySelector(".flash-container") || createFlashContainer();
  const div = document.createElement("div");
  div.className = "alert alert-warning alert-dismissible fade show alert-toast";
  div.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  container.prepend(div);
  setTimeout(() => bootstrap.Alert.getOrCreateInstance(div).close(), 4000);
}

function createFlashContainer() {
  const div = document.createElement("div");
  div.className = "flash-container";
  document.body.appendChild(div);
  return div;
}

/* ── Date → Num Days Sync ─────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  const startDate = document.getElementById("startDate");
  const endDate   = document.getElementById("endDate");
  const numDays   = document.getElementById("numDays");

  if (startDate && endDate && numDays) {
    function calcDays() {
      const s = new Date(startDate.value);
      const e = new Date(endDate.value);
      if (!isNaN(s) && !isNaN(e) && e >= s) {
        numDays.value = Math.ceil((e - s) / 86400000) + 1;
      }
    }
    startDate.addEventListener("change", calcDays);
    endDate.addEventListener("change", calcDays);
    // Set min date to today
    const today = new Date().toISOString().split("T")[0];
    startDate.min = today;
    endDate.min   = today;
  }

  // Budget range ↔ input sync
  const budgetInput = document.getElementById("budgetInput");
  const budgetRange = document.getElementById("budgetRange");
  if (budgetInput && budgetRange) {
    budgetInput.addEventListener("input", () => {
      budgetRange.value = budgetInput.value;
    });
  }

  // Form submit loading state
  const form = document.getElementById("plannerForm");
  if (form) {
    form.addEventListener("submit", () => {
      const btn = document.getElementById("generateBtn");
      if (btn) {
        btn.querySelector(".btn-default-text").classList.add("d-none");
        btn.querySelector(".btn-loading-text").classList.remove("d-none");
        btn.disabled = true;
      }
    });
  }

  // Weather preview button
  const weatherBtn = document.getElementById("checkWeatherBtn");
  if (weatherBtn) {
    weatherBtn.addEventListener("click", async () => {
      const dest = document.getElementById("destinationInput").value.trim();
      if (!dest) { showAlert("Enter a destination first."); return; }
      const preview = document.getElementById("weatherPreview");
      preview.classList.remove("d-none");
      preview.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Fetching weather for ${dest}…`;
      try {
        const res  = await fetch(`/planner/api/weather/${encodeURIComponent(dest)}`);
        const data = await res.json();
        const c    = data.current;
        if (c && !c.error) {
          preview.innerHTML = `
            <img src="https://openweathermap.org/img/wn/${c.icon}.png" width="32" alt="" />
            <strong>${c.city}, ${c.country}</strong>: ${c.temperature}°C · ${c.description}
            · 💧${c.humidity}% · 💨${c.wind_speed}m/s`;
        } else {
          preview.innerHTML = `<i class="bi bi-exclamation-triangle me-1 text-warning"></i>${c.error || "Weather unavailable"}`;
        }
      } catch {
        preview.innerHTML = "Could not fetch weather data.";
      }
    });
  }
});

/* ── Budget Sync ──────────────────────────────────────────────────── */
function syncBudget(val) {
  const input = document.getElementById("budgetInput");
  if (input) input.value = val;
}

/* ── Counter ──────────────────────────────────────────────────────── */
function changeCount(name, delta) {
  const input = document.querySelector(`input[name="${name}"]`);
  if (!input) return;
  const min = parseInt(input.min || 1);
  const max = parseInt(input.max || 999);
  const val = Math.min(max, Math.max(min, parseInt(input.value || 1) + delta));
  input.value = val;
}

/* ── Trip Summary Preview (Step 4) ───────────────────────────────── */
function renderTripSummary() {
  const dest      = document.getElementById("destinationInput")?.value || "—";
  const start     = document.getElementById("startDate")?.value || "—";
  const end       = document.getElementById("endDate")?.value || "—";
  const days      = document.getElementById("numDays")?.value || "—";
  const budget    = document.getElementById("budgetInput")?.value || "—";
  const travelers = document.getElementById("numTravelers")?.value || "1";
  const style     = document.querySelector('input[name="travel_style"]:checked')?.value || "—";
  const transport = document.querySelector('input[name="transport"]:checked')?.value || "—";
  const interests = [...document.querySelectorAll('input[name="interests"]:checked')].map(i => i.value).join(", ") || "None";
  const reqs      = [...document.querySelectorAll('input[name="special_requirements"]:checked')].map(i => i.value).join(", ") || "None";

  const container = document.getElementById("tripSummary");
  if (!container) return;
  container.innerHTML = `
    <div class="tsf-row"><span>Destination</span><strong>${dest}</strong></div>
    <div class="tsf-row"><span>Dates</span><strong>${start} → ${end} (${days} days)</strong></div>
    <div class="tsf-row"><span>Travelers</span><strong>${travelers}</strong></div>
    <div class="tsf-row"><span>Budget</span><strong>$${parseFloat(budget).toLocaleString()} USD</strong></div>
    <div class="tsf-row"><span>Travel Style</span><strong>${style.charAt(0).toUpperCase() + style.slice(1)}</strong></div>
    <div class="tsf-row"><span>Transport</span><strong>${transport.charAt(0).toUpperCase() + transport.slice(1)}</strong></div>
    <div class="tsf-row"><span>Interests</span><strong>${interests}</strong></div>
    <div class="tsf-row"><span>Special Requirements</span><strong>${reqs}</strong></div>
  `;
}
