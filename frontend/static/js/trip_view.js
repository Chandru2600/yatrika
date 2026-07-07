/**
 * AI Travel Planner — Trip View JavaScript
 * Charts, Maps, Interactive Features
 */

"use strict";

document.addEventListener("DOMContentLoaded", () => {

  /* ── Budget Pie Chart ─────────────────────────────────────────── */
  const pieCanvas = document.getElementById("budgetPieChart");
  if (pieCanvas && typeof BUDGET_LABELS !== "undefined" && BUDGET_LABELS.length) {
    const palette = ["#0062FF","#6929C4","#009D9A","#198038","#B28600","#FA4D56","#FF832B"];
    new Chart(pieCanvas, {
      type: "doughnut",
      data: {
        labels:   BUDGET_LABELS.map(l => l.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())),
        datasets: [{
          data:            BUDGET_DATA,
          backgroundColor: palette,
          borderWidth:     2,
          borderColor:     "#fff",
          hoverOffset:     6
        }]
      },
      options: {
        responsive: true,
        cutout:     "60%",
        plugins: {
          legend: {
            position: "bottom",
            labels:   { font: { size: 11 }, boxWidth: 14, padding: 10 }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => ` $${ctx.parsed.toLocaleString()}`
            }
          }
        }
      }
    });
  }

  /* ── Expense Chart ────────────────────────────────────────────── */
  const expCanvas = document.getElementById("expenseChart");
  if (expCanvas && typeof EXP_LABELS !== "undefined" && EXP_LABELS.length) {
    // Aggregate by category
    const agg = {};
    EXP_LABELS.forEach((cat, i) => {
      agg[cat] = (agg[cat] || 0) + EXP_DATA[i];
    });
    new Chart(expCanvas, {
      type: "bar",
      data: {
        labels:   Object.keys(agg).map(l => l.charAt(0).toUpperCase() + l.slice(1)),
        datasets: [{
          label:           "Spent (USD)",
          data:             Object.values(agg),
          backgroundColor: "#0062FF",
          borderRadius:    6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { callback: v => "$" + v } }
        }
      }
    });
  }

  /* ── MapLibre Interactive Map ─────────────────────────────────── */
  const mapContainer = document.getElementById("tripMap");
  if (mapContainer && typeof TRIP_DEST !== "undefined") {
    // Geocode destination using Nominatim (OpenStreetMap, free)
    geocodeAndRenderMap(TRIP_DEST, mapContainer);
  }

  /* ── Animate Budget Bars ──────────────────────────────────────── */
  setTimeout(() => {
    document.querySelectorAll(".budget-bar-fill").forEach(bar => {
      const w = bar.style.width;
      bar.style.width = "0";
      requestAnimationFrame(() => { bar.style.width = w; });
    });
  }, 100);
});


/* ── Map Helper ───────────────────────────────────────────────────── */
async function geocodeAndRenderMap(destination, container) {
  try {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(destination)}&format=json&limit=1`;
    const res  = await fetch(url, { headers: { "Accept-Language": "en" } });
    const data = await res.json();

    let lat = 20, lng = 0;
    if (data && data.length > 0) {
      lat = parseFloat(data[0].lat);
      lng = parseFloat(data[0].lon);
    }

    // MapLibre GL with OpenStreetMap raster tiles
    const map = new maplibregl.Map({
      container: container.id,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors"
          }
        },
        layers: [{
          id:     "osm",
          type:   "raster",
          source: "osm"
        }]
      },
      center: [lng, lat],
      zoom:   11
    });

    // Main destination marker
    new maplibregl.Marker({ color: "#0062FF" })
      .setLngLat([lng, lat])
      .setPopup(new maplibregl.Popup().setHTML(`
        <strong>📍 ${destination}</strong><br>
        <small>Your destination</small>
      `))
      .addTo(map);

    // Search and add POI markers
    const poiTypes = [
      { query: "hotel",           emoji: "🏨", label: "Hotel" },
      { query: "restaurant",      emoji: "🍴", label: "Restaurant" },
      { query: "tourist attraction", emoji: "🎯", label: "Attraction" },
      { query: "hospital",        emoji: "🏥", label: "Hospital" },
    ];

    for (const poi of poiTypes) {
      try {
        const poiUrl = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(poi.query + " in " + destination)}&format=json&limit=3`;
        const poiRes  = await fetch(poiUrl, { headers: { "Accept-Language": "en" } });
        const poiData = await poiRes.json();
        poiData.forEach(p => {
          new maplibregl.Marker({ color: "#6929C4" })
            .setLngLat([parseFloat(p.lon), parseFloat(p.lat)])
            .setPopup(new maplibregl.Popup().setHTML(`
              <strong>${poi.emoji} ${p.display_name.split(",")[0]}</strong><br>
              <small>${poi.label}</small>
            `))
            .addTo(map);
        });
        // Rate-limit Nominatim (1 req/sec)
        await new Promise(r => setTimeout(r, 1000));
      } catch { /* Ignore individual POI errors */ }
    }

  } catch (err) {
    container.innerHTML = `<div class="d-flex align-items-center justify-content-center h-100 text-muted">
      <i class="bi bi-map me-2"></i>Map unavailable (${err.message})
    </div>`;
  }
}
