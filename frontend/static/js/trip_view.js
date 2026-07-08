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
  if (ITINERARY_DATA.selected_attractions && ITINERARY_DATA.selected_attractions.length) {
    State.selectedAttractions = ITINERARY_DATA.selected_attractions;
    State.dayPlanner = {};
    const rawPlanner = ITINERARY_DATA.day_planner || {};
    for (let k in rawPlanner) {
      State.dayPlanner[parseInt(k)] = rawPlanner[k];
    }
  } else if (ITINERARY_DATA.days) {
    // Fallback parser for older trips
    const sel = [];
    const dp = {};
    ITINERARY_DATA.days.forEach(day => {
      const d = day.day;
      dp[d] = { morning: [], afternoon: [], evening: [], night: [] };
      ['morning', 'afternoon', 'evening'].forEach(zone => {
        const slot = day[zone];
        if (slot && slot.places) {
          slot.places.forEach(pl => {
            const a = {
              id: pl.id || ('osm_' + Math.floor(Math.random()*1000000)),
              name: pl.name,
              icon: pl.icon || '📍',
              cat: pl.category || '',
              dur: 90, // fallback average 1.5h
              fee: pl.raw_fee || 0,
              lat: pl.lat,
              lon: pl.lon,
              dist: pl.dist || 0
            };
            sel.push(a);
            dp[d][zone].push({
              id: a.id, icon: a.icon, name: a.name, dur: '1.5h', type: 'attraction', category: a.cat, fee: a.fee
            });
          });
        }
      });
    });
    State.selectedAttractions = sel;
    State.dayPlanner = dp;
  }

  // Ensure dayPlanner elements exist for every day
  for (let d = 1; d <= State.days; d++) {
    if (!State.dayPlanner[d]) {
      State.dayPlanner[d] = { morning: [], afternoon: [], evening: [], night: [] };
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

  // Render Day Selector Tabs
  const ds = document.getElementById('daySelector');
  if (ds) {
    ds.innerHTML = Array.from({length: State.days}, (_, i) => {
      const dNum = i + 1;
      const activeClass = dNum === State.currentPlannerDay ? 'active' : '';
      return `<button class="day-btn ${activeClass}" onclick="switchPlannerDay(${dNum}, this)">Day ${dNum}</button>`;
    }).join('');
  }

  const assignedIds = new Set();
  Object.values(State.dayPlanner).forEach(dayObj => {
    ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
      (dayObj[zone] || []).forEach(act => {
        if (act.type === 'attraction' || (act.id && !act.id.startsWith('custom_') && act.id !== 'breakfast' && act.id !== 'lunch' && act.id !== 'dinner' && act.id !== 'rest' && act.id !== 'shopping' && act.id !== 'depart' && act.id !== 'return')) {
          assignedIds.add(String(act.id));
        }
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
    dz.innerHTML = items.length ? items.map((act, idx) => `
      <div class="activity-card" draggable="true" data-id="${act.id}" data-type="${act.type || 'attraction'}" data-zone="${zone}" data-index="${idx}">
        <div class="act-icon">${act.icon || '📍'}</div>
        <div class="act-name">${act.name}</div>
        <div class="act-duration">${act.dur || ''}</div>
        <span class="act-type-badge type-${act.type || 'attraction'}">${act.type || 'attraction'}</span>
        ${isShared ? '' : `<button class="act-remove-btn" onclick="removePlannedActivity(${State.currentPlannerDay}, '${zone}', ${idx}); event.stopPropagation();" style="border:none; background:none; color:var(--text-muted); font-size:1.1rem; cursor:pointer;">×</button>`}
      </div>
    `).join('') : `<div class="text-center text-muted py-4 small">No activities scheduled</div>`;
    dz.querySelectorAll('.activity-card').forEach(initCardDrag);
  });

  // Render the Unscheduled Activities Pool
  const pool = document.getElementById('poolItems');
  if (pool) {
    const unassignedAttractions = sel.filter(a => !assignedIds.has(String(a.id)));
    const poolActs = [
      ...unassignedAttractions.map(a => ({ id: a.id, icon: a.icon, name: a.name, dur: fmtHrs(a.dur), type: 'attraction', category: a.cat, fee: a.fee })),
      { id: 'breakfast', icon: '🥞', name: 'Breakfast', dur: '30m', type: 'food' },
      { id: 'lunch', icon: '🍛', name: 'Lunch', dur: '45m', type: 'food' },
      { id: 'dinner', icon: '🍽️', name: 'Dinner', dur: '60m', type: 'food' },
      { id: 'rest', icon: '😴', name: 'Rest at Hotel', dur: '60m', type: 'leisure' },
      { id: 'shopping', icon: '🛍️', name: 'Local Shopping', dur: '45m', type: 'leisure' },
      { id: 'depart', icon: '🚗', name: 'Travel to Destination', dur: '2h', type: 'travel' },
      { id: 'return', icon: '🔙', name: 'Return Journey', dur: '2h', type: 'travel' },
      ...(State.customPoolActivities || [])
    ];
    pool.innerHTML = poolActs.map(a => `
      <div class="activity-card" draggable="true" data-id="${a.id}" data-type="${a.type}" style="display: inline-flex; width: auto; margin-right: 8px;">
        <div class="act-icon">${a.icon}</div>
        <div class="act-name" style="margin-right: 10px;">${a.name}</div>
        <div class="act-duration" style="margin-right: 10px;">${a.dur}</div>
        <span class="act-type-badge type-${a.type}">${a.type}</span>
      </div>`).join('');
    pool.querySelectorAll('.activity-card').forEach(initCardDrag);
  }
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

window.savePlannerChangesToServer = async function() {
  const payload = { day_planner: State.dayPlanner };

  try {
    const response = await fetch(`/planner/${State.tripId}/update_planner`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (result.success) {
      alert('🎉 Planner layout updated successfully!');
      location.reload();
    } else {
      alert(`❌ Update failed: ${result.error}`);
    }
  } catch (err) {
    console.error(err);
    alert('❌ Error connecting to server');
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
        if (act.id && act.id.startsWith('osm_')) {
          const attraction = State.selectedAttractions.find(a => a.id === act.id);
          if (attraction && !dayAttractions.includes(attraction)) {
            dayAttractions.push(attraction);
          }
        }
      });
    });
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
    { type:'hotel', icon:'🏨', name:'Your Hotel', lat:null, lon:null },
    ...sel.map(a=>({ type:'attraction', icon:a.icon, name:a.name, lat:a.lat, lon:a.lon, dur:a.dur, fee:a.fee, cat:a.cat })),
    { type:'hotel', icon:'🏨', name:'Return to Hotel', lat:null, lon:null }
  ];

  rt.innerHTML = `<div class="d-flex align-items-center gap-2 p-3"><span class="spinner-border spinner-border-sm"></span><span>Loading road distance info…</span></div>`;

  let totalDistM = 0, totalDurS = 0;
  let html = '';

  for (let i = 0; i < stops.length; i++) {
    const s = stops[i];
    html += `<div class="route-stop">
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

  if (State.mapInstance) { State.mapInstance.remove(); State.mapInstance = null; }

  const center = sel.length ? [sel[0].lon, sel[0].lat] : [77.5946, 12.9716];

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
    center,
    zoom: sel.length ? 11 : 9
  });
  State.mapInstance = map;

  map.addControl(new maplibregl.NavigationControl(), 'top-right');

  map.on('load', () => {
    const bounds = new maplibregl.LngLatBounds();
    sel.forEach((a) => {
      if (!a.lat || !a.lon) return;
      const el = document.createElement('div');
      el.style.cssText = `width:30px;height:30px;background:#10b981;border-radius:50%;border:2px solid #fff;display:flex;align-items:center;justify-content:center;font-size:0.9rem;box-shadow:0 2px 5px rgba(0,0,0,0.3);`;
      el.textContent = a.icon;

      new maplibregl.Marker({ element: el })
        .setLngLat([a.lon, a.lat])
        .setPopup(new maplibregl.Popup({ offset: 15 }).setHTML(`<strong>${a.icon} ${a.name}</strong><br><small>${a.cat}</small>`))
        .addTo(map);

      bounds.extend([a.lon, a.lat]);
    });

    if (sel.length && !bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 50, maxZoom: 13 });
    }
  });
};
