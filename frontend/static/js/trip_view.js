/**
 * AI Travel Planner — Trip View JavaScript
 * Tab switcher charts, day planner drag-drop, timeline generator, OSRM route connector statistics, MapLibre
 */

"use strict";

const State = {
  tripId: TRIP_ID,
  dest: TRIP_DEST,
  days: TRAVEL_DAYS,
  travelers: TRAVELERS,
  budget: BUDGET,
  transport: TRANSPORT_MODE,
  style: STYLE,
  selectedAttractions: [],
  dayPlanner: {},
  weatherData: WEATHER_DATA,
  routeData: null,
  mapInstance: null,
  currentPlannerDay: 1,
  customPoolActivities: []
};

// Formatting helpers
const fmtINR = n => '₹' + Math.round(n).toLocaleString('en-IN');
const fmtHrs = m => { const h=Math.floor(m/60),r=m%60; return h?(r?`${h}h ${r}m`:`${h}h`):`${r}m`; };
const fmtKm  = m => m >= 1000 ? (m/1000).toFixed(1)+' km' : Math.round(m)+' m';

function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371, dLat = (lat2-lat1)*Math.PI/180, dLon = (lon2-lon1)*Math.PI/180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

// OpenStreetMap routing proxy helper
async function fetchRoute(fromLat, fromLon, toLat, toLon) {
  const profile = State.transport === 'bike' ? 'bike' : 'car';
  const coords = `${fromLon},${fromLat};${toLon},${toLat}`;
  const url = `/planner/api/osrm?profile=${profile}&coords=${encodeURIComponent(coords)}`;
  try {
    const res  = await fetch(url);
    if (!res.ok) return null;
    const data = await res.json();
    if (data.code !== 'Ok') return null;
    return { distM: data.routes[0].distance, durS: data.routes[0].duration };
  } catch { return null; }
}

document.addEventListener("DOMContentLoaded", () => {
  // Populate selectedAttractions and dayPlanner from database JSON payload
  State.dayPlanner = {};

  if (ITINERARY_DATA.day_planner && Object.keys(ITINERARY_DATA.day_planner).length) {
    for (let k in ITINERARY_DATA.day_planner) {
      State.dayPlanner[parseInt(k)] = ITINERARY_DATA.day_planner[k];
    }
  }

  // Parse days from ITINERARY_DATA.days or ITINERARY_DATA.itinerary.days
  const daysList = ITINERARY_DATA.days || (ITINERARY_DATA.itinerary && ITINERARY_DATA.itinerary.days) || [];
  const parsedSel = [];

  if (daysList.length) {
    daysList.forEach((day, idx) => {
      const d = parseInt(day.day || day.day_number || (idx + 1));
      if (!State.dayPlanner[d]) {
        State.dayPlanner[d] = { morning: [], afternoon: [], evening: [], night: [] };
      }

      ['morning', 'afternoon', 'evening'].forEach(zone => {
        if (State.dayPlanner[d][zone] && State.dayPlanner[d][zone].length) return;
        const slot = day[zone];
        if (!slot) return;

        if (Array.isArray(slot.places) && slot.places.length) {
          slot.places.forEach(pl => {
            const a = {
              id: pl.id || ('osm_' + Math.floor(Math.random()*1000000)),
              name: pl.name,
              icon: pl.icon || '📍',
              cat: pl.category || 'Sightseeing',
              dur: pl.duration || '1.5h',
              fee: pl.raw_fee || 0,
              lat: pl.lat,
              lon: pl.lon,
              dist: pl.dist || 0
            };
            parsedSel.push(a);
            State.dayPlanner[d][zone].push({
              id: a.id, icon: a.icon, name: a.name, dur: a.dur, type: 'attraction', category: a.cat, fee: a.fee
            });
          });
        } else if (typeof slot === 'object') {
          const actName = slot.activity || slot.name || slot.place || 'Sightseeing';
          const actTime = slot.time || '';
          const actDur = slot.duration || '2h';
          const icon = zone === 'morning' ? '🌅' : (zone === 'afternoon' ? '☀️' : '🌆');
          const a = {
            id: 'gen_' + d + '_' + zone,
            icon: icon,
            name: actName,
            dur: actDur,
            time: actTime,
            type: zone === 'afternoon' && actName.toLowerCase().includes('lunch') ? 'food' : 'attraction',
            category: 'Sightseeing',
            fee: slot.fee_inr || 0,
            proximity: slot.proximity || '',
            description: slot.description || ''
          };
          parsedSel.push(a);
          State.dayPlanner[d][zone].push(a);
        } else if (typeof slot === 'string') {
          const icon = zone === 'morning' ? '🌅' : (zone === 'afternoon' ? '☀️' : '🌆');
          State.dayPlanner[d][zone].push({
            id: 'gen_' + d + '_' + zone,
            icon: icon,
            name: slot,
            dur: '2h',
            type: 'attraction',
            category: 'Sightseeing'
          });
        }
      });
    });
  }

  // Set selected attractions if available
  if (ITINERARY_DATA.selected_attractions && ITINERARY_DATA.selected_attractions.length) {
    State.selectedAttractions = ITINERARY_DATA.selected_attractions;
  } else if (parsedSel.length) {
    State.selectedAttractions = parsedSel;
  }

  // Ensure dayPlanner elements exist for every day and have curated activities
  for (let d = 1; d <= State.days; d++) {
    if (!State.dayPlanner[d]) {
      State.dayPlanner[d] = { morning: [], afternoon: [], evening: [], night: [] };
    }
    const dp = State.dayPlanner[d];
    if (!dp.morning.length && !dp.afternoon.length && !dp.evening.length) {
      dp.morning.push({
        id: `auto_${d}_morn`,
        icon: '🌅',
        name: `Day ${d} Sightseeing Loop & Viewpoints`,
        dur: '2.5h',
        type: 'attraction',
        category: 'Sightseeing'
      });
      dp.afternoon.push({
        id: `auto_${d}_aftn`,
        icon: '☀️',
        name: `Authentic Regional Lunch & Local Exploration`,
        dur: '2h',
        type: 'food',
        category: 'Dining'
      });
      dp.evening.push({
        id: `auto_${d}_eve`,
        icon: '🌆',
        name: `Sunset Point, Bazaar Walk & Dinner`,
        dur: '2.5h',
        type: 'leisure',
        category: 'Leisure'
      });
    }
  }

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
          legend: { position: "bottom", labels: { font: { size: 11 }, boxWidth: 14, padding: 10 } },
          tooltip: { callbacks: { label: (ctx) => ` ₹${ctx.parsed.toLocaleString('en-IN')}` } }
        }
      }
    });
  }

  /* ── Expense Chart ────────────────────────────────────────────── */
  const expCanvas = document.getElementById("expenseChart");
  if (expCanvas && typeof EXP_LABELS !== "undefined" && EXP_LABELS.length) {
    const agg = {};
    EXP_LABELS.forEach((cat, i) => {
      agg[cat] = (agg[cat] || 0) + EXP_DATA[i];
    });
    new Chart(expCanvas, {
      type: "bar",
      data: {
        labels:   Object.keys(agg).map(l => l.charAt(0).toUpperCase() + l.slice(1)),
        datasets: [{
          label:           "Spent (INR)",
          data:             Object.values(agg),
          backgroundColor: "#0062FF",
          borderRadius:    6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { callback: v => "₹" + v } }
        }
      }
    });
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

/* ── STEP 5: Day Planner Rendering & Interactive Actions ───────────────── */
window.renderDayPlanner = function() {
  const sel = State.selectedAttractions;

  // Render Day Selector Tabs with modern pill design
  const ds = document.getElementById('daySelector');
  if (ds) {
    ds.innerHTML = Array.from({length: State.days}, (_, i) => {
      const dNum = i + 1;
      const activeClass = dNum === State.currentPlannerDay ? 'active' : '';
      return `<button type="button" class="day-btn ${activeClass}" onclick="switchPlannerDay(${dNum}, this)">Day ${dNum}</button>`;
    }).join('');
  }

  const assignedIds = new Set();
  Object.values(State.dayPlanner).forEach(dayObj => {
    ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
      (dayObj[zone] || []).forEach(act => {
        if (act.id) assignedIds.add(String(act.id));
      });
    });
  });

  // Populate drop zones for active day
  const currentDayPlan = State.dayPlanner[State.currentPlannerDay] || { morning: [], afternoon: [], evening: [], night: [] };
  ['morning', 'afternoon', 'evening'].forEach(zone => {
    const dz = document.getElementById(zone + '-drop');
    if (!dz) return;
    const items = currentDayPlan[zone] || [];
    const isShared = typeof IS_SHARED !== 'undefined' && IS_SHARED;
    dz.innerHTML = items.length ? items.map((act, idx) => {
      const attMatch = State.selectedAttractions.find(a => String(a.id) === String(act.id) || a.name === act.name);
      const lat = (act.lat !== undefined && act.lat !== null) ? act.lat : (attMatch ? attMatch.lat : null);
      const lon = (act.lon !== undefined && act.lon !== null) ? act.lon : (attMatch ? attMatch.lon : null);
      const latAttr = (lat !== null && isFinite(lat)) ? lat : '';
      const lonAttr = (lon !== null && isFinite(lon)) ? lon : '';

      return `
      <div class="activity-card-planned activity-card-interactive" draggable="true"
           data-id="${act.id}" data-type="${act.type || 'attraction'}" data-zone="${zone}" data-index="${idx}"
           data-name="${act.name.replace(/"/g, '&quot;')}" data-lat="${latAttr}" data-lon="${lonAttr}"
           onclick="window.focusCardElementOnMap(this)" title="Click to view on Map">
        <div class="d-flex align-items-center gap-2 flex-grow-1">
          <span class="act-icon fs-5">${act.icon || '📍'}</span>
          <div class="flex-grow-1">
            <div class="act-name fw-bold text-navy small">${act.name}</div>
            ${act.time ? `<div class="extra-small text-muted"><i class="bi bi-clock me-1"></i>${act.time}</div>` : ''}
          </div>
          <span class="badge bg-light text-muted border extra-small">${act.dur || '1.5h'}</span>
        </div>
        ${isShared ? '' : `
        <div class="d-flex align-items-center gap-1 ms-2" onclick="event.stopPropagation();">
          <div class="reorder-btn-group">
            <button type="button" class="btn btn-sm btn-reorder-move ${idx === 0 && zone === 'morning' ? 'disabled' : ''}"
                    onclick="window.reorderPlannedActivity(${State.currentPlannerDay}, '${zone}', ${idx}, -1); event.stopPropagation();"
                    title="Move Earlier in itinerary" aria-label="Move Earlier">▲ Earlier</button>
            <button type="button" class="btn btn-sm btn-reorder-move ${idx === items.length - 1 && zone === 'evening' ? 'disabled' : ''}"
                    onclick="window.reorderPlannedActivity(${State.currentPlannerDay}, '${zone}', ${idx}, 1); event.stopPropagation();"
                    title="Move Later in itinerary" aria-label="Move Later">▼ Later</button>
          </div>
          <button type="button" class="btn btn-sm btn-light border py-0 px-2 extra-small" onclick="movePlannedActivity(${State.currentPlannerDay}, '${zone}', ${idx}); event.stopPropagation();" title="Shift to next time slot">➔</button>
          <button type="button" class="btn btn-sm btn-outline-danger border-0 py-0 px-1" onclick="removePlannedActivity(${State.currentPlannerDay}, '${zone}', ${idx}); event.stopPropagation();" title="Remove activity">×</button>
        </div>`}
      </div>
      `;
    }).join('') : `<div class="text-center text-muted py-4 small"><i class="bi bi-calendar-plus me-1"></i> No activities yet. Click any item below to add!</div>`;
    dz.querySelectorAll('.activity-card-planned').forEach(initCardDrag);
  });

  // Render the Unscheduled Activities Pool with 1-click slot buttons
  const pool = document.getElementById('poolItems');
  if (pool) {
    const unassignedAttractions = sel.filter(a => !assignedIds.has(String(a.id)));
    const poolActs = [
      ...unassignedAttractions.map(a => ({ id: a.id, icon: a.icon || '📍', name: a.name, dur: typeof a.dur === 'number' ? fmtHrs(a.dur) : (a.dur || '1.5h'), type: 'attraction' })),
      { id: 'breakfast', icon: '🥞', name: 'Breakfast', dur: '30m', type: 'food' },
      { id: 'lunch', icon: '🍛', name: 'Regional Lunch', dur: '45m', type: 'food' },
      { id: 'dinner', icon: '🍽️', name: 'Dinner & Cafe', dur: '60m', type: 'food' },
      { id: 'rest', icon: '😴', name: 'Rest at Hotel', dur: '60m', type: 'leisure' },
      { id: 'shopping', icon: '🛍️', name: 'Local Shopping & Spices', dur: '45m', type: 'leisure' },
      { id: 'viewpoint', icon: '🌄', name: 'Scenic Sunset Viewpoint', dur: '1.5h', type: 'attraction' },
      { id: 'depart', icon: '🚗', name: 'Travel to Destination', dur: '2h', type: 'travel' },
      { id: 'return', icon: '🔙', name: 'Return Journey', dur: '2h', type: 'travel' },
      ...(State.customPoolActivities || [])
    ];
    pool.innerHTML = poolActs.map(a => `
      <div class="pool-activity-card" draggable="true" data-id="${a.id}" data-type="${a.type}" onclick="quickAddActivity('${a.id}', 'morning')">
        <span class="act-icon">${a.icon}</span>
        <span class="act-name">${a.name}</span>
        <span class="act-dur-badge">${a.dur}</span>
        <div class="slot-add-btns" onclick="event.stopPropagation();">
          <button type="button" class="btn-slot-pill" onclick="quickAddActivity('${a.id}', 'morning')" title="Add to Morning">+ Morn</button>
          <button type="button" class="btn-slot-pill" onclick="quickAddActivity('${a.id}', 'afternoon')" title="Add to Afternoon">+ Aftn</button>
          <button type="button" class="btn-slot-pill" onclick="quickAddActivity('${a.id}', 'evening')" title="Add to Evening">+ Eve</button>
        </div>
      </div>`).join('');
    pool.querySelectorAll('.pool-activity-card').forEach(initCardDrag);
  }
};

/* ── Toast Helper ─────────────────────────────────────────────────── */
function showToast(message, type = 'info') {
  let toastEl = document.getElementById('plannerToast');
  if (!toastEl) {
    toastEl = document.createElement('div');
    toastEl.id = 'plannerToast';
    toastEl.className = 'reorder-save-toast';
    document.body.appendChild(toastEl);
  }
  const icons = {
    success: '✓',
    danger: '⚠️',
    warning: '📍',
    info: 'ℹ️'
  };
  toastEl.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> <span>${message}</span>`;
  toastEl.classList.add('show');
  clearTimeout(toastEl._timer);
  toastEl._timer = setTimeout(() => {
    toastEl.classList.remove('show');
  }, 2800);
}
window.showMapToast = showToast;

function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

/* ── Mobile Itinerary Reordering ──────────────────────────────────── */
window.reorderPlannedActivity = function(day, currentZone, idx, direction) {
  if (!State.dayPlanner[day] || !State.dayPlanner[day][currentZone]) return;
  const list = State.dayPlanner[day][currentZone];
  if (idx < 0 || idx >= list.length) return;

  const zones = ['morning', 'afternoon', 'evening'];
  const zoneIdx = zones.indexOf(currentZone);

  if (direction === -1) {
    // Move earlier
    if (idx > 0) {
      const temp = list[idx];
      list[idx] = list[idx - 1];
      list[idx - 1] = temp;
    } else if (zoneIdx > 0) {
      const prevZone = zones[zoneIdx - 1];
      if (!State.dayPlanner[day][prevZone]) State.dayPlanner[day][prevZone] = [];
      const item = list.splice(idx, 1)[0];
      State.dayPlanner[day][prevZone].push(item);
    }
  } else if (direction === 1) {
    // Move later
    if (idx < list.length - 1) {
      const temp = list[idx];
      list[idx] = list[idx + 1];
      list[idx + 1] = temp;
    } else if (zoneIdx < zones.length - 1) {
      const nextZone = zones[zoneIdx + 1];
      if (!State.dayPlanner[day][nextZone]) State.dayPlanner[day][nextZone] = [];
      const item = list.splice(idx, 1)[0];
      State.dayPlanner[day][nextZone].unshift(item);
    }
  }

  renderDayPlanner();
  if (typeof window.renderTimeline === 'function') {
    window.renderTimeline();
  }

  // Persist seamlessly to server
  savePlannerChangesToServer(true);
};

window.quickAddActivity = function(idStr, targetZone) {
  let actObject = null;
  const attraction = State.selectedAttractions.find(a => String(a.id) === String(idStr));
  if (attraction) {
    actObject = {
      id: attraction.id,
      icon: attraction.icon || '📍',
      name: attraction.name,
      dur: typeof attraction.dur === 'number' ? fmtHrs(attraction.dur) : (attraction.dur || '1.5h'),
      type: 'attraction',
      category: attraction.cat || 'Sightseeing',
      lat: attraction.lat || attraction.latitude,
      lon: attraction.lon || attraction.longitude
    };
  } else if (String(idStr).startsWith('custom_')) {
    const customAct = State.customPoolActivities.find(c => String(c.id) === String(idStr));
    if (customAct) actObject = { ...customAct };
  } else {
    const defaults = {
      breakfast: { id: 'breakfast', icon: '🥞', name: 'Breakfast', dur: '30m', type: 'food' },
      lunch: { id: 'lunch', icon: '🍛', name: 'Regional Lunch', dur: '45m', type: 'food' },
      dinner: { id: 'dinner', icon: '🍽️', name: 'Dinner & Cafe', dur: '60m', type: 'food' },
      rest: { id: 'rest', icon: '😴', name: 'Rest at Hotel', dur: '60m', type: 'leisure' },
      shopping: { id: 'shopping', icon: '🛍️', name: 'Local Shopping & Spices', dur: '45m', type: 'leisure' },
      viewpoint: { id: 'viewpoint', icon: '🌄', name: 'Scenic Sunset Viewpoint', dur: '1.5h', type: 'attraction' },
      depart: { id: 'depart', icon: '🚗', name: 'Travel to Destination', dur: '2h', type: 'travel' },
      return: { id: 'return', icon: '🔙', name: 'Return Journey', dur: '2h', type: 'travel' }
    };
    actObject = defaults[idStr];
  }

  if (!actObject) return;

  const currentDay = State.currentPlannerDay || 1;
  if (!State.dayPlanner[currentDay]) {
    State.dayPlanner[currentDay] = { morning: [], afternoon: [], evening: [], night: [] };
  }
  const zone = targetZone || 'morning';
  State.dayPlanner[currentDay][zone].push(actObject);
  renderDayPlanner();
  savePlannerChangesToServer(true);
};

window.movePlannedActivity = function(day, currentZone, idx) {
  if (!State.dayPlanner[day] || !State.dayPlanner[day][currentZone]) return;
  const act = State.dayPlanner[day][currentZone].splice(idx, 1)[0];
  if (!act) return;
  const nextZone = currentZone === 'morning' ? 'afternoon' : (currentZone === 'afternoon' ? 'evening' : 'morning');
  if (!State.dayPlanner[day][nextZone]) State.dayPlanner[day][nextZone] = [];
  State.dayPlanner[day][nextZone].push(act);
  renderDayPlanner();
  savePlannerChangesToServer(true);
};

window.switchPlannerDay = function(dNum, btn) {
  State.currentPlannerDay = dNum;
  renderDayPlanner();

  if (btn) {
    document.querySelectorAll('.day-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }
};

window.allowDrop = function(e) {
  e.preventDefault();
};

window.dropActivity = function(e, zone) {
  e.preventDefault();
  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    const { id, type, sourceZone, sourceIndex } = data;

    let actObject = null;
    const idStr = String(id);

    const attraction = State.selectedAttractions.find(a => String(a.id) === idStr);
    if (attraction) {
      actObject = { id: attraction.id, icon: attraction.icon, name: attraction.name, dur: fmtHrs(attraction.dur), type: 'attraction', category: attraction.cat || '', fee: attraction.fee || 0, lat: attraction.lat, lon: attraction.lon, dist: attraction.dist || 0 };
    } else if (idStr.startsWith('custom_')) {
      const customAct = State.customPoolActivities.find(c => String(c.id) === idStr);
      if (customAct) {
        actObject = { id: customAct.id, icon: customAct.icon, name: customAct.name, dur: customAct.dur, type: customAct.type };
      }
    } else {
      const defaults = {
        breakfast: { id: 'breakfast', icon: '🥞', name: 'Breakfast', dur: '30m', type: 'food' },
        lunch: { id: 'lunch', icon: '🍛', name: 'Lunch', dur: '45m', type: 'food' },
        dinner: { id: 'dinner', icon: '🍽️', name: 'Dinner', dur: '60m', type: 'food' },
        rest: { id: 'rest', icon: '😴', name: 'Rest at Hotel', dur: '60m', type: 'leisure' },
        shopping: { id: 'shopping', icon: '🛍️', name: 'Local Shopping', dur: '45m', type: 'leisure' },
        depart: { id: 'depart', icon: '🚗', name: 'Travel to Destination', dur: '2h', type: 'travel' },
        return: { id: 'return', icon: '🔙', name: 'Return Journey', dur: '2h', type: 'travel' },
      };
      actObject = defaults[idStr];
    }

    if (!actObject) return;

    if (sourceZone !== null && sourceIndex !== null) {
      State.dayPlanner[State.currentPlannerDay][sourceZone].splice(sourceIndex, 1);
    }

    if (!State.dayPlanner[State.currentPlannerDay][zone]) {
      State.dayPlanner[State.currentPlannerDay][zone] = [];
    }
    State.dayPlanner[State.currentPlannerDay][zone].push(actObject);

    renderDayPlanner();
    savePlannerChangesToServer(true);
  } catch (err) {
    console.error(err);
  }
};

function initCardDrag(card) {
  if (typeof IS_SHARED !== 'undefined' && IS_SHARED) {
    card.setAttribute('draggable', 'false');
    card.style.cursor = 'default';
    return;
  }
  card.addEventListener('dragstart', e => {
    e.dataTransfer.setData('text/plain', JSON.stringify({
      id: card.dataset.id,
      type: card.dataset.type,
      sourceZone: card.dataset.zone || null,
      sourceIndex: card.dataset.index !== undefined ? parseInt(card.dataset.index) : null
    }));
  });
}

window.removePlannedActivity = function(day, zone, idx) {
  if (State.dayPlanner[day] && State.dayPlanner[day][zone]) {
    State.dayPlanner[day][zone].splice(idx, 1);
    renderDayPlanner();
    savePlannerChangesToServer(true);
  }
};

window.addCustomActivityPool = function() {
  const nameInput = document.getElementById('customActName');
  const typeSelect = document.getElementById('customActType');
  const durInput = document.getElementById('customActDur');
  
  const name = nameInput.value.trim();
  const durVal = durInput.value.trim() || '1h';
  if (!name) return;
  
  const type = typeSelect.value;
  const icons = { leisure: '🎯', food: '🍽️', travel: '🚗' };
  const icon = icons[type] || '✨';
  
  const id = 'custom_' + Date.now();
  State.customPoolActivities.push({ id, icon, name, dur: durVal, type });
  
  nameInput.value = '';
  durInput.value = '';
  renderDayPlanner();
};

window.savePlannerChangesToServer = async function(silent = false) {
  const payload = { day_planner: State.dayPlanner };

  try {
    const response = await fetch(`/planner/${State.tripId}/update_planner`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (result.success) {
      showToast('✓ Itinerary schedule saved', 'success');
    } else {
      showToast(`❌ Update failed: ${result.error || 'Server error'}`, 'danger');
    }
  } catch (err) {
    console.error(err);
    if (!silent) {
      showToast('❌ Error connecting to server', 'danger');
    }
  }
};

/* ── Bidirectional Map & Card Synchronization ────────────────────── */
window.focusCardElementOnMap = function(cardEl) {
  if (!cardEl) return;
  const id = cardEl.dataset.id || '';
  const name = cardEl.dataset.name || cardEl.querySelector('.act-name, strong, .rs-name')?.textContent || '';
  const lat = cardEl.dataset.lat ? Number(cardEl.dataset.lat) : null;
  const lon = cardEl.dataset.lon ? Number(cardEl.dataset.lon) : null;
  window.focusActivityOnMap(id, name, lat, lon);
};

window.focusActivityOnMap = function(actId, actName, lat, lon) {
  // If coordinates weren't supplied directly, attempt lookup
  if ((lat === null || lat === undefined || !isFinite(lat)) && State.selectedAttractions) {
    const match = State.selectedAttractions.find(a => String(a.id) === String(actId) || a.name === actName);
    if (match && isFinite(match.lat) && isFinite(match.lon)) {
      lat = Number(match.lat);
      lon = Number(match.lon);
    }
  }

  // Handle missing coordinates gracefully
  if (lat === null || lat === undefined || !isFinite(lat) || lon === null || lon === undefined || !isFinite(lon)) {
    showToast(`📍 Location coordinates unavailable for "${actName || 'this activity'}"`, 'warning');
    return;
  }

  // Ensure map tab is active if on another tab
  const mapTabBtn = document.querySelector('#itineraryTabs a[href="#tab-map"]');
  if (mapTabBtn && !mapTabBtn.classList.contains('active')) {
    if (window.bootstrap && bootstrap.Tab) {
      bootstrap.Tab.getOrCreateInstance(mapTabBtn).show();
    } else {
      mapTabBtn.click();
    }
  }

  // Ensure map renders and resizes if tab was hidden
  setTimeout(() => {
    if (State.mapInstance) {
      State.mapInstance.resize();
      State.mapInstance.flyTo({
        center: [Number(lon), Number(lat)],
        zoom: 15,
        speed: 1.3,
        essential: true
      });

      // Find marker and open popup
      let marker = null;
      if (State.mapMarkers) {
        if (actId && State.mapMarkers.has(String(actId))) {
          marker = State.mapMarkers.get(String(actId));
        } else if (actName && State.mapMarkers.has(String(actName).toLowerCase().trim())) {
          marker = State.mapMarkers.get(String(actName).toLowerCase().trim());
        }
      }

      if (marker) {
        const popup = marker.getPopup();
        if (popup && !popup.isOpen()) {
          marker.togglePopup();
        }
        const pinEl = marker.getElement();
        if (pinEl) {
          pinEl.classList.add('map-pin-pulse');
          setTimeout(() => pinEl.classList.remove('map-pin-pulse'), 2500);
        }
      }
    }
  }, 120);
};

window.highlightAndScrollToActivity = function(actId, actName) {
  const normName = String(actName || '').toLowerCase().trim();
  const allCards = document.querySelectorAll('.activity-card-planned, .slot-row-item, .route-stop, .tourist-sight-card');
  let target = null;

  for (const card of allCards) {
    if (actId && card.dataset.id === String(actId)) {
      target = card;
      break;
    }
    const cardName = String(card.dataset.name || card.querySelector('.act-name, strong, .rs-name')?.textContent || '').toLowerCase().trim();
    if (normName && (cardName === normName || cardName.includes(normName) || normName.includes(cardName))) {
      target = card;
      break;
    }
  }

  if (target) {
    target.classList.add('activity-card-highlighted');
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => {
      target.classList.remove('activity-card-highlighted');
    }, 2500);
  }
};

/* ── STEP 6: Smart Timeline ────────────────────────────────────── */
window.renderTimeline = function() {
  const cont = document.getElementById('smartTimeline');
  if (!cont) return;

  const sel = State.selectedAttractions;
  if (!sel.length) {
    cont.innerHTML = `<div class="text-center py-5 text-muted"><p>No attractions selected for this trip.</p></div>`;
    return;
  }

  const days = State.days;
  const days_plan = [];

  for (let d = 1; d <= days; d++) {
    const dayObj = State.dayPlanner[d] || { morning: [], afternoon: [], evening: [], night: [] };
    const dayAttractions = [];
    ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
      (dayObj[zone] || []).forEach(act => {
        if (act && act.name) {
          let attraction = State.selectedAttractions.find(a => String(a.id) === String(act.id) || a.name === act.name);
          if (!attraction) {
            attraction = {
              id: act.id || ('act_' + Math.random()),
              name: act.name,
              icon: act.icon || '📍',
              cat: act.category || (act.type === 'food' ? 'Food & Dining' : 'Sightseeing'),
              dur: typeof act.dur === 'number' ? act.dur : 90,
              dist: act.dist || 4.5,
              fee: act.fee || 0,
              lat: act.lat,
              lon: act.lon
            };
          }
          if (!dayAttractions.some(x => x.name === attraction.name)) {
            dayAttractions.push(attraction);
          }
        }
      });
    });

    if (!dayAttractions.length && State.selectedAttractions.length) {
      const idxStart = ((d - 1) * 2) % State.selectedAttractions.length;
      dayAttractions.push(State.selectedAttractions[idxStart]);
      if (State.selectedAttractions.length > idxStart + 1) {
        dayAttractions.push(State.selectedAttractions[idxStart + 1]);
      }
    }

    days_plan.push(dayAttractions);
  }


  const dayLabels = [
    'Arrival & Explore', 'Deep Exploration', 'Adventure Day',
    'Cultural Immersion', 'Leisure & Relax', 'Hidden Gems',
    'Final Day & Departure'
  ];

  cont.innerHTML = `
    <div class="tl-days-wrap">
      ${days_plan.map((attrs, d) => `
        <div class="tl-day-col">
          <div class="tl-day-header">
            <span class="tl-day-num">Day ${d+1}</span>
            <span class="tl-day-label">${dayLabels[d] || ('Exploration Day '+(d+1))}</span>
            <span class="tl-day-count">${attrs.length} stops</span>
          </div>
          <div class="tl-events">
            ${buildPlannedDayEvents(d+1, attrs, days_plan.length).map(e => buildEventCard(e)).join('')}
          </div>
        </div>
      `).join('')}
    </div>`;
};

function buildPlannedDayEvents(dayNum, attrs, totalDays) {
  const events = [];
  const fmtTime = (totalMins) => {
    const h = Math.floor(totalMins / 60);
    const m = totalMins % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  };

  let minutesCursor = 8 * 60; // Start at 08:00

  if (dayNum === 1) {
    events.push({
      time: fmtTime(minutesCursor),
      type: 'hotel',
      icon: '🏨',
      title: `Arrive at ${State.dest.split(',')[0]} & Check-in`,
      subtitle: 'Hotel registration and check-in',
      priority: 'high',
      duration: 30
    });
    minutesCursor += 30;
  }

  attrs.forEach((a, i) => {
    const travelMin = Math.max(10, Math.round((a.dist || 0) / 35 * 60));
    events.push({
      time: fmtTime(minutesCursor),
      type: 'travel',
      icon: State.transport === 'bike' ? '🏍️' : '🚗',
      title: `Travel to ${a.name}`,
      subtitle: `~${a.dist || 0} km · ~${travelMin} min by ${State.transport}`,
      priority: 'low',
      duration: travelMin
    });
    minutesCursor += travelMin;

    const visitHrs = ((a.dur || 90) / 60).toFixed(1).replace('.0', '');
    events.push({
      time: fmtTime(minutesCursor),
      type: 'attraction',
      icon: a.icon,
      title: a.name,
      subtitle: `${a.cat} · ${visitHrs}h visit`,
      priority: 'medium',
      duration: a.dur || 90
    });
    minutesCursor += a.dur || 90;
  });

  if (events.length > 0 && dayNum < totalDays) {
    events.push({
      time: fmtTime(minutesCursor),
      type: 'hotel',
      icon: '🏨',
      title: 'Back to Hotel',
      subtitle: 'Rest up for tomorrow',
      priority: 'low',
      duration: 0
    });
  } else if (events.length > 0) {
    events.push({
      time: fmtTime(minutesCursor),
      type: 'travel',
      icon: '🏠',
      title: 'Return to Starting Location',
      subtitle: 'Safe travels home! 🎉',
      priority: 'high',
      duration: 0
    });
  }

  return events;
}

function buildEventCard(e) {
  const colorMap = {
    hotel:      '#6929C4',
    food:       '#009D9A',
    travel:     '#0062FF',
    attraction: '#198038',
  };
  const color = colorMap[e.type] || '#6929C4';
  return `
    <div class="tl-event tl-event-${e.type}">
      <div class="tl-event-time">${e.time}</div>
      <div class="tl-event-dot" style="background:${color}">${e.icon}</div>
      <div class="tl-event-body">
        <div class="tl-event-title">${e.title}</div>
        <div class="tl-event-sub">${e.subtitle}</div>
        ${e.duration ? `<div class="tl-event-dur">⏱ ${e.duration >= 60 ? Math.floor(e.duration/60)+'h'+(e.duration%60?(' '+e.duration%60+'m'):'') : e.duration+'m'}</div>` : ''}
      </div>
      <span class="tl-event-badge tl-badge-${e.priority || 'medium'}">${(e.priority||'medium').toUpperCase()}</span>
    </div>`;
}

/* ── STEP 7: Route Planner stops sequence ────────────────────────── */
window.renderRoute = async function() {
  const sel = State.selectedAttractions;
  const rt  = document.getElementById('routeTimeline');
  const js  = document.getElementById('journeyStats');
  const cb  = document.getElementById('costBreakdown');
  if (!rt) return;

  const tIcon = State.transport === 'bike' ? '🏍️' : '🚗';

  const stops = [
    { type:'hotel', icon:'🏨', name:'Your Base Camp Hotel', lat:null, lon:null },
    ...sel.map(a=>({ id:a.id, type:'attraction', icon:a.icon, name:a.name, lat:a.lat || a.latitude, lon:a.lon || a.longitude, dur:a.dur, fee:a.fee, cat:a.cat })),
    { type:'hotel', icon:'🏨', name:'Return to Base Camp', lat:null, lon:null }
  ];


  rt.innerHTML = `<div class="d-flex align-items-center gap-2 p-3"><span class="spinner-border spinner-border-sm"></span><span>Loading road distance info…</span></div>`;

  let totalDistM = 0, totalDurS = 0;
  let html = '';

  for (let i = 0; i < stops.length; i++) {
    const s = stops[i];
    html += `<div class="route-stop activity-card-interactive"
                  data-id="${s.id || ''}"
                  data-name="${(s.name || '').replace(/"/g, '&quot;')}"
                  data-lat="${s.lat || ''}"
                  data-lon="${s.lon || ''}"
                  onclick="window.focusCardElementOnMap(this)"
                  title="Click to view on Map">
      <div class="rs-pin ${s.type}">${s.icon}</div>
      <div class="rs-info">
        <div class="rs-name">${s.name}</div>
        ${s.cat ? `<div class="rs-details"><span class="rs-detail-item">${s.cat}</span>${s.dur?`<span class="rs-detail-item">⏱ ${fmtHrs(s.dur)}</span>`:''}${s.fee?`<span class="rs-detail-item">🎟 ${s.fee}</span>`:''}</div>` : ''}
      </div>
    </div>`;

    if (i < stops.length - 1 && stops[i].lat && stops[i+1].lat) {
      const r = await fetchRoute(stops[i].lat, stops[i].lon, stops[i+1].lat, stops[i+1].lon);
      const dkm = r ? (r.distM/1000).toFixed(1) : '—';
      const tmin = r ? Math.round(r.durS/60) : '—';
      if (r) { totalDistM += r.distM; totalDurS += r.durS; }
      html += `<div class="rs-travel-connector">
        <span class="mode-icon">${tIcon}</span>
        <span class="travel-info">${dkm} km · ${typeof tmin==='number'?fmtHrs(tmin):tmin} · via road</span>
      </div>`;
    }
  }

  rt.innerHTML = html;

  const distKm = totalDistM > 0 ? (totalDistM/1000).toFixed(1) : sel.reduce((s,a)=>s+(a.dist||0), 0);
  const driveMin = totalDurS > 0 ? Math.round(totalDurS/60) : Math.round(distKm / 45 * 60);

  const fuelCost  = State.transport==='bike'?Math.round(distKm/30*110):Math.round(distKm/12*100);
  const tollCost  = Math.round(distKm/10*5);
  const entryCost = sel.reduce((s,a)=>(s+(a.fee||0)),0);
  const foodEst   = State.travelers*State.days*600;
  const hotelEst  = State.days*2000;

  if (js) js.innerHTML = [
    ['🛣️ Total Road Distance', distKm+' km'],
    ['🚗 Driving Time',         fmtHrs(driveMin)],
    ['🌙 Trip Duration',        State.days+' Days'],
    ['👥 Travelers',            State.travelers],
    ['🚗 Transport Mode',       State.transport.charAt(0).toUpperCase()+State.transport.slice(1)],
  ].map(([l,v])=>`<div class="js-row d-flex justify-content-between py-2 border-bottom" style="font-size:0.88rem;"><span class="js-label text-muted">${l}</span><span class="js-value fw-bold">${v}</span></div>`).join('');

  if (cb) cb.innerHTML = [
    ['⛽ Fuel',         fmtINR(fuelCost)],
    ['🚧 Tolls',        fmtINR(tollCost)],
    ['🎟️ Entry Fees',  fmtINR(entryCost)],
    ['🍽️ Food (est.)', fmtINR(foodEst)],
    ['🏨 Hotel (est.)', fmtINR(hotelEst)],
  ].map(([l,v])=>`<div class="cb-row d-flex justify-content-between py-1" style="font-size:0.88rem;"><span class="cb-label">${l}</span><span class="cb-amount fw-bold">${v}</span></div>`).join('') +
  `<hr><div class="cb-row d-flex justify-content-between pt-1"><span class="cb-label fw-bold">💰 Total Estimate</span><span class="cb-amount fw-bold text-primary">${fmtINR(fuelCost+tollCost+entryCost+foodEst+hotelEst)}</span></div>`;
};

/* ── STEP 8: MapLibre Interactive Map ───────────────────────────── */
window.renderMap = function() {
  const sel = State.selectedAttractions;
  if (typeof maplibregl === 'undefined') return;

  if (State.mapInstance) {
    try { State.mapInstance.remove(); } catch (e) {}
    State.mapInstance = null;
  }
  State.mapMarkers = new Map();

  // Find center coordinate from first attraction with valid coords, fallback to Bangalore
  let defaultCenter = [77.5946, 12.9716];
  for (const a of sel) {
    const lat = Number(a.lat || a.latitude);
    const lon = Number(a.lon || a.longitude);
    if (isFinite(lat) && isFinite(lon) && (lat !== 0 || lon !== 0)) {
      defaultCenter = [lon, lat];
      break;
    }
  }

  const map = new maplibregl.Map({
    container: 'tripMap',
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
        id: "osm",
        type: "raster",
        source: "osm"
      }]
    },
    center: defaultCenter,
    zoom: sel.length ? 11 : 9
  });
  State.mapInstance = map;

  map.addControl(new maplibregl.NavigationControl(), 'top-right');

  // Handle map resizing when Map tab is shown on desktop or mobile
  const mapTabTrigger = document.querySelector('a[data-bs-toggle="tab"][href="#tab-map"]');
  if (mapTabTrigger && !mapTabTrigger._resizeBound) {
    mapTabTrigger._resizeBound = true;
    mapTabTrigger.addEventListener('shown.bs.tab', () => {
      setTimeout(() => {
        if (State.mapInstance) {
          State.mapInstance.resize();
        }
      }, 100);
    });
  }

  map.on('load', () => {
    const bounds = new maplibregl.LngLatBounds();
    const coordCounts = {};
    let validCount = 0;

    sel.forEach((a) => {
      const origLat = Number(a.lat || a.latitude);
      const origLon = Number(a.lon || a.longitude);

      // Handle missing coordinates safely
      if (!isFinite(origLat) || !isFinite(origLon) || (origLat === 0 && origLon === 0)) {
        return;
      }

      // Handle duplicate coordinates by applying a slight offset spiral
      const coordKey = `${origLat.toFixed(4)},${origLon.toFixed(4)}`;
      const seenCount = coordCounts[coordKey] || 0;
      coordCounts[coordKey] = seenCount + 1;

      let plotLat = origLat;
      let plotLon = origLon;
      if (seenCount > 0) {
        const angle = seenCount * 1.25;
        const radius = 0.00035 * seenCount;
        plotLat += Math.sin(angle) * radius;
        plotLon += Math.cos(angle) * radius;
      }

      validCount++;

      // Create interactive DOM element for marker
      const el = document.createElement('div');
      el.className = 'custom-map-marker';
      el.style.cssText = `width:34px;height:34px;background:#10b981;border-radius:50%;border:2.5px solid #fff;display:flex;align-items:center;justify-content:center;font-size:1.05rem;box-shadow:0 3px 8px rgba(0,0,0,0.3);cursor:pointer;transition:transform 0.2s ease;user-select:none;`;
      el.textContent = a.icon || '📍';
      el.title = `${a.name} (Click to locate in schedule)`;

      // Bidirectional marker click: highlight and scroll to activity card in timeline/schedule
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        window.highlightAndScrollToActivity(a.id, a.name);
      });

      // Escape quotes for safe inline JS
      const safeName = (a.name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
      const safeCat = (a.cat || 'Sightseeing').replace(/"/g, '&quot;');

      const popupHtml = `
        <div style="font-family:inherit;min-width:180px;padding:4px 0;">
          <div style="font-weight:700;font-size:0.95rem;color:#0F172A;line-height:1.2;margin-bottom:3px;">
            ${a.icon || '📍'} ${a.name}
          </div>
          <div style="font-size:0.8rem;color:#64748B;margin-bottom:8px;">${safeCat}</div>
          <button type="button" class="btn btn-sm btn-outline-primary w-100 py-1" style="font-size:0.75rem;font-weight:600;border-radius:6px;"
                  onclick="window.highlightAndScrollToActivity('${a.id || ''}', '${safeName}')">
            🔍 View in Schedule
          </button>
        </div>
      `;

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([plotLon, plotLat])
        .setPopup(new maplibregl.Popup({ offset: 18, closeButton: true }).setHTML(popupHtml))
        .addTo(map);

      // Register marker in State.mapMarkers for bidirectional lookup
      if (a.id) {
        State.mapMarkers.set(String(a.id), marker);
      }
      if (a.name) {
        State.mapMarkers.set(String(a.name).toLowerCase().trim(), marker);
      }

      bounds.extend([plotLon, plotLat]);
    });

    if (validCount > 0 && !bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 60, maxZoom: 14 });
    }
  });
};

