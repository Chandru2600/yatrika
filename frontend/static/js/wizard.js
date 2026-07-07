/* =====================================================================
   Smart Travel Wizard — wizard.js  (Real-time API version)
   APIs: Nominatim (geocoding) · Overpass (OSM attractions) ·
         OSRM (road routing) · OpenWeatherMap (via Flask proxy)
   ===================================================================== */

/* ── State ────────────────────────────────────────────────────────── */
const State = {
  step: 1,
  source: '', sourceLat: null, sourceLon: null,
  dest: '',   destLat:   null, destLon:   null,
  days: 3, travelers: 2, budget: 30000,
  transport: 'car', style: 'Adventure',
  selectedAttractions: [],
  liveAttractions: [],        // fetched from Overpass
  routeData: null,            // from OSRM
  weatherData: null,          // from OWM
  favAttractions: new Set(),
  charts: {},
  mapInstance: null,          // MapLibre instance
  mapSatellite: false,
  attrSearchQuery: '',        // Step 2 search
  customPoolActivities: [],   // Custom created activities
};

/* ── LocalStorage persistence ─────────────────────────────────────── */
const LS_KEY = 'wizard_state_v2';
function saveStateToLS() {
  try {
    const snap = {
      source: State.source, sourceLat: State.sourceLat, sourceLon: State.sourceLon,
      dest: State.dest, destLat: State.destLat, destLon: State.destLon,
      days: State.days, travelers: State.travelers, budget: State.budget,
      transport: State.transport, style: State.style,
      selectedIds: State.selectedAttractions.map(a => a.id),
      step: State.step,
      dayPlanner: State.dayPlanner || {},
      currentPlannerDay: State.currentPlannerDay || 1,
      customPoolActivities: State.customPoolActivities || [],
    };
    localStorage.setItem(LS_KEY, JSON.stringify(snap));
  } catch(e) {}
}
function loadStateFromLS() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return false;
    const snap = JSON.parse(raw);
    Object.assign(State, {
      source: snap.source||'', sourceLat: snap.sourceLat, sourceLon: snap.sourceLon,
      dest: snap.dest||'', destLat: snap.destLat, destLon: snap.destLon,
      days: snap.days||3, travelers: snap.travelers||2, budget: snap.budget||30000,
      transport: snap.transport||'car', style: snap.style||'Adventure',
      dayPlanner: snap.dayPlanner || {},
      currentPlannerDay: snap.currentPlannerDay || 1,
      customPoolActivities: snap.customPoolActivities || [],
    });
    if (State.dayPlanner) {
      syncAttractionsOrderFromPlanner();
    }
    return snap;
  } catch(e) { return false; }
}

/* ── Utility ──────────────────────────────────────────────────────── */
const fmtINR = n => '₹' + Math.round(n).toLocaleString('en-IN');
const fmtHrs = m => { const h=Math.floor(m/60),r=m%60; return h?(r?`${h}h ${r}m`:`${h}h`):`${r}m`; };
const fmtKm  = m => m >= 1000 ? (m/1000).toFixed(1)+' km' : Math.round(m)+' m';
const sleep  = ms => new Promise(r => setTimeout(r, ms));

const CAT_ICONS = {
  tourism: { attraction:'🏛️', museum:'🏛️', viewpoint:'🌄', theme_park:'🎡', zoo:'🦁',
    artwork:'🎨', gallery:'🖼️', aquarium:'🐠', waterfall:'💧', default:'📍' },
  amenity: { restaurant:'🍽️', cafe:'☕', fast_food:'🍔', bar:'🍺', pub:'🍻',
    place_of_worship:'🕌', hospital:'🏥', parking:'🅿️', default:'🏢' },
  leisure: { park:'🌳', garden:'🌸', nature_reserve:'🌿', sports_centre:'🏋️',
    stadium:'🏟️', beach_resort:'🏖️', default:'🌿' },
  natural: { peak:'🏔️', waterfall:'💧', hot_spring:'♨️', beach:'🏖️',
    cave_entrance:'🕳️', glacier:'🧊', default:'🌲' },
  historic: { castle:'🏰', fort:'🏯', monument:'🗿', ruins:'🏚️', temple:'⛩️',
    church:'⛪', default:'🏛️' },
};
function catIcon(tags) {
  for (const [k, v] of Object.entries(CAT_ICONS)) {
    if (tags[k] && v[tags[k]]) return v[tags[k]];
    if (tags[k] && v.default)   return v.default;
  }
  return '📍';
}
function catName(tags) {
  const order = ['tourism','historic','leisure','natural','amenity'];
  for (const k of order) if (tags[k]) return (tags[k].replace(/_/g,' ')||k).replace(/\b\w/g,c=>c.toUpperCase());
  return 'Point of Interest';
}
function osmPhoto(name, cat) {
  // source.unsplash.com/400x250/?q= is deprecated — use picsum for a reliable
  // deterministic placeholder image keyed on the attraction name hash.
  const seed = Math.abs(name.split('').reduce((h,c)=>((h<<5)-h+c.charCodeAt(0))|0, 0)) % 1000;
  return `https://picsum.photos/seed/${seed}/400/250`;
}

/* ── Nominatim — via Flask proxy (adds required User-Agent) ──────── */
async function geocode(query) {
  try {
    const res = await fetch(`/planner/api/geocode?q=${encodeURIComponent(query)}&limit=8`);
    return res.ok ? res.json() : [];
  } catch { return []; }
}

/* ── Overpass — fetch tourist attractions near a coord ───────────── */
// Build the Overpass QL for a fixed 40 km radius — returns raw elements
function _buildOverpassQL(lat, lon, r) {
  return `[out:json][timeout:45];
(
  node["tourism"~"attraction|museum|viewpoint|artwork|zoo|theme_park|waterfall|gallery|aquarium"](around:${r},${lat},${lon});
  node["historic"~"castle|fort|monument|ruins|temple|church|memorial|mosque|shrine|palace"](around:${r},${lat},${lon});
  node["natural"~"peak|waterfall|hot_spring|beach|cave_entrance|glacier|volcano"](around:${r},${lat},${lon});
  node["leisure"~"park|garden|nature_reserve|beach_resort|sports_centre"](around:${r},${lat},${lon});
  node["amenity"~"place_of_worship|theatre|cinema|library"](around:${r},${lat},${lon});
  way["tourism"~"attraction|museum|viewpoint|zoo|theme_park|gallery"](around:${r},${lat},${lon});
  way["historic"~"castle|fort|monument|ruins|temple|palace"](around:${r},${lat},${lon});
  way["leisure"~"park|garden|nature_reserve"](around:${r},${lat},${lon});
  relation["tourism"~"attraction|museum"](around:${r},${lat},${lon});
);
out center tags 120;`;
}

// Prominence score — higher = more famous / well-known
// Signals: wikidata link, wikipedia link, tourism tag weight, name length (shorter = more famous)
function _prominenceScore(tags) {
  let score = 0;
  if (tags.wikidata)                          score += 40;
  if (tags.wikipedia)                         score += 35;
  if (tags.wikimedia_commons)                 score += 10;
  if (tags.tourism === 'attraction')          score += 30;
  if (tags.tourism === 'museum')              score += 28;
  if (tags.tourism === 'theme_park')          score += 25;
  if (tags.tourism === 'zoo')                 score += 22;
  if (tags.tourism === 'viewpoint')           score += 18;
  if (tags.tourism === 'gallery')             score += 15;
  if (tags.historic === 'castle' ||
      tags.historic === 'fort' ||
      tags.historic === 'palace')             score += 30;
  if (tags.historic === 'monument' ||
      tags.historic === 'ruins')              score += 20;
  if (tags.historic === 'temple' ||
      tags.historic === 'shrine')             score += 18;
  if (tags.natural === 'peak')                score += 25;
  if (tags.natural === 'waterfall')           score += 22;
  if (tags.natural === 'beach')               score += 20;
  if (tags.leisure === 'nature_reserve')      score += 18;
  if (tags.leisure === 'park')                score += 10;
  // Shorter name = more famous (single well-known names)
  const nameLen = (tags.name || '').length;
  if (nameLen > 0 && nameLen <= 10)           score += 8;
  else if (nameLen <= 20)                     score += 4;
  if (tags.description || tags['description:en']) score += 5;
  if (tags.website)                           score += 3;
  if (tags.opening_hours)                     score += 2;
  return score;
}

function isMuslimPlaceOfWorship(tags) {
  if (!tags) return false;
  const religion = (tags.religion || '').toLowerCase();
  const denomination = (tags.denomination || '').toLowerCase();
  if (religion === 'muslim' || religion === 'islam' || denomination === 'sunni' || denomination === 'shia') {
    return true;
  }
  const name = (tags.name || '').toLowerCase();
  const forbiddenKeywords = ['mosque', 'masjid', 'dargah', 'darga', 'eidgah', 'idgah', 'imambara', 'madrasa', 'jama masjid', 'mazar', 'ziyarat'];
  if (forbiddenKeywords.some(keyword => name.includes(keyword))) {
    return true;
  }
  const amenity = (tags.amenity || '').toLowerCase();
  if (amenity === 'place_of_worship') {
    if (name.includes('hazrat') || name.includes('peer') || name.includes('wali') || (name.includes('shrine') && (name.includes('peer') || name.includes('shah') || name.includes('dargah')))) {
      return true;
    }
  }
  return false;
}

async function fetchAttractions(lat, lon) {
  const RADIUS = 40000; // fixed 40 km — user requested
  let elements = [];
  try {
    const res = await fetch('/planner/api/overpass', {
      method: 'POST',
      body: 'data=' + encodeURIComponent(_buildOverpassQL(lat, lon, RADIUS)),
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    if (!res.ok) return [];
    const data = await res.json();
    elements = (data.elements || []).filter(e => e.tags && e.tags.name && !isMuslimPlaceOfWorship(e.tags));
  } catch { return []; }

  return elements
    .map(e => {
      const lt = e.lat  || e.center?.lat;
      const ln = e.lon  || e.center?.lon;
      if (!lt || !ln) return null;
      const dist = haversineKm(lat, lon, lt, ln);
      // Apply road-distance factor: actual road distance is ~1.35x the straight-line
      const roadDist = Math.round(dist * 1.35 * 10) / 10;
      if (dist > 40) return null;
      const nm   = e.tags.name;
      const icon = catIcon(e.tags);
      const cat  = catName(e.tags);
      const prominence = _prominenceScore(e.tags);
      return {
        id:   'osm_' + e.id,
        name: nm,
        cat, icon,
        lat: lt, lon: ln,
        dist: roadDist,
        prominence,
        dur:  guessVisitDuration(e.tags),
        fee:  0,
        rating: (3.8 + Math.random() * 1.2).toFixed(1),
        difficulty: roadDist > 20 ? 'Moderate' : 'Easy',
        family: true,
        popular: prominence >= 35,
        hidden:  prominence < 15 && Math.random() > 0.6,
        tags: deriveTags(e.tags),
        img:  osmPhoto(nm, cat),
        desc: e.tags.description || e.tags['description:en'] || `${nm} is a ${cat.toLowerCase()} located near ${State.dest}.`,
        tips: ['Check local timings before visiting', 'Carry water and snacks', 'Best visited in the morning'],
        nearbyFood: ['Local restaurant nearby', 'Street food available'],
        review: [{ author: 'Traveller', stars: Math.round(3.5 + Math.random()*1.5), text: 'Wonderful place, highly recommended!' }],
        website: e.tags.website || null,
        opening: e.tags.opening_hours || 'Check locally',
        phone:   e.tags.phone || null,
      };
    })
    .filter(Boolean)
    // Sort: most famous first, then by distance as tiebreaker
    .sort((a, b) => b.prominence - a.prominence || a.dist - b.dist);
}

function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371, dLat = (lat2-lat1)*Math.PI/180, dLon = (lon2-lon1)*Math.PI/180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function guessVisitDuration(tags) {
  if (tags.tourism === 'museum')           return 120;
  if (tags.tourism === 'theme_park')       return 240;
  if (tags.tourism === 'zoo')              return 180;
  if (tags.tourism === 'viewpoint')        return 45;
  if (tags.natural === 'waterfall')        return 90;
  if (tags.natural === 'peak')             return 300;
  if (tags.historic === 'castle')          return 90;
  if (tags.historic === 'fort')            return 90;
  if (tags.leisure === 'park')             return 60;
  if (tags.leisure === 'nature_reserve')   return 120;
  return 60;
}

function deriveTags(tags) {
  const result = [];
  if (tags.tourism === 'viewpoint' || tags.natural === 'peak') result.push('Sunset', 'Nature');
  if (tags.tourism === 'museum' || tags.historic)              result.push('Afternoon', 'Family');
  if (tags.natural === 'waterfall' || tags.natural === 'beach')result.push('Morning', 'Nature');
  if (tags.leisure === 'park' || tags.leisure === 'garden')    result.push('Morning', 'Family');
  if (tags.amenity === 'place_of_worship')                     result.push('Morning', 'Spiritual');
  if (result.length === 0) result.push('Morning');
  return [...new Set(result)];
}

/* ── OSRM — real road distance via Flask proxy ────────────────────── */
async function fetchRoute(fromLat, fromLon, toLat, toLon) {
  const profile = State.transport === 'bike' ? 'bike' : 'car';
  // OSRM expects lon,lat order
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

/* ── Weather — via Flask proxy (uses OPENWEATHER_API_KEY from .env) ─ */
async function fetchWeather(city) {
  try {
    const res = await fetch(`/planner/api/weather/${encodeURIComponent(city)}`);
    return res.ok ? res.json() : null;
  } catch { return null; }
}

/* ── Autocomplete widget ──────────────────────────────────────────── */
let acTimers = {};
function initAutocomplete(inputId, resultId, onSelect) {
  const inp  = document.getElementById(inputId);
  const list = document.getElementById(resultId);
  if (!inp || !list) return;

  inp.addEventListener('input', () => {
    clearTimeout(acTimers[inputId]);
    const q = inp.value.trim();
    if (q.length < 3) { list.classList.add('d-none'); return; }
    acTimers[inputId] = setTimeout(async () => {
      list.innerHTML = `<div class="ac-item ac-loading"><span class="spinner-border spinner-border-sm me-2"></span>Searching…</div>`;
      list.classList.remove('d-none');
      const results = await geocode(q);
      if (!results.length) {
        list.innerHTML = `<div class="ac-item text-muted">No results found</div>`;
        return;
      }
      list.innerHTML = results.map(r => `
        <div class="ac-item" data-lat="${r.lat}" data-lon="${r.lon}" data-name="${r.display_name}">
          <span class="ac-pin">📍</span>
          <div>
            <div class="ac-name">${r.display_name.split(',').slice(0,3).join(', ')}</div>
            <div class="ac-sub">${r.display_name.split(',').slice(3).join(', ').trim()}</div>
          </div>
        </div>
      `).join('');
      list.querySelectorAll('.ac-item:not(.ac-loading)').forEach(item => {
        item.addEventListener('click', () => {
          const name = item.querySelector('.ac-name').textContent;
          inp.value  = name;
          list.classList.add('d-none');
          onSelect(name, parseFloat(item.dataset.lat), parseFloat(item.dataset.lon));
        });
      });
    }, 350);
  });

  document.addEventListener('click', e => {
    if (!inp.contains(e.target) && !list.contains(e.target)) list.classList.add('d-none');
  });
}

/* ── DOM Ready ───────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initDateDefaults();
  initTransportStyle();

  // Restore saved state
  const saved = loadStateFromLS();
  if (saved && saved.dest) {
    const srcEl = document.getElementById('w_source');
    const dstEl = document.getElementById('w_dest');
    if (srcEl) srcEl.value = State.source;
    if (dstEl) dstEl.value = State.dest;
    if (saved.travelers) {
      const tel = document.getElementById('w_travelers');
      if (tel) tel.value = State.travelers;
    }
    if (saved.budget) {
      const bel = document.getElementById('w_budget_range');
      if (bel) { bel.value = State.budget; document.getElementById('w_budget_val').textContent='₹'+State.budget.toLocaleString('en-IN'); }
    }
    updatePreviewCard();
    showToast(`✅ Restored your last session: ${State.dest.split(',')[0]}`, 'success');
  }

  // Source autocomplete
  initAutocomplete('w_source', 'ac_source_list', (name, lat, lon) => {
    State.source    = name;
    State.sourceLat = lat;
    State.sourceLon = lon;
    updatePreviewCard();
    tryFetchRouteDistance();
    saveStateToLS();
  });

  // Destination autocomplete
  initAutocomplete('w_dest', 'ac_dest_list', async (name, lat, lon) => {
    State.dest    = name;
    State.destLat = lat;
    State.destLon = lon;
    updatePreviewCard();
    tryFetchRouteDistance();
    saveStateToLS();
    // fetch weather live
    showWeatherLoading();
    const w = await fetchWeather(name.split(',')[0]);
    showWeatherResult(w);
  });

  // Travelers / budget live update
  ['w_travelers','w_budget_range'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', () => {
      if (id === 'w_travelers') State.travelers = parseInt(el.value);
      if (id === 'w_budget_range') State.budget = parseInt(el.value);
      updatePreviewCard();
      saveStateToLS();
    });
  });

  initScrollReveal();
});

/* ── Date helpers ────────────────────────────────────────────────── */
function initDateDefaults() {
  const today = new Date();
  const d1 = new Date(today); d1.setDate(d1.getDate()+7);
  const d2 = new Date(d1);    d2.setDate(d2.getDate()+2);
  const fmt = d => d.toISOString().slice(0,10);
  const td  = document.getElementById('w_travel_date');
  const rd  = document.getElementById('w_return_date');
  if (td) { td.value = fmt(d1); td.min = fmt(today); td.addEventListener('change', calcDays); }
  if (rd) { rd.value = fmt(d2); rd.min = fmt(today); rd.addEventListener('change', calcDays); }
  calcDays();
}
function calcDays() {
  const t = document.getElementById('w_travel_date')?.value;
  const r = document.getElementById('w_return_date')?.value;
  if (!t || !r) return;
  State.days = Math.max(1, Math.round((new Date(r)-new Date(t))/(864e5)));
  const el = document.getElementById('w_days');
  if (el) el.value = State.days;
  updatePreviewCard();
}
function adjustCounter(id, delta) {
  const el = document.getElementById(id);
  if (!el) return;
  el.value = Math.max(+el.min||1, Math.min(+el.max||99, (+el.value||1)+delta));
  el.dispatchEvent(new Event('input'));
}

/* ── Transport & Style tiles ─────────────────────────────────────── */
function initTransportStyle() {
  document.querySelectorAll('.transport-tile').forEach(tile => {
    tile.addEventListener('click', () => {
      document.querySelectorAll('.transport-tile').forEach(t=>t.classList.remove('selected'));
      tile.classList.add('selected');
      State.transport = tile.querySelector('input').value;
      updatePreviewCard();
      tryFetchRouteDistance();
    });
  });
  document.querySelectorAll('.style-tile').forEach(tile => {
    tile.addEventListener('click', () => {
      document.querySelectorAll('.style-tile').forEach(t=>t.classList.remove('selected'));
      tile.classList.add('selected');
      State.style = tile.querySelector('input').value;
      updatePreviewCard();
    });
  });
}

/* ── Preview card ────────────────────────────────────────────────── */
function updatePreviewCard() {
  setText('pc_dest',      State.dest      || '—');
  setText('pc_from',      'From: ' + (State.source || '—'));
  setText('pc_days',      State.days + ' Day' + (State.days>1?'s':''));
  setText('pc_travelers', State.travelers + ' Traveler' + (State.travelers>1?'s':''));
  setText('pc_budget',    fmtINR(State.budget));
  setText('pc_transport', State.transport.charAt(0).toUpperCase() + State.transport.slice(1));
  setText('pc_style',     State.style);
  if (State.dest) setText('dest-name-title', State.dest.split(',')[0]);
}
function setText(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

/* ── Route distance preview (in Step 1 preview card) ────────────── */
let routeTimer = null;
async function tryFetchRouteDistance() {
  if (!State.sourceLat || !State.destLat) return;
  clearTimeout(routeTimer);
  routeTimer = setTimeout(async () => {
    const el = document.getElementById('pc_route_dist');
    if (el) el.textContent = 'Calculating…';
    const r = await fetchRoute(State.sourceLat, State.sourceLon, State.destLat, State.destLon);
    State.routeData = r;
    if (el && r) el.textContent = fmtKm(r.distM) + ' · ~' + fmtHrs(Math.round(r.durS/60));
    else if (el) el.textContent = 'Route unavailable';
  }, 500);
}

/* ── Weather widgets ─────────────────────────────────────────────── */
function showWeatherLoading() {
  const el = document.getElementById('weatherPreviewCard');
  if (el) { el.classList.remove('d-none'); el.innerHTML = `<div class="d-flex align-items-center gap-2 p-2"><span class="spinner-border spinner-border-sm"></span><span class="small text-muted">Fetching live weather…</span></div>`; }
}
function showWeatherResult(w) {
  const el = document.getElementById('weatherPreviewCard');
  if (!el) return;
  if (!w || w.error || !w.current) {
    el.innerHTML = `<div class="p-2 small text-muted">⚠️ Weather data unavailable — add WEATHER_API_KEY to .env</div>`;
    return;
  }
  const c = w.current;
  el.innerHTML = `
    <div class="live-weather-chip">
      <div class="lw-temp">${c.temperature}°C</div>
      <div class="lw-info">
        <div class="fw-semibold">${c.city || State.dest.split(',')[0]}</div>
        <div class="small text-muted">${c.description} · 💧${c.humidity}% · 💨${c.wind_speed} m/s</div>
      </div>
      <span class="lw-badge">Live</span>
    </div>`;
  State.weatherData = w;
}

/* ── Step Navigation ─────────────────────────────────────────────── */
const STEP_LABELS = ['','Journey Details','Destination Explorer','Attraction Selection','Attraction Details','Day Planner','Smart Timeline','Route Planner','Interactive Map','Travel Summary','Trip Overview'];

async function goToStep(n) {
  if (n === 2 && !State.destLat) {
    showToast('⚠️ Please select a destination from the autocomplete suggestions first.', 'warning');
    return;
  }
  const cur = document.getElementById('wstep-' + State.step);
  const nxt = document.getElementById('wstep-' + n);
  if (!nxt) return;
  if (cur) cur.classList.add('d-none');
  nxt.classList.remove('d-none');
  State.step = n;
  updateProgressBar(n);
  updateBreadcrumb(n);
  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (n === 2) await loadStep2();
  if (n === 3) renderSelectedList();
  if (n === 4) renderDetailGrid();   // Attraction Details
  if (n === 5) renderDayPlanner();   // Day Planner
  if (n === 6) renderTimeline();     // Smart Timeline
  if (n === 7) await renderRoute();  // Route Planner
  if (n === 8) renderMap();          // Interactive Map
  if (n === 9) renderAnalytics();
  if (n === 10) renderOverview();
}

function updateProgressBar(n) {
  const fill = document.getElementById('progressFill');
  if (fill) fill.style.width = ((n/10)*100)+'%';
  document.querySelectorAll('.progress-step').forEach(s => {
    const sn = +s.dataset.step;
    s.classList.remove('active','done');
    if (sn===n) s.classList.add('active'); else if (sn<n) s.classList.add('done');
  });
  document.querySelectorAll('.ps-connector').forEach((c,i) => c.classList.toggle('done', i<n-1));
}
function updateBreadcrumb(n) {
  const bc = document.getElementById('wizardBreadcrumb');
  if (!bc) return;
  bc.innerHTML = STEP_LABELS.slice(1,n+1).map((l,i,a) =>
    `<span class="${i===a.length-1?'bc-item active':'bc-item'}">${l}</span>${i<a.length-1?'<span class="bc-sep"></span>':''}`
  ).join('');
}

/* ── STEP 2 — Load real attractions from Overpass ────────────────── */
async function loadStep2() {
  const grid  = document.getElementById('attractionGrid');
  const title = document.getElementById('dest-name-title');
  if (title) title.textContent = State.dest.split(',')[0];
  if (!grid) return;

  // Show skeleton
  State.selectedAttractions = [];
  State.liveAttractions     = [];
  grid.innerHTML = Array(8).fill(0).map(()=>`<div class="skeleton sk-card"></div>`).join('');
  updateSidebar();

  const attrs = await fetchAttractions(State.destLat, State.destLon);
  if (!attrs.length) {
    grid.innerHTML = `<div class="text-center py-5 text-muted" style="grid-column:1/-1">
      <div style="font-size:2.5rem">😕</div>
      <p>No tourist attractions found near <strong>${State.dest}</strong>.<br>
      Try a more specific city name, e.g. "Lonavala, Maharashtra" or "Paris, France".</p>
    </div>`;
    return;
  }
  State.liveAttractions = attrs;
  renderAttractionGrid(attrs);
}

function renderAttractionGrid(attractions) {
  const grid = document.getElementById('attractionGrid');
  if (!grid) return;
  if (!attractions.length) {
    grid.innerHTML = `<div class="text-center py-4 text-muted" style="grid-column:1/-1">No attractions match this filter.</div>`;
    return;
  }
  grid.innerHTML = attractions.map(a => buildAttractionCard(a)).join('');
  grid.querySelectorAll('.attraction-card').forEach(card => {
    card.addEventListener('click', e => { if (!e.target.closest('.ac-fav-btn')) toggleSelection(card.dataset.id); });
  });
  grid.querySelectorAll('.ac-fav-btn').forEach(btn => {
    btn.addEventListener('click', e => { e.stopPropagation(); toggleFav(btn.closest('.attraction-card').dataset.id, btn); });
  });
}

function buildAttractionCard(a) {
  const sel   = !!State.selectedAttractions.find(x=>x.id===a.id);
  const faved = State.favAttractions.has(a.id);
  const badges = [
    a.popular ? `<span class="ac-badge badge-popular">⭐ Popular</span>` : '',
    a.family  ? `<span class="ac-badge badge-family">👨‍👩‍👧 Family</span>` : '',
    a.hidden  ? `<span class="ac-badge badge-hidden">💎 Hidden Gem</span>` : '',
  ].filter(Boolean).slice(0,2).join('');
  return `
  <div class="attraction-card ${sel?'selected':''}" data-id="${a.id}">
    <div class="ac-image" style="background-image:url('${a.img}');background-color:#e5e7eb">
      <div class="ac-image-overlay"></div>
      <div class="ac-badges">${badges}</div>
      <button class="ac-fav-btn ${faved?'faved':''}"><i class="bi bi-heart${faved?'-fill':''}"></i></button>
      <div class="ac-rating-overlay"><div class="ac-rating">★ ${a.rating}</div></div>
      <div class="ac-select-indicator" style="display:${sel?'flex':'none'}">✓</div>
    </div>
    <div class="ac-body">
      <div class="ac-category">${a.icon} ${a.cat}</div>
      <div class="ac-name">${a.name}</div>
      <div class="ac-meta">
        <div class="ac-meta-item"><i class="bi bi-clock me-1"></i>${fmtHrs(a.dur)}</div>
        <div class="ac-meta-item"><i class="bi bi-geo-alt me-1"></i>${a.dist} km away</div>
        <div class="ac-meta-item"><i class="bi bi-people me-1"></i>${a.difficulty}</div>
        ${a.opening !== 'Check locally' ? `<div class="ac-meta-item"><i class="bi bi-door-open me-1"></i>${a.opening}</div>` : ''}
      </div>
    </div>
  </div>`;
}

function toggleSelection(id) {
  const a = State.liveAttractions.find(x=>x.id===id);
  if (!a) return;
  const idx = State.selectedAttractions.findIndex(x=>x.id===id);
  if (idx > -1) State.selectedAttractions.splice(idx,1); else State.selectedAttractions.push(a);
  updateSidebar();
  const card = document.querySelector(`.attraction-card[data-id="${id}"]`);
  if (card) {
    const added = idx === -1;
    card.classList.toggle('selected', added);
    const ind = card.querySelector('.ac-select-indicator');
    if (ind) ind.style.display = added ? 'flex' : 'none';
    const favBtn = card.querySelector('.ac-fav-btn');
    if (favBtn) favBtn.style.display = added ? 'none' : '';
  }
}
function toggleFav(id, btn) {
  if (State.favAttractions.has(id)) { State.favAttractions.delete(id); btn.classList.remove('faved'); btn.innerHTML='<i class="bi bi-heart"></i>'; }
  else { State.favAttractions.add(id); btn.classList.add('faved'); btn.innerHTML='<i class="bi bi-heart-fill"></i>'; }
}
function filterAttractions(tag, btnEl) {
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  if (btnEl && typeof btnEl !== 'string') btnEl.classList.add('active');
  const f = tag.toLowerCase();
  State._activeFilter = f;
  applyAttractionFilters();
}
function searchAttractions(query) {
  State.attrSearchQuery = query.toLowerCase();
  applyAttractionFilters();
}
function applyAttractionFilters() {
  const f = State._activeFilter || 'all';
  const q = State.attrSearchQuery || '';
  let filtered = State.liveAttractions;
  if (f !== 'all') filtered = filtered.filter(a => a.tags.some(t=>t.toLowerCase().includes(f)) || a.cat.toLowerCase().includes(f));
  if (q) filtered = filtered.filter(a => a.name.toLowerCase().includes(q) || a.cat.toLowerCase().includes(q));
  renderAttractionGrid(filtered);
}
function removeFromSelection(id) {
  const idx = State.selectedAttractions.findIndex(x=>x.id===id);
  if (idx>-1) State.selectedAttractions.splice(idx,1);
  updateSidebar();
  const card = document.querySelector(`.attraction-card[data-id="${id}"]`);
  if (card) { card.classList.remove('selected'); const ind=card.querySelector('.ac-select-indicator'); if(ind)ind.style.display='none'; const fb=card.querySelector('.ac-fav-btn'); if(fb)fb.style.display=''; }
}
function updateSidebar() {
  const sel = State.selectedAttractions;
  setText('selectedCount', sel.length);
  const totalMins = sel.reduce((s,a)=>s+a.dur,0);
  const totalDist = sel.reduce((s,a)=>s+a.dist,0);
  const budgetEst = sel.reduce((s,a)=>s+a.fee,0) + totalDist*4 + totalMins*20;
  const avail     = (State.days*8*60) - totalMins;
  setText('totalDuration', fmtHrs(totalMins));
  setText('totalDistance', totalDist+' km');
  setText('estBudget', fmtINR(budgetEst));
  setText('timeLeft', avail>0?fmtHrs(avail):'Full!');
  const list = document.getElementById('selectedAttractions');
  if (list) list.innerHTML = sel.length
    ? sel.map(a=>`<div class="isb-item"><span class="isb-item-icon">${a.icon}</span><span class="isb-item-name">${a.name}</span><span class="isb-item-remove" onclick="removeFromSelection('${a.id}')">✕</span></div>`).join('')
    : `<p class="text-muted small text-center p-3">Tap attraction cards to add them</p>`;
}

/* ── STEP 3 — Selected list ──────────────────────────────────────── */
function renderSelectedList() {
  const sel  = State.selectedAttractions;
  const list = document.getElementById('selectedList');
  if (!list) return;
  if (!sel.length) { list.innerHTML=`<div class="text-center py-4 text-muted"><div style="font-size:2.5rem">🗺️</div><p>No attractions selected.<br><a href="#" onclick="goToStep(2)">Go back to Step 2</a></p></div>`; return; }
  list.innerHTML = sel.map((a,i)=>`
    <div class="sl-item" draggable="true" data-id="${a.id}">
      <span class="sl-drag-handle"><i class="bi bi-grip-vertical"></i></span>
      <span class="sl-num">${i+1}</span>
      <div class="sl-info"><div class="sl-name">${a.icon} ${a.name}</div><div class="sl-meta">${a.cat} · ${a.dist} km · ${a.difficulty}</div></div>
      <span class="sl-duration">${fmtHrs(a.dur)}</span>
      <span class="sl-remove" onclick="removeFromSelection('${a.id}');renderSelectedList()"><i class="bi bi-trash3"></i></span>
    </div>`).join('');
  const totalMins=sel.reduce((s,a)=>s+a.dur,0), totalDist=sel.reduce((s,a)=>s+a.dist,0), totalFees=sel.reduce((s,a)=>s+a.fee,0);
  setText('ss_places',   sel.length);
  setText('ss_duration', fmtHrs(totalMins));
  setText('ss_distance', totalDist+' km');
  setText('ss_fees',     fmtINR(totalFees));
  setText('ss_days',     Math.max(1,Math.ceil(totalMins/480)));
  initDragSort(list);
}
function initDragSort(container) {
  let drag = null;
  container.querySelectorAll('.sl-item').forEach(item => {
    item.addEventListener('dragstart', ()=>{ drag=item; setTimeout(()=>item.classList.add('dragging'),0); });
    item.addEventListener('dragend',   ()=>{ drag=null; item.classList.remove('dragging'); });
    item.addEventListener('dragover',  e=>{ e.preventDefault(); const mid=item.getBoundingClientRect().y+item.getBoundingClientRect().height/2; container.insertBefore(drag, e.clientY<mid?item:item.nextSibling); });
  });
}

/* ── STEP 4 — Real OSRM route ────────────────────────────────────── */
async function renderRoute() {
  const sel = State.selectedAttractions;
  const rt  = document.getElementById('routeTimeline');
  const js  = document.getElementById('journeyStats');
  const cb  = document.getElementById('costBreakdown');
  if (!rt) return;

  const tIcons = { bike:'🏍️', car:'🚗', bus:'🚌', train:'🚂', flight:'✈️' };
  const tIcon  = tIcons[State.transport] || '🚗';

  // Build stops list
  const stops = [
    { type:'hotel', icon:'🏨', name: State.source || 'Your Starting Point', lat:State.sourceLat, lon:State.sourceLon },
    ...sel.map(a=>({ type:'attraction', icon:a.icon, name:a.name, lat:a.lat, lon:a.lon, dur:a.dur, fee:a.fee, cat:a.cat })),
    { type:'hotel', icon:'🏨', name:'Return to Hotel / Home', lat:State.sourceLat, lon:State.sourceLon }
  ];

  rt.innerHTML = `<div class="d-flex align-items-center gap-2 p-3"><span class="spinner-border spinner-border-sm"></span><span>Calculating real road distances via OSRM…</span></div>`;

  let totalDistM = 0, totalDurS = 0;
  let html = '';
  for (let i = 0; i < stops.length; i++) {
    const s = stops[i];
    html += `<div class="route-stop">
      <div class="rs-pin ${s.type}">${s.icon}</div>
      <div class="rs-info">
        <div class="rs-name">${s.name}</div>
        ${s.cat ? `<div class="rs-details"><span class="rs-detail-item">${s.cat}</span>${s.dur?`<span class="rs-detail-item">⏱ ${fmtHrs(s.dur)}</span>`:''}${s.fee?`<span class="rs-detail-item">🎟 ₹${s.fee}</span>`:''}</div>` : ''}
      </div>
    </div>`;
    if (i < stops.length-1 && stops[i].lat && stops[i+1].lat) {
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

  const sightMins = sel.reduce((s,a)=>s+a.dur,0);
  const driveMin  = Math.round(totalDurS/60);
  const distKm    = (totalDistM/1000).toFixed(1);
  const fuelCost  = State.transport==='bike'?Math.round(totalDistM/1000/30*110): State.transport==='car'?Math.round(totalDistM/1000/12*100):0;
  const tollCost  = ['car','bike'].includes(State.transport)?Math.round(totalDistM/1000/10*5):0;
  const entryCost = sel.reduce((s,a)=>s+a.fee,0);
  const foodEst   = State.travelers*State.days*600;
  const hotelEst  = State.days*2000;

  if (js) js.innerHTML = [
    ['🛣️ Total Road Distance', distKm+' km'],
    ['🚗 Driving Time',         fmtHrs(driveMin)],
    ['📍 Sightseeing Time',     fmtHrs(sightMins)],
    ['👁️ Stops',               sel.length+' attractions'],
    ['🌙 Trip Duration',        State.days+' Days'],
    ['🚗 Transport Mode',       State.transport.charAt(0).toUpperCase()+State.transport.slice(1)],
  ].map(([l,v])=>`<div class="js-row"><span class="js-label">${l}</span><span class="js-value">${v}</span></div>`).join('');

  if (cb) cb.innerHTML = [
    ['⛽ Fuel',         fmtINR(fuelCost)],
    ['🚧 Tolls',        fmtINR(tollCost)],
    ['🎟️ Entry Fees',  fmtINR(entryCost)],
    ['🍽️ Food (est.)', fmtINR(foodEst)],
    ['🏨 Hotel (est.)', fmtINR(hotelEst)],
  ].map(([l,v])=>`<div class="cb-row"><span class="cb-label">${l}</span><span class="cb-amount">${v}</span></div>`).join('') +
  `<hr><div class="cb-row"><span class="cb-label fw-bold">💰 Total Estimate</span><span class="cb-amount fw-bold text-primary">${fmtINR(fuelCost+tollCost+entryCost+foodEst+hotelEst)}</span></div>`;

  // Save for later steps
  State.routeData = { distKm, driveMin, fuelCost, tollCost, entryCost, foodEst, hotelEst };
}

/* ── STEP 5 — Smart Timeline (check-in 8:00, built from planner) ── */
function renderTimeline() {
  const sel  = State.selectedAttractions;
  const cont = document.getElementById('smartTimeline');
  if (!cont) return;

  if (!sel.length) {
    cont.innerHTML = `<div class="text-center py-5 text-muted">
      <div style="font-size:2.5rem">📋</div>
      <p>No attractions selected yet. <a href="#" onclick="goToStep(2)">Go back to Step 2</a></p>
    </div>`;
    return;
  }

  // ── Distribute attractions across days smartly ──────────────────
  // Each day has ~11 usable hours (8:00–19:00). Fill greedily.
  const DAILY_MINUTES = 11 * 60;  // 660 min
  const BREAKFAST_MIN = 30;
  const LUNCH_MIN     = 60;
  const days  = Math.max(1, State.days);
  const days_plan = [];  // array of attraction arrays per day

  let hasPlannerAssignments = false;
  if (State.dayPlanner) {
    for (let d = 1; d <= days; d++) {
      const dayObj = State.dayPlanner[d];
      if (dayObj) {
        ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
          if ((dayObj[zone] || []).length > 0) {
            hasPlannerAssignments = true;
          }
        });
      }
    }
  }

  if (hasPlannerAssignments) {
    for (let d = 1; d <= days; d++) {
      const dayObj = State.dayPlanner[d] || { morning: [], afternoon: [], evening: [], night: [] };
      const dayAttractions = [];
      ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
        (dayObj[zone] || []).forEach(act => {
          if (act.id.startsWith('osm_')) {
            const attraction = State.selectedAttractions.find(a => a.id === act.id);
            if (attraction && !dayAttractions.includes(attraction)) {
              dayAttractions.push(attraction);
            }
          }
        });
      });
      days_plan.push(dayAttractions);
    }
  } else {
    // Fallback: Greedy distribution
    let bucket = [];
    let minutesUsed = BREAKFAST_MIN; // reserve breakfast slot
    sel.forEach((a, idx) => {
      const travelMin = Math.round(a.dist / 35 * 60); // road dist at 35 km/h
      const visitMin  = a.dur;
      const needed    = travelMin + visitMin + (bucket.length === 0 ? 0 : 0);

      // Add lunch slot if we're at midday
      const lunchNeeded = bucket.length > 0 && minutesUsed < (DAILY_MINUTES / 2) &&
                          (minutesUsed + needed) > (DAILY_MINUTES / 2) ? LUNCH_MIN : 0;

      if (days_plan.length < days - 1 && minutesUsed + needed + lunchNeeded > DAILY_MINUTES && bucket.length > 0) {
        // Current day is full, start a new day
        days_plan.push(bucket);
        bucket = [];
        minutesUsed = BREAKFAST_MIN;
      }
      bucket.push(a);
      minutesUsed += travelMin + visitMin + lunchNeeded;
    });
    if (bucket.length) days_plan.push(bucket);

    // Pad empty days if needed
    while (days_plan.length < days) days_plan.push([]);
  }

  const dayLabels = [
    'Arrival & Explore', 'Deep Exploration', 'Adventure Day',
    'Cultural Immersion', 'Leisure & Relax', 'Hidden Gems',
    'Final Day & Departure'
  ];

  cont.innerHTML = `
    <div class="tl-summary-bar">
      <span>📅 ${days} Day${days>1?'s':''}</span>
      <span>📍 ${sel.length} Attraction${sel.length>1?'s':''}</span>
      <span>🕗 Check-in: 8:00 AM</span>
      <span>🚗 ${State.transport.charAt(0).toUpperCase()+State.transport.slice(1)}</span>
    </div>
    <div class="tl-days-wrap">
      ${days_plan.map((attrs, d) => `
        <div class="tl-day-col">
          <div class="tl-day-header">
            <span class="tl-day-num">Day ${d+1}</span>
            <span class="tl-day-label">${dayLabels[d] || ('Exploration Day '+(d+1))}</span>
            <span class="tl-day-count">${attrs.length} stops</span>
          </div>
          <div class="tl-events">
            ${(hasPlannerAssignments ? buildPlannedDayEvents(d+1, days_plan.length) : buildSmartDayEvents(d+1, attrs, days_plan.length)).map(e => buildEventCard(e)).join('')}
          </div>
        </div>
      `).join('')}
    </div>`;
}

function buildPlannedDayEvents(dayNum, totalDays) {
  const events = [];
  const fmtTime = (totalMins) => {
    const h = Math.floor(totalMins / 60);
    const m = totalMins % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  };

  let minutesCursor = 8 * 60; // Start at 08:00
  const dayObj = State.dayPlanner[dayNum];

  // Arrive on Day 1 morning
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

  if (dayObj) {
    const zones = ['morning', 'afternoon', 'evening', 'night'];
    zones.forEach(zone => {
      const list = dayObj[zone] || [];
      list.forEach(act => {
        let durMins = 60;
        if (typeof act.dur === 'number') {
          durMins = act.dur;
        } else if (typeof act.dur === 'string') {
          if (act.dur.endsWith('h')) durMins = parseFloat(act.dur) * 60;
          else if (act.dur.endsWith('m')) durMins = parseInt(act.dur);
        }

        if (act.id.startsWith('osm_')) {
          const attraction = State.selectedAttractions.find(a => a.id === act.id);
          if (attraction) {
            const travelMin = Math.max(10, Math.round(attraction.dist / 35 * 60));
            events.push({
              time: fmtTime(minutesCursor),
              type: 'travel',
              icon: State.transport === 'bike' ? '🏍️' : '🚗',
              title: `Travel to ${attraction.name}`,
              subtitle: `~${attraction.dist} km · ~${travelMin} min by ${State.transport}`,
              priority: 'low',
              duration: travelMin
            });
            minutesCursor += travelMin;

            const visitHrs = (attraction.dur / 60).toFixed(1).replace('.0', '');
            events.push({
              time: fmtTime(minutesCursor),
              type: 'attraction',
              icon: attraction.icon,
              title: attraction.name,
              subtitle: `${attraction.cat} · ${visitHrs}h visit`,
              priority: 'medium',
              duration: attraction.dur
            });
            minutesCursor += attraction.dur;
          }
        } else {
          events.push({
            time: fmtTime(minutesCursor),
            type: act.type,
            icon: act.icon,
            title: act.name,
            subtitle: `Scheduled for ${zone.charAt(0).toUpperCase() + zone.slice(1)}`,
            priority: 'medium',
            duration: durMins
          });
          minutesCursor += durMins;
        }
      });
    });
  }

  // End of Day
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
      title: `Return to ${State.source || 'Home'}`,
      subtitle: 'Safe travels home! 🎉',
      priority: 'high',
      duration: 0
    });
  }

  return events;
}

function buildSmartDayEvents(dayNum, attrs, totalDays) {
  const events = [];
  const fmtTime = (totalMins) => {
    const h = Math.floor(totalMins / 60);
    const m = totalMins % 60;
    const hh = String(h).padStart(2, '0');
    const mm = String(m).padStart(2, '0');
    return `${hh}:${mm}`;
  };

  let minutesCursor = 8 * 60; // Always start at 08:00

  // ── Breakfast / Morning start ──────────────────────────────────
  if (dayNum === 1) {
    events.push({
      time: fmtTime(minutesCursor),
      type: 'hotel',
      icon: '🏨',
      title: `Arrive at ${State.dest.split(',')[0]} & Hotel Check-in`,
      subtitle: 'Freshen up and get ready for the day',
      priority: 'high',
      duration: 30
    });
    minutesCursor += 30;
    events.push({
      time: fmtTime(minutesCursor),
      type: 'food',
      icon: '🍳',
      title: 'Breakfast',
      subtitle: 'Fuel up before exploring',
      priority: 'medium',
      duration: 30
    });
    minutesCursor += 30;
  } else {
    events.push({
      time: fmtTime(minutesCursor),
      type: 'food',
      icon: '🍳',
      title: 'Hotel Breakfast',
      subtitle: 'Start Day ' + dayNum + ' energised',
      priority: 'medium',
      duration: 30
    });
    minutesCursor += 30;
  }

  let lunchAdded = false;
  const lunchThreshold = 12 * 60; // 12:00

  attrs.forEach((a, i) => {
    const travelMin = Math.max(10, Math.round(a.dist / 35 * 60));

    // ── Travel connector ────────────────────────────────────────
    events.push({
      time: fmtTime(minutesCursor),
      type: 'travel',
      icon: State.transport === 'bike' ? '🏍️' : State.transport === 'train' ? '🚂' : State.transport === 'bus' ? '🚌' : '🚗',
      title: `Travel to ${a.name}`,
      subtitle: `~${a.dist} km · ~${travelMin} min by ${State.transport}`,
      priority: 'low',
      duration: travelMin
    });
    minutesCursor += travelMin;

    // ── Lunch break if we cross midday ─────────────────────────
    if (!lunchAdded && minutesCursor >= lunchThreshold) {
      events.push({
        time: fmtTime(minutesCursor),
        type: 'food',
        icon: '🍽️',
        title: 'Lunch Break',
        subtitle: 'Local cuisine near ' + a.name,
        priority: 'medium',
        duration: 60
      });
      minutesCursor += 60;
      lunchAdded = true;
    }

    // ── Attraction visit ────────────────────────────────────────
    const visitHrs = (a.dur / 60).toFixed(1).replace('.0','');
    events.push({
      time: fmtTime(minutesCursor),
      type: 'attraction',
      icon: a.icon,
      title: a.name,
      subtitle: `${a.cat} · ${visitHrs}h visit · ★ ${a.rating}`,
      priority: i === 0 ? 'high' : 'medium',
      duration: a.dur
    });
    minutesCursor += a.dur;
  });

  // ── Late lunch if not already added ──────────────────────────
  if (!lunchAdded && attrs.length > 0) {
    events.push({
      time: fmtTime(minutesCursor),
      type: 'food',
      icon: '🍽️',
      title: 'Lunch / Snack Break',
      subtitle: 'Recharge before the afternoon',
      priority: 'medium',
      duration: 45
    });
    minutesCursor += 45;
    lunchAdded = true;
  }

  // ── Dinner ─────────────────────────────────────────────────
  const dinnerTime = Math.max(minutesCursor, 19 * 60); // min 7 PM
  events.push({
    time: fmtTime(dinnerTime),
    type: 'food',
    icon: '🌙',
    title: 'Dinner',
    subtitle: dayNum < totalDays ? 'Relax & rest up for tomorrow' : 'Celebrate your trip!',
    priority: 'medium',
    duration: 60
  });

  // ── Hotel / Departure ──────────────────────────────────────
  if (dayNum < totalDays) {
    events.push({
      time: fmtTime(dinnerTime + 60),
      type: 'hotel',
      icon: '🏨',
      title: 'Back to Hotel',
      subtitle: 'Rest for the next day of adventures',
      priority: 'low',
      duration: 0
    });
  } else {
    events.push({
      time: fmtTime(dinnerTime + 60),
      type: 'travel',
      icon: '🏠',
      title: `Return to ${State.source || 'Home'}`,
      subtitle: 'Safe travels! Thanks for using AI Travel Planner 🎉',
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


/* ── STEP 6 — Detail grid + drawer ──────────────────────────────── */
function renderDetailGrid() {
  const grid = document.getElementById('detailAttractionGrid');
  if (!grid) return;
  const sel = State.selectedAttractions;
  if (!sel.length) { grid.innerHTML=`<div class="text-center py-5 text-muted" style="grid-column:1/-1"><p>No attractions selected. <a href="#" onclick="goToStep(2)">Go back to Step 2</a></p></div>`; return; }
  grid.innerHTML = sel.map(a=>`
    <div class="dg-card">
      <div class="dg-image" style="background-image:url('${a.img}');background-color:#e5e7eb">
        <div class="dg-overlay"><div class="dg-name">${a.name}</div></div>
      </div>
      <div class="dg-body">
        <div class="dg-tags"><span class="dg-tag">${a.icon} ${a.cat}</span><span class="dg-tag">${a.dist} km</span></div>
        <button class="dg-explore" onclick="openDrawer('${a.id}')"><i class="bi bi-info-circle me-2"></i>Full Details</button>
      </div>
    </div>`).join('');
}
function openDrawer(id) {
  const a = State.selectedAttractions.find(x=>x.id===id) || State.liveAttractions.find(x=>x.id===id);
  if (!a) return;
  document.getElementById('drawerContent').innerHTML = `
    <div class="drawer-gallery">
      <div class="main-img" style="background-image:url('${a.img}');background-color:#e5e7eb"></div>
      <div class="sub-img" style="background-image:url('https://picsum.photos/seed/${`${a.id||0}1`}/400/250');background-color:#e5e7eb"></div>
      <div class="sub-img" style="background-image:url('https://picsum.photos/seed/${`${a.id||0}2`}/400/250');background-color:#e5e7eb"></div>
    </div>
    <div class="drawer-section">
      <div style="font-size:1.1rem;font-weight:800;margin-bottom:4px">${a.icon} ${a.name}</div>
      <div style="color:var(--wizard-accent);font-weight:600;font-size:.85rem;text-transform:uppercase;margin-bottom:12px">${a.cat}</div>
      <p style="color:var(--text-muted);font-size:.88rem;line-height:1.7">${a.desc}</p>
    </div>
    <div class="drawer-section">
      <h5>📋 Quick Info</h5>
      <div class="drawer-info-grid">
        <div class="di-item"><div class="di-label">⏰ Visit Duration</div><div class="di-value">${fmtHrs(a.dur)}</div></div>
        <div class="di-item"><div class="di-label">📍 Distance</div><div class="di-value">${a.dist} km</div></div>
        <div class="di-item"><div class="di-label">⭐ Rating</div><div class="di-value">${a.rating}/5</div></div>
        <div class="di-item"><div class="di-label">💪 Difficulty</div><div class="di-value">${a.difficulty}</div></div>
        <div class="di-item"><div class="di-label">🕐 Opening</div><div class="di-value">${a.opening}</div></div>
        ${a.website?`<div class="di-item"><div class="di-label">🌐 Website</div><div class="di-value"><a href="${a.website}" target="_blank" class="text-primary">Visit</a></div></div>`:''}
      </div>
    </div>
    <div class="drawer-section"><h5>💡 Travel Tips</h5>${a.tips.map(t=>`<div style="display:flex;gap:8px;margin-bottom:6px;font-size:.85rem"><span>✅</span><span>${t}</span></div>`).join('')}</div>
    <div class="drawer-section"><h5>📦 Packing Suggestions</h5><div style="display:flex;flex-wrap:wrap;gap:6px">${['Comfortable shoes','Water bottle','Sunscreen','Camera','Raincoat','Snacks'].map(p=>`<span class="dg-tag">${p}</span>`).join('')}</div></div>
    <div class="drawer-section"><h5>⭐ Reviews</h5>${a.review.map(r=>`<div class="review-card"><div class="review-author">${r.author} ${'⭐'.repeat(r.stars)}</div><div class="review-text">${r.text}</div></div>`).join('')}</div>
  `;
  document.getElementById('detailDrawer').classList.add('open');
}
function closeDrawer() { document.getElementById('detailDrawer').classList.remove('open'); }

function getDayRoutePoints(d) {
  const points = [];
  
  if (State.sourceLat && State.sourceLon) {
    points.push({ lat: State.sourceLat, lon: State.sourceLon });
  }
  
  let hasAssigned = false;
  if (State.dayPlanner && State.dayPlanner[d]) {
    const dayObj = State.dayPlanner[d];
    ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
      (dayObj[zone] || []).forEach(act => {
        if (act.id.startsWith('osm_')) {
          const attraction = State.selectedAttractions.find(a => a.id === act.id);
          if (attraction) {
            points.push({ lat: attraction.lat, lon: attraction.lon });
            hasAssigned = true;
          }
        }
      });
    });
  }
  
  if (!hasAssigned) {
    const dayAttrs = State.selectedAttractions.filter((_, idx) => idx % Math.max(1, State.days) === (d - 1));
    dayAttrs.forEach(a => {
      points.push({ lat: a.lat, lon: a.lon });
    });
  }

  if (State.sourceLat && State.sourceLon && points.length > 1) {
    points.push({ lat: State.sourceLat, lon: State.sourceLon });
  }
  
  return points;
}

/* ── STEP 7 — MapLibre real tile map ──────────────────────────────── */
function renderMap() {
  const sel = State.selectedAttractions;
  const nl  = document.getElementById('nearbyList');
  if (nl) nl.innerHTML = [
    ['⛽','Fuel Station','~0.5 km'],['🏥','Hospital','~1.2 km'],['👮','Police','~0.8 km'],
    ['🅿️','Parking','~0.3 km'],['🏪','Local Store','~1.0 km'],['🏦','ATM','~0.2 km']
  ].map(([icon,name,dist])=>`<div class="nearby-item"><span class="nearby-icon">${icon}</span><div><div style="font-weight:600">${name}</div><div style="font-size:.7rem;color:var(--text-muted)">${dist}</div></div></div>`).join('');

  // If MapLibre isn't loaded yet, bail gracefully
  if (typeof maplibregl === 'undefined') {
    document.getElementById('mapLibreMap').innerHTML = '<div class="d-flex align-items-center justify-content-center h-100 text-muted">Map loading…</div>';
    return;
  }

  // Destroy previous instance to prevent duplicate map
  if (State.mapInstance) { State.mapInstance.remove(); State.mapInstance = null; }

  const center = sel.length
    ? [sel[0].lon, sel[0].lat]
    : State.destLon ? [State.destLon, State.destLat] : [77.5946, 12.9716];

  const map = new maplibregl.Map({
    container: 'mapLibreMap',
    style: 'https://tiles.openfreemap.org/styles/liberty',
    center,
    zoom: sel.length ? 11 : 9,
    attributionControl: true,
  });
  State.mapInstance = map;
  State.mapSatellite = false;

  map.addControl(new maplibregl.NavigationControl(), 'top-right');

  map.on('load', () => {
    // Add source marker
    if (State.sourceLat) {
      new maplibregl.Marker({ color: '#ef4444', scale: 1.1 })
        .setLngLat([State.sourceLon, State.sourceLat])
        .setPopup(new maplibregl.Popup().setHTML(`<strong>🏠 ${State.source || 'Start'}</strong>`))
        .addTo(map);
    }

    // Add destination marker
    if (State.destLat) {
      new maplibregl.Marker({ color: '#0062FF', scale: 1.1 })
        .setLngLat([State.destLon, State.destLat])
        .setPopup(new maplibregl.Popup().setHTML(`<strong>🏁 ${State.dest.split(',')[0]}</strong>`))
        .addTo(map);
    }

    // Add attraction pins
    const bounds = new maplibregl.LngLatBounds();
    sel.forEach((a, i) => {
      if (!a.lat || !a.lon) return;
      const el = document.createElement('div');
      el.style.cssText = `width:36px;height:36px;background:#10b981;border-radius:50%;border:3px solid #fff;display:flex;align-items:center;justify-content:center;font-size:1rem;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.3);`;
      el.textContent = a.icon;
      new maplibregl.Marker({ element: el })
        .setLngLat([a.lon, a.lat])
        .setPopup(new maplibregl.Popup({ offset: 20 }).setHTML(
          `<strong>${a.icon} ${a.name}</strong><br><small>${a.cat} · ${a.dist} km · ⏱ ${fmtHrs(a.dur)}</small>`
        ))
        .addTo(map);
      bounds.extend([a.lon, a.lat]);
    });

    // Group and draw route lines via OSRM proxy per day
    const dayColors = ['#0062FF', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#ec4899', '#14b8a6'];
    for (let d = 1; d <= State.days; d++) {
      const pts = getDayRoutePoints(d);
      if (pts.length >= 2) {
        const coords = pts.map(p => `${p.lon},${p.lat}`).join(';');
        const color = dayColors[(d - 1) % dayColors.length];
        const proxyUrl = `/planner/api/osrm?profile=car&coords=${encodeURIComponent(coords)}&overview=full&geometries=geojson`;

        fetch(proxyUrl)
          .then(r => r.json())
          .then(data => {
            if (data.code === 'Ok' && data.routes && data.routes[0]) {
              const routeId = `route-day-${d}`;
              map.addSource(routeId, {
                type: 'geojson',
                data: {
                  type: 'Feature',
                  geometry: data.routes[0].geometry
                }
              });
              map.addLayer({
                id: `${routeId}-line`,
                type: 'line',
                source: routeId,
                layout: {
                  'line-join': 'round',
                  'line-cap': 'round'
                },
                paint: {
                  'line-color': color,
                  'line-width': 5,
                  'line-opacity': 0.85
                }
              });
            }
          })
          .catch(() => {});
      }
    }

    // Fit map to all pins
    if (sel.length && !bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 60, maxZoom: 13, duration: 1200 });
    }
  });
}

function mapFlyToRoute() {
  if (!State.mapInstance || !State.selectedAttractions.length) return;
  const first = State.selectedAttractions[0];
  if (first.lat) State.mapInstance.flyTo({ center: [first.lon, first.lat], zoom: 12, speed: 1.4 });
}
function mapToggleSatellite() {
  if (!State.mapInstance) return;
  State.mapSatellite = !State.mapSatellite;
  const style = State.mapSatellite
    ? 'https://tiles.openfreemap.org/styles/positron'
    : 'https://tiles.openfreemap.org/styles/liberty';
  State.mapInstance.setStyle(style);
}
function mapShowNearby() {
  showToast('📍 Nearby places fetched from OpenStreetMap data', 'info');
}

/* ── STEP 6 — State-Aware Day Planner ────────────────────────────── */
function renderDayPlanner() {
  const sel = State.selectedAttractions;
  
  // Initialize state structures if not already present
  if (!State.dayPlanner) {
    State.dayPlanner = {};
  }
  for (let d = 1; d <= State.days; d++) {
    if (!State.dayPlanner[d]) {
      State.dayPlanner[d] = { morning: [], afternoon: [], evening: [], night: [] };
    }
  }
  if (!State.currentPlannerDay) {
    State.currentPlannerDay = 1;
  }

  // Render Day Selector Tabs
  const ds = document.getElementById('daySelector');
  if (ds) {
    ds.innerHTML = Array.from({length: State.days}, (_, i) => {
      const dNum = i + 1;
      const activeClass = dNum === State.currentPlannerDay ? 'active' : '';
      return `<button class="day-btn ${activeClass}" onclick="switchPlanDay(${dNum}, this)">Day ${dNum}</button>`;
    }).join('');
  }

  // Determine which attractions are already assigned anywhere in the day planner
  const assignedIds = new Set();
  Object.values(State.dayPlanner).forEach(dayObj => {
    ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
      (dayObj[zone] || []).forEach(act => {
        if (act.id.startsWith('osm_')) {
          assignedIds.add(act.id);
        }
      });
    });
  });

  // Populate drop zones for the current active day
  const currentDayPlan = State.dayPlanner[State.currentPlannerDay];
  ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
    const dz = document.getElementById(zone + '-drop');
    if (!dz) return;
    const items = currentDayPlan[zone] || [];
    dz.innerHTML = items.map((act, idx) => `
      <div class="activity-card" draggable="true" data-id="${act.id}" data-type="${act.type}" data-zone="${zone}" data-index="${idx}">
        <div class="act-icon">${act.icon}</div>
        <div class="act-name">${act.name}</div>
        <div class="act-duration">${act.dur}</div>
        <span class="act-type-badge type-${act.type}">${act.type}</span>
        <button class="act-remove-btn" onclick="removePlannedActivity(${State.currentPlannerDay}, '${zone}', ${idx}); event.stopPropagation();">×</button>
      </div>
    `).join('');
    dz.querySelectorAll('.activity-card').forEach(initCardDrag);
  });

  // Render the Unscheduled Activities Pool (excluding assigned attractions)
  const pool = document.getElementById('poolItems');
  if (pool) {
    const unassignedAttractions = sel.filter(a => !assignedIds.has(a.id));
    const poolActs = [
      ...unassignedAttractions.map(a => ({ id: a.id, icon: a.icon, name: a.name, dur: fmtHrs(a.dur), type: 'attraction' })),
      { id: 'breakfast', icon: '🥞', name: 'Breakfast', dur: '30m', type: 'food' },
      { id: 'lunch', icon: '🍛', name: 'Lunch', dur: '45m', type: 'food' },
      { id: 'dinner', icon: '🍽️', name: 'Dinner', dur: '60m', type: 'food' },
      { id: 'rest', icon: '😴', name: 'Rest at Hotel', dur: '60m', type: 'leisure' },
      { id: 'shopping', icon: '🛍️', name: 'Local Shopping', dur: '45m', type: 'leisure' },
      { id: 'depart', icon: '🚗', name: 'Travel to Destination', dur: '2h', type: 'travel' },
      { id: 'return', icon: '🔙', name: 'Return Journey', dur: '2h', type: 'travel' },
      ...(State.customPoolActivities || [])
    ];
    pool.innerHTML = poolActs.map(a => buildActivityCard(a)).join('');
    pool.querySelectorAll('.activity-card').forEach(initCardDrag);
  }
}
function buildActivityCard(a) {
  return `
    <div class="activity-card" draggable="true" data-id="${a.id}" data-type="${a.type}">
      <div class="act-icon">${a.icon}</div>
      <div class="act-name">${a.name}</div>
      <div class="act-duration">${a.dur}</div>
      <span class="act-type-badge type-${a.type}">${a.type}</span>
    </div>`;
}

function initCardDrag(card) {
  card.addEventListener('dragstart', e => {
    e.dataTransfer.setData('text/plain', JSON.stringify({
      id: card.dataset.id,
      type: card.dataset.type,
      sourceZone: card.dataset.zone || null,
      sourceIndex: card.dataset.index !== undefined ? parseInt(card.dataset.index) : null
    }));
    setTimeout(() => card.classList.add('dragging'), 0);
  });
  card.addEventListener('dragend', () => card.classList.remove('dragging'));
}

function allowDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.add('drag-over');
  e.currentTarget.addEventListener('dragleave', () => e.currentTarget.classList.remove('drag-over'), { once: true });
}

function dropActivity(e, zone) {
  e.preventDefault();
  const dz = document.getElementById(zone + '-drop');
  if (dz) dz.classList.remove('drag-over');

  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    const { id, type, sourceZone, sourceIndex } = data;

    let actObject = null;
    
    // Find attraction details or create a dummy object for custom items
    if (id.startsWith('osm_')) {
      const attraction = State.selectedAttractions.find(a => a.id === id);
      if (attraction) {
        actObject = { id: attraction.id, icon: attraction.icon, name: attraction.name, dur: fmtHrs(attraction.dur), type: 'attraction' };
      }
    } else if (id.startsWith('custom_')) {
      const customAct = State.customPoolActivities.find(c => c.id === id);
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
      actObject = defaults[id];
    }

    if (!actObject) return;

    // Remove from old zone if it was moved
    if (sourceZone !== null && sourceIndex !== null) {
      State.dayPlanner[State.currentPlannerDay][sourceZone].splice(sourceIndex, 1);
    }

    // Add to new zone
    State.dayPlanner[State.currentPlannerDay][zone].push(actObject);

    // Sync attraction array order
    syncAttractionsOrderFromPlanner();
    
    // Save state to localStorage
    saveStateToLS();

    // Re-render Day Planner
    renderDayPlanner();
  } catch (err) {
    console.error("Drop failed:", err);
  }
}

function removePlannedActivity(day, zone, idx) {
  if (State.dayPlanner[day] && State.dayPlanner[day][zone]) {
    State.dayPlanner[day][zone].splice(idx, 1);
    syncAttractionsOrderFromPlanner();
    saveStateToLS();
    renderDayPlanner();
  }
}

function switchPlanDay(day, btn) {
  State.currentPlannerDay = day;
  document.querySelectorAll('.day-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  saveStateToLS();
  renderDayPlanner();
}

function syncAttractionsOrderFromPlanner() {
  if (!State.dayPlanner) return;
  const ordered = [];
  
  // Go through day planner chronologically
  for (let d = 1; d <= State.days; d++) {
    const dayObj = State.dayPlanner[d];
    if (!dayObj) continue;
    ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
      (dayObj[zone] || []).forEach(act => {
        if (act.id.startsWith('osm_')) {
          const attraction = State.selectedAttractions.find(a => a.id === act.id);
          if (attraction && !ordered.includes(attraction)) {
            ordered.push(attraction);
          }
        }
      });
    });
  }

  // Append any selected attractions that haven't been assigned yet
  State.selectedAttractions.forEach(a => {
    if (!ordered.includes(a)) {
      ordered.push(a);
    }
  });

  State.selectedAttractions = ordered;
}

function addCustomActivityPool() {
  const nameInput = document.getElementById('customActName');
  const typeSelect = document.getElementById('customActType');
  const durInput = document.getElementById('customActDur');
  
  const name = nameInput.value.trim();
  const durVal = durInput.value.trim() || '1h';
  if (!name) {
    showToast('⚠️ Please enter an activity name first.', 'warning');
    return;
  }
  const type = typeSelect.value;
  const icons = { leisure: '🎯', food: '🍽️', travel: '🚗' };
  const icon = icons[type] || '✨';
  
  const id = 'custom_' + Date.now();
  
  if (!State.customPoolActivities) {
    State.customPoolActivities = [];
  }
  State.customPoolActivities.push({
    id,
    icon,
    name,
    dur: durVal,
    type
  });
  
  nameInput.value = '';
  durInput.value = '';
  saveStateToLS();
  renderDayPlanner();
  showToast(`✅ Added custom activity "${name}" to the pool!`, 'success');
}

function optimizeRouteTSP() {
  const sel = State.selectedAttractions;
  if (sel.length <= 2) {
    showToast('💡 Optimization requires at least 3 selected attractions.', 'info');
    return;
  }
  
  const startLat = State.destLat || (sel.length ? sel[0].lat : 0);
  const startLon = State.destLon || (sel.length ? sel[0].lon : 0);
  
  const unvisited = [...sel];
  const ordered = [];
  
  let curLat = startLat;
  let curLon = startLon;
  
  while (unvisited.length > 0) {
    let nearestIdx = 0;
    let minDist = Infinity;
    for (let i = 0; i < unvisited.length; i++) {
      const u = unvisited[i];
      const d = haversineKm(curLat, curLon, u.lat, u.lon);
      if (d < minDist) {
        minDist = d;
        nearestIdx = i;
      }
    }
    const nextNode = unvisited.splice(nearestIdx, 1)[0];
    ordered.push(nextNode);
    curLat = nextNode.lat;
    curLon = nextNode.lon;
  }
  
  State.selectedAttractions = ordered;
  
  // Re-fill Day Planner based on new optimized order
  if (State.dayPlanner) {
    State.dayPlanner = {};
    for (let d = 1; d <= State.days; d++) {
      State.dayPlanner[d] = { morning: [], afternoon: [], evening: [], night: [] };
    }
    const days = Math.max(1, State.days);
    State.selectedAttractions.forEach((a, i) => {
      const day = (i % days) + 1;
      const zones = ['morning', 'afternoon', 'evening', 'night'];
      const zone = zones[Math.floor(i / days) % 4];
      State.dayPlanner[day][zone].push({
        id: a.id, icon: a.icon, name: a.name, dur: fmtHrs(a.dur), type: 'attraction'
      });
    });
  }
  
  saveStateToLS();
  
  // Refresh current view
  if (State.step === 3) renderSelectedList();
  if (State.step === 5) renderDayPlanner();
  
  showToast('🚀 Route optimized using AI nearest-neighbor algorithm to minimize travel distance!', 'success');
}

/* ── STEP 9 — Analytics ──────────────────────────────────────────── */
function renderAnalytics() {
  const sel  = State.selectedAttractions;
  const grid = document.getElementById('analyticsGrid');
  if (!grid) return;
  const rd   = State.routeData || {};
  const totalMins  = sel.reduce((s,a)=>s+a.dur,0);
  const fuelCost   = rd.fuelCost  || (State.transport==='bike'?Math.round(sel.reduce((s,a)=>s+a.dist,0)/30*110):Math.round(sel.reduce((s,a)=>s+a.dist,0)/12*100));
  const totalSpend = fuelCost + sel.reduce((s,a)=>s+a.fee,0) + State.travelers*State.days*600 + State.days*2000;
  const distKm     = rd.distKm || sel.reduce((s,a)=>s+a.dist,0);
  const driveMin   = rd.driveMin || Math.round(+distKm/45*60);

  grid.innerHTML = [
    {grad:'ac-grad-blue',  icon:'🛣️', val:distKm+' km',          label:'Total Distance',   sub:'Real road distance (OSRM)'},
    {grad:'ac-grad-gold',  icon:'🚗', val:fmtHrs(driveMin),      label:'Driving Time',      sub:'Real routing estimate'},
    {grad:'ac-grad-green', icon:'👁️', val:fmtHrs(totalMins),    label:'Sightseeing',       sub:'Total at attractions'},
    {grad:'ac-grad-purple',icon:'🚶', val:Math.round(totalMins/3)+' steps',label:'Walking Est.', sub:'At attractions'},
    {grad:'ac-grad-sunset',icon:'⛽', val:fmtINR(fuelCost),      label:'Fuel Cost',         sub:State.transport},
    {grad:'ac-grad-blue',  icon:'💸', val:fmtINR(totalSpend),    label:'Total Estimate',    sub:'All categories'},
    {grad:'ac-grad-green', icon:'💰', val:fmtINR(Math.max(0,State.budget-totalSpend)), label:'Remaining Budget', sub:'From '+fmtINR(State.budget)},
    {grad:'ac-grad-gold',  icon:'📍', val:sel.length,            label:'Attractions',       sub:'OSM real places'},
  ].map(c=>`<div class="analytics-card ${c.grad}" data-icon="${c.icon}"><div class="ac-val">${c.val}</div><div class="ac-label">${c.label}</div><div class="ac-sub">${c.sub}</div></div>`).join('');

  setTimeout(()=>{
    ['budgetChart','timeChart'].forEach(id=>{const el=document.getElementById(id);if(el&&State.charts[id])State.charts[id].destroy();});
    const bc=document.getElementById('budgetChart');
    if(bc)State.charts.budgetChart=new Chart(bc,{type:'doughnut',data:{labels:['Fuel','Entry Fees','Food','Hotel','Shopping'],datasets:[{data:[fuelCost,sel.reduce((s,a)=>s+a.fee,0),State.travelers*State.days*600,State.days*2000,State.travelers*500],backgroundColor:['#0062FF','#10b981','#f59e0b','#8b5cf6','#ef4444'],borderWidth:0,hoverOffset:8}]},options:{plugins:{legend:{position:'bottom'}},cutout:'65%'}});
    const tc=document.getElementById('timeChart');
    if(tc&&sel.length)State.charts.timeChart=new Chart(tc,{type:'bar',data:{labels:sel.map(a=>a.name.split(' ')[0]),datasets:[{label:'Minutes',data:sel.map(a=>a.dur),backgroundColor:'#0062FFcc',borderRadius:6,borderWidth:0}]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true},x:{grid:{display:false}}}}});
  },300);
}

/* ── STEP 10 — Overview ──────────────────────────────────────────── */
function renderOverview() {
  const sel  = State.selectedAttractions;
  const body = document.getElementById('overviewBody');
  const rd   = State.routeData || {};
  if (!body) return;
  setText('toh-title', State.dest.split(',')[0] || 'Your Trip');
  setText('toh-sub',   `${State.days} Days · ${State.travelers} Traveler${State.travelers>1?'s':''} · ${State.style}`);
  const fuelCost = rd.fuelCost || 0;
  const totalSpend = fuelCost + sel.reduce((s,a)=>s+a.fee,0)+State.travelers*State.days*600+State.days*2000+State.travelers*500;
  body.innerHTML = `
  <div class="row g-4">
    <div class="col-lg-8">
      <div class="overview-section">
        <div class="overview-section-title"><span>📊</span> Trip Statistics</div>
        <div class="row g-3">
          ${[['📅','Travel Dates',(document.getElementById('w_travel_date')?.value||'TBD')+' → '+(document.getElementById('w_return_date')?.value||'TBD')],['🛣️','Road Distance',(rd.distKm||'—')+' km'],['📍','Attractions',sel.length+' places (OSM)'],['⏰','Sightseeing',fmtHrs(sel.reduce((s,a)=>s+a.dur,0))],['💰','Est. Spend',fmtINR(totalSpend)],['🚗','Transport',State.transport]].map(([i,l,v])=>`<div class="col-6 col-md-4"><div class="glass-card text-center p-3"><div style="font-size:1.5rem">${i}</div><div class="fw-bold">${v}</div><div class="text-muted small">${l}</div></div></div>`).join('')}
        </div>
      </div>
      <div class="overview-section">
        <div class="overview-section-title"><span>📍</span> Selected Attractions</div>
        <div class="row g-2">${sel.map((a,i)=>`<div class="col-md-6"><div class="glass-card d-flex align-items-center gap-3 p-3"><span style="font-size:1.5rem">${a.icon}</span><div><div class="fw-bold" style="font-size:.88rem">${i+1}. ${a.name}</div><div class="text-muted small">${a.cat} · ${a.dist} km · ${fmtHrs(a.dur)}</div>${a.website?`<a href="${a.website}" target="_blank" class="small text-primary">Website →</a>`:''}</div></div></div>`).join('')}</div>
      </div>
      <div class="overview-section">
        <div class="overview-section-title"><span>🎒</span> Packing Checklist</div>
        <div class="checklist-grid">${['ID/Aadhar Card','Phone & Charger','Power Bank','Cash','First Aid Kit','Sunscreen SPF50','Rain Jacket','Comfortable Shoes','Water Bottle','Camera','Medicines','Snacks','Warm Jacket','Insect Repellent','Hand Sanitizer','Backpack','Sunglasses','Umbrella'].map(item=>`<div class="checklist-item"><input type="checkbox" class="form-check-input"/><span>${item}</span></div>`).join('')}</div>
      </div>
      ${document.getElementById('smartTimeline')?.innerHTML ? `
      <div class="overview-section mt-4">
        <div class="overview-section-title"><span>⏰</span> Day-by-Day Timeline</div>
        <div class="overview-print-timeline" style="margin-top: 12px;">
          ${document.getElementById('smartTimeline').innerHTML}
        </div>
      </div>` : ''}
    </div>
    <div class="col-lg-4">
      ${State.weatherData?.current && !State.weatherData.current.error ? `
      <div class="overview-section">
        <div class="overview-section-title"><span>🌤</span> Live Weather — ${State.dest.split(',')[0]}</div>
        <div class="glass-card p-3">
          <div class="weather-temp">${State.weatherData.current.temperature}°C</div>
          <div class="weather-desc text-muted">${State.weatherData.current.description}</div>
          <div class="row g-2 mt-2">
            <div class="col-6"><span class="wkey">💧 Humidity</span><span class="wval">${State.weatherData.current.humidity}%</span></div>
            <div class="col-6"><span class="wkey">💨 Wind</span><span class="wval">${State.weatherData.current.wind_speed} m/s</span></div>
          </div>
        </div>
      </div>` : ''}
      <div class="overview-section">
        <div class="overview-section-title"><span>💰</span> Expense Summary</div>
        <div class="glass-card">${[['⛽ Fuel',fmtINR(fuelCost)],['🎟️ Entry Fees',fmtINR(sel.reduce((s,a)=>s+a.fee,0))],['🍽️ Food',fmtINR(State.travelers*State.days*600)],['🏨 Hotel',fmtINR(State.days*2000)],['🛍️ Shopping',fmtINR(State.travelers*500)]].map(([l,v])=>`<div class="d-flex justify-content-between py-2 border-bottom" style="font-size:.85rem"><span>${l}</span><strong>${v}</strong></div>`).join('')}<div class="d-flex justify-content-between pt-2 fw-bold text-primary"><span>💸 Total</span><span>${fmtINR(totalSpend)}</span></div></div>
      </div>
      <div class="overview-section">
        <div class="overview-section-title"><span>🚨</span> Emergency Contacts</div>
        <div class="emergency-cards">${[{l:'Police',v:'100'},{l:'Ambulance',v:'108'},{l:'Fire',v:'101'},{l:'Tourist Helpline',v:'1363'}].map(e=>`<div class="ec-card"><div class="ec-label">${e.l}</div><div class="ec-value">${e.v}</div></div>`).join('')}</div>
      </div>
    </div>
  </div>`;
}

/* ── Download / Share / Clear / Save ────────────────────────────── */
function downloadItinerary() {
  const sel = State.selectedAttractions;
  const rd  = State.routeData || {};
  const td  = document.getElementById('w_travel_date')?.value || 'TBD';
  const ret = document.getElementById('w_return_date')?.value || 'TBD';
  const lines = [
    `SMART TRAVEL ITINERARY`, `${'='.repeat(50)}`,
    `Destination : ${State.dest}`, `From        : ${State.source}`,
    `Dates       : ${td} → ${ret}`, `Duration    : ${State.days} Days`,
    `Travelers   : ${State.travelers}`, `Style       : ${State.style}`,
    `Transport   : ${State.transport}`,
    `Road Dist   : ${rd.distKm || '—'} km`,
    `Drive Time  : ${rd.driveMin ? fmtHrs(rd.driveMin) : '—'}`,
    `Est. Cost   : ${fmtINR((rd.fuelCost||0)+sel.reduce((s,a)=>s+a.fee,0)+State.travelers*State.days*600+State.days*2000)}`,
    ``, `ATTRACTIONS  (Real data from OpenStreetMap)`, `${'─'.repeat(50)}`,
    ...sel.map((a,i)=>`${i+1}. ${a.name}\n   Category: ${a.cat} | Distance: ${a.dist} km | Visit: ${fmtHrs(a.dur)} | Rating: ${a.rating}`),
    ``, `EMERGENCY CONTACTS`, `${'─'.repeat(50)}`,
    `Police: 100 | Ambulance: 108 | Fire: 101 | Tourist Helpline: 1363`,
    ``, `Powered by: Nominatim · Overpass API · OSRM · OpenWeatherMap`,
    `Generated by AI Travel Planner`
  ];
  const blob = new Blob([lines.join('\n')], {type:'text/plain'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `itinerary_${(State.dest.split(',')[0]).replace(/\s+/g,'_')}_${td}.txt`;
  a.click();
  showToast('✅ Itinerary downloaded!', 'success');
}
function shareTrip() {
  const text = `🗺️ I'm planning a trip to ${State.dest.split(',')[0]} from ${State.source.split(',')[0]}!\n📅 ${State.days} days · 👥 ${State.travelers} travelers · 🎯 ${State.style}\n📍 Attractions: ${State.selectedAttractions.slice(0,3).map(a=>a.name).join(', ')}${State.selectedAttractions.length>3?'…':''}`;
  if (navigator.share) navigator.share({title:`Trip to ${State.dest.split(',')[0]}`, text, url: window.location.href});
  else navigator.clipboard?.writeText(text).then(()=>showToast('✅ Trip details copied to clipboard!','success'));
}
function clearWizard() {
  if (!confirm('Start a fresh plan? Your current selections will be cleared.')) return;
  localStorage.removeItem(LS_KEY);
  location.reload();
}
function saveWizardToDashboard() {
  if (!State.dest) { showToast('⚠️ Please complete Journey Details first', 'warning'); return; }
  const form = document.createElement('form');
  form.method = 'GET';
  form.action = '/planner/new';
  const fields = {
    destination: State.dest.split(',')[0],
    start_date: document.getElementById('w_travel_date')?.value || '',
    end_date: document.getElementById('w_return_date')?.value || '',
    num_days: State.days,
    num_travelers: State.travelers,
    budget: State.budget,
    travel_style: State.style.toLowerCase(),
    transport: State.transport,
  };
  Object.entries(fields).forEach(([k,v]) => {
    const inp = document.createElement('input');
    inp.type = 'hidden'; inp.name = k; inp.value = v;
    form.appendChild(inp);
  });
  document.body.appendChild(form);
  showToast('🚀 Redirecting to AI Planner with your wizard data…', 'success');
  setTimeout(()=>form.submit(), 800);
}
async function saveCustomWizardTripDirectly() {
  if (!State.dest) {
    showToast('⚠️ Please complete Journey Details first', 'warning');
    return;
  }

  showToast('💾 Saving custom itinerary directly to your dashboard…', 'info');

  const payload = {
    destination: State.dest,
    start_date: document.getElementById('w_travel_date')?.value || '',
    end_date: document.getElementById('w_return_date')?.value || '',
    num_days: State.days,
    num_travelers: State.travelers,
    budget: State.budget,
    travel_style: State.style.toLowerCase(),
    transport: State.transport,
    selected_attractions: State.selectedAttractions,
    day_planner: State.dayPlanner || {},
    weather: State.weatherData
  };

  try {
    const response = await fetch('/planner/save_wizard', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (result.success) {
      showToast('🎉 Trip saved successfully!', 'success');
      setTimeout(() => {
        window.location.href = `/planner/${result.trip_id}`;
      }, 1000);
    } else {
      showToast(`❌ Save failed: ${result.error}`, 'danger');
    }
  } catch (error) {
    console.error('Error saving wizard trip:', error);
    showToast('❌ Error connecting to server', 'danger');
  }
}

/* ── Toast ───────────────────────────────────────────────────────── */
function showToast(msg, type='info') {
  const t=document.createElement('div');
  t.className=`alert alert-${type==='warning'?'warning':type==='success'?'success':'info'} alert-toast position-fixed`;
  t.style.cssText='top:80px;right:16px;z-index:9999;width:320px;font-size:.88rem;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.15)';
  t.textContent=msg; document.body.appendChild(t);
  setTimeout(()=>t.remove(),3500);
}

/* ── Scroll reveal ───────────────────────────────────────────────── */
function initScrollReveal() {
  const obs = new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('visible');obs.unobserve(e.target);}}),{threshold:.1});
  document.querySelectorAll('.scroll-reveal').forEach(el=>obs.observe(el));
}
