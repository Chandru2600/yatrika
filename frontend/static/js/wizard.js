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
  days: 3, travelers: 2, budget: 15000, budgetPerPerson: 15000,
  transport: 'car', style: 'Adventure',
  transitMode: 'car', transitCost: 0, transitCostPerPerson: 0, arrivalTime: '10:00',
  transitDetails: null, transitOptions: null,
  selectedAttractions: [],
  liveAttractions: [],        // fetched from Overpass & Verified DB
  loadedAttractionsDest: '',  // destination for which liveAttractions was fetched
  routeData: null,            // from OSRM
  weatherData: null,          // from OWM
  favAttractions: new Set(),
  charts: {},
  mapInstance: null,          // MapLibre instance
  mapSatellite: false,
  activeTimelineDay: 1,
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
      days: snap.days||3, travelers: snap.travelers||2,
      budget: snap.budget || 15000,
      budgetPerPerson: snap.budgetPerPerson || snap.budget || 15000,
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
function osmPhoto(name, cat, tags = {}) {
  if (tags && tags.image && tags.image.startsWith('http')) return tags.image;
  if (tags && tags.wikimedia_commons) {
    const fName = encodeURIComponent(tags.wikimedia_commons.replace(/^File:/i, '').replace(/ /g, '_'));
    return `https://commons.wikimedia.org/wiki/Special:FilePath/${fName}?width=600`;
  }
  const c = (cat || '').toLowerCase();
  const n = (name || '').toLowerCase();
  if (c.includes('waterfall') || n.includes('falls')) {
    return 'https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=600&q=80';
  } else if (c.includes('fort') || c.includes('palace') || c.includes('historic') || n.includes('fort')) {
    return 'https://images.unsplash.com/photo-1596401057633-54a8fe8ef647?auto=format&fit=crop&w=600&q=80';
  } else if (c.includes('view') || c.includes('peak') || n.includes('peak') || n.includes('seat')) {
    return 'https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=600&q=80';
  } else if (c.includes('temple') || c.includes('spiritual') || c.includes('monastery')) {
    return 'https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?auto=format&fit=crop&w=600&q=80';
  }
  return 'https://images.unsplash.com/photo-1506461883276-594a12b11cf3?auto=format&fit=crop&w=600&q=80';
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
  node["historic"~"castle|fort|monument|ruins|palace"](around:${r},${lat},${lon});
  node["natural"~"peak|waterfall|hot_spring|beach|cave_entrance|glacier|volcano"](around:${r},${lat},${lon});
  node["leisure"~"park|garden|nature_reserve|beach_resort|sports_centre"](around:${r},${lat},${lon});
  way["tourism"~"attraction|museum|viewpoint|zoo|theme_park|gallery"](around:${r},${lat},${lon});
  way["historic"~"castle|fort|monument|ruins|palace"](around:${r},${lat},${lon});
  way["leisure"~"park|garden|nature_reserve"](around:${r},${lat},${lon});
  relation["tourism"~"attraction|museum"](around:${r},${lat},${lon});
);
out center tags 100;`;
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

function isMinorReligiousPlace(tags, name) {
  const n = (name || tags?.name || '').toLowerCase();
  const amenity = (tags?.amenity || '').toLowerCase();
  const historic = (tags?.historic || '').toLowerCase();
  const religion = (tags?.religion || '').toLowerCase();

  const isReligious = 
    amenity === 'place_of_worship' ||
    ['temple', 'church', 'mosque', 'shrine', 'synagogue'].includes(historic) ||
    ['muslim', 'christian', 'hindu', 'jain', 'sikh', 'jewish', 'buddhist'].includes(religion) ||
    /\b(temple|mandir|church|masjid|mosque|dargah|shrine|chapel|ashram|st\.?\s+[a-z]+)\b/i.test(n);

  if (!isReligious) return false;

  // Universally famous major landmarks to preserve
  const FAMOUS_LANDMARKS = [
    'golden temple', 'namdroling', 'bylakuppe', 'talakaveri', 'talacauvery', 'omkareshwara',
    'kukke subramanya', 'subramanya', 'chamundeshwari', 'somnath', 'kedarnath', 'badrinath',
    'meenakshi', 'brihadeeswarar', 'konark', 'jagannath', 'tirupati', 'venkateswara',
    'vaishno devi', 'shirdi', 'mahabodhi', 'akshardham', 'lotus temple', 'virupaksha',
    'murudeshwar', 'belur', 'halebidu', 'gommateshwara', 'shravanabelagola', 'siddhivinayak',
    'padmanabhaswamy', 'rameshwaram', 'kashi vishwanath', 'basilica of bom jesus', 'se cathedral'
  ];

  if (FAMOUS_LANDMARKS.some(f => n.includes(f))) {
    return false; // Very famous landmark — keep it!
  }

  // If designated UNESCO / major heritage with Wikipedia documentation
  const isMajorHeritage = tags?.heritage || (tags?.wikipedia && tags?.wikidata);
  if (isMajorHeritage) return false;

  // Otherwise, it's a minor / local neighborhood place of worship -> filter out
  return true;
}

const BARE_GENERIC_NAMES = new Set([
  "monument", "statue", "viewpoint", "waterfall", "temple", "mandir", "church", "mosque",
  "park", "museum", "cave", "dam", "building", "fort", "palace", "lake", "beach", "garden",
  "unknown", "unnamed", "place", "site", "heritage site", "tourist spot", "tourist attraction",
  "scenic spot", "scenic point", "point", "hill", "peak", "river", "forest", "safari",
  "gate", "arch", "tomb", "dome", "tank", "pool", "top", "home", "reef", "memorial",
  "attraction", "sights", "sightseeing"
]);

function isGenericPlaceholderName(name) {
  if (!name || typeof name !== 'string') return true;
  const s = name.trim();
  if (s.length < 3) return true;

  // 1. Matches ASI numbered placeholders and generic monument tags
  // e.g., "ASI Monument #0157 - Karnataka Protected Heritage", "Monument #12", "Camp #3", "Point #9", "#4500"
  if (/ASI Monument|Monument\s*#|#\d+|Protected Heritage|ASI Protected|Protected Site/i.test(s)) {
    return true;
  }

  // 2. Pure numbers or alphanumeric plot/grid codes like "2620", "24-F", "8 RD", "S-60", "1 AD"
  if (/^[\d\s\-_#]+$/.test(s) || /^\d+[A-Za-z\-_]+$/.test(s) || /^[A-Za-z0-9\-_]{1,4}$/.test(s)) {
    return true;
  }

  // 3. Street addresses / house markers mistakenly tagged as attractions
  if (/\b(?:H#|St\s*\d+|G\d+-\d+|Market ID|Plot No|Sector\s*\d+)\b/i.test(s)) {
    return true;
  }

  // 4. Bare generic category words without a specific name
  if (BARE_GENERIC_NAMES.has(s.toLowerCase())) {
    return true;
  }

  return false;
}

async function fetchAttractions(lat, lon) {
  const RADIUS = 80000; // 80 km radius around destination / base camp
  let elements = [];
  try {
    const res = await fetch('/planner/api/overpass', {
      method: 'POST',
      body: 'data=' + encodeURIComponent(_buildOverpassQL(lat, lon, RADIUS)),
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    if (!res.ok) return [];
    const data = await res.json();
    elements = (data.elements || []).filter(e => e.tags && e.tags.name && !isGenericPlaceholderName(e.tags.name) && !isMinorReligiousPlace(e.tags, e.tags.name));
  } catch { return []; }

  return elements
    .map(e => {
      const lt = e.lat  || e.center?.lat;
      const ln = e.lon  || e.center?.lon;
      if (!lt || !ln) return null;
      const dist = haversineKm(lat, lon, lt, ln);
      // Apply road-distance factor: actual road distance is ~1.35x the straight-line
      const roadDist = Math.round(dist * 1.35 * 10) / 10;
      if (dist > 80) return null;
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
        img:  osmPhoto(nm, cat, e.tags),
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

  // Restore saved state only if URL did not specify a different destination
  const urlParams = new URLSearchParams(window.location.search);
  const urlDest = urlParams.get('destination');
  const saved = loadStateFromLS();
  if (saved && saved.dest && (!urlDest || urlDest.toLowerCase().trim() === saved.dest.toLowerCase().trim())) {
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
    fetchInterCityTransit();
    showToast(`✅ Restored your last session: ${State.dest.split(',')[0]}`, 'success');
  } else if (urlDest) {
    State.dest = urlDest.trim();
    const coords = resolveDestinationCoords(State.dest);
    State.destLat = coords.lat;
    State.destLon = coords.lon;
    State.selectedStay = null;
    State.liveAttractions = [];
    State.selectedAttractions = [];
    State.loadedAttractionsDest = '';
    cachedAttractionsDest = '';
    cachedInstantAttractions = [];
  }

  // Source & Destination placeSelected bindings
  const wSourceInput = document.getElementById('w_source');
  if (wSourceInput) {
    wSourceInput.addEventListener('placeSelected', (e) => {
      const p = e.detail || {};
      State.source = wSourceInput.value.trim();
      if (p.lat) State.sourceLat = p.lat;
      if (p.lon) State.sourceLon = p.lon;
      updatePreviewCard();
      fetchInterCityTransit();
      saveStateToLS();
    });
  }

  const wDestInput = document.getElementById('w_dest');
  if (wDestInput) {
    wDestInput.addEventListener('placeSelected', async (e) => {
      const p = e.detail || {};
      const newDest = wDestInput.value.trim();
      const changed = (State.dest || '').toLowerCase().trim() !== newDest.toLowerCase().trim();
      State.dest = newDest;
      if (p.lat && p.lon) {
        State.destLat = p.lat;
        State.destLon = p.lon;
      } else {
        const coords = resolveDestinationCoords(newDest);
        State.destLat = coords.lat;
        State.destLon = coords.lon;
      }
      if (changed) {
        State.selectedStay = null;
        State.liveAttractions = [];
        State.selectedAttractions = [];
        State.loadedAttractionsDest = '';
        cachedAttractionsDest = '';
        cachedInstantAttractions = [];
      }
      updatePreviewCard();
      fetchDestinationStays(State.dest);
      fetchInterCityTransit();
      saveStateToLS();
      // fetch weather live
      showWeatherLoading();
      const w = await fetchWeather(State.dest.split(',')[0]);
      showWeatherResult(w);
    });
  }

  // Source / Destination / Travelers / budget live update
  ['w_source', 'w_dest', 'w_travelers', 'w_budget_range'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', () => {
      if (id === 'w_source') State.source = el.value.trim();
      if (id === 'w_dest') {
        const newDest = el.value.trim();
        const changed = (State.dest || '').toLowerCase().trim() !== newDest.toLowerCase().trim();
        State.dest = newDest;
        if (changed) {
          const coords = resolveDestinationCoords(newDest);
          State.destLat = coords.lat;
          State.destLon = coords.lon;
          State.selectedStay = null;
          State.liveAttractions = [];
          State.selectedAttractions = [];
          State.loadedAttractionsDest = '';
          cachedAttractionsDest = '';
          cachedInstantAttractions = [];
          fetchDestinationStays(State.dest);
        }
      }
      if (id === 'w_travelers') State.travelers = parseInt(el.value);
      if (id === 'w_budget_range') State.budget = parseInt(el.value);
      updatePreviewCard();
      fetchInterCityTransit();
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

/* ── Preview card with Live Budget Dial & Cost Meter ──────────────── */
function updatePreviewCard() {
  const trav = Math.max(1, State.travelers || 1);
  const nights = Math.max(1, (State.days || 1) - 1);

  setText('pc_dest',      State.dest      || '—');
  setText('pc_from',      'From: ' + (State.source || '—'));
  setText('pc_days',      State.days + ' Day' + (State.days>1?'s':''));
  setText('pc_travelers', State.travelers + ' Traveler' + (State.travelers>1?'s':''));
  setText('pc_budget',    fmtINR(State.budget || 15000) + ' / person');
  setText('pc_transport', State.transitDetails?.mode_title || (State.transport.charAt(0).toUpperCase() + State.transport.slice(1)));
  setText('pc_style',     State.style);
  if (State.dest) setText('dest-name-title', State.dest.split(',')[0]);

  // 1. Base Camp Stay Cost (Per Person Share)
  let stayCostTotal = 0;
  let stayCostPerPerson = 0;
  if (State.selectedStay) {
    stayCostTotal = (State.selectedStay.price_per_night || 0) * nights;
    stayCostPerPerson = Math.round(stayCostTotal / trav);
    setText('pc_stay_name', `${State.selectedStay.name} (${nights}n)`);
    setText('pc_stay_cost', fmtINR(stayCostPerPerson) + ' / person');
  } else {
    setText('pc_stay_name', 'Pick a stay in Stage 1');
    setText('pc_stay_cost', '₹0 / person');
  }

  // 2. Inter-City Transit Cost (Per Person Share / Ticket)
  let transitCostPerPerson = 0;
  if (State.transitCostPerPerson && State.transitCostPerPerson > 0) {
    transitCostPerPerson = State.transitCostPerPerson;
  } else if (State.transitCost && State.transitCost > 0) {
    transitCostPerPerson = Math.round(State.transitCost / trav);
  } else {
    const fuel = State.routeData?.fuelCost || (State.transport === 'bike' ? 1200 : 3500);
    transitCostPerPerson = Math.round(fuel / trav);
  }
  setText('pc_transit_name', `${State.transitDetails?.mode_title || State.transport}`);
  setText('pc_transit_cost', fmtINR(transitCostPerPerson) + ' / person');

  // 3. Sightseeing Entry Fees (Per Person)
  const sightseeingCostPerPerson = (State.selectedAttractions || []).reduce((s, a) => s + (a.fee || 0), 0);

  // 4. Food & Daily Dining Buffer (Per Person)
  const foodCostPerPerson = (State.days || 1) * 600;

  // 5. Total Spent for 1 Person & Live Budget Dial
  const singlePersonSpent = stayCostPerPerson + transitCostPerPerson + sightseeingCostPerPerson + foodCostPerPerson;
  const singlePersonBudget = State.budget || 15000;
  const pct = Math.min(100, Math.round((singlePersonSpent / singlePersonBudget) * 100));
  const remaining = singlePersonBudget - singlePersonSpent;

  setText('pc_total_spent', fmtINR(singlePersonSpent) + ' / person');
  setText('pc_pocket_left', (remaining >= 0 ? fmtINR(remaining) : `-${fmtINR(Math.abs(remaining))}`) + ' / person');
  setText('pc_budget_percent', `${pct}%`);

  const bar = document.getElementById('pc_budget_bar');
  if (bar) {
    bar.style.width = `${pct}%`;
    bar.className = 'progress-bar transition-all ' + (pct > 95 ? 'bg-danger' : pct > 75 ? 'bg-warning' : 'bg-success');
  }

  const statusBadge = document.getElementById('pc_budget_status');
  if (statusBadge) {
    if (remaining < 0) {
      statusBadge.className = 'badge bg-danger text-white fw-bold';
      statusBadge.textContent = '🔴 Exceeds Budget';
    } else if (pct > 75) {
      statusBadge.className = 'badge bg-warning text-dark fw-bold';
      statusBadge.textContent = '🟡 Near Limit';
    } else {
      statusBadge.className = 'badge bg-success text-white fw-bold';
      statusBadge.textContent = '🟢 On Track';
    }
  }
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
const STEP_LABELS = ['','Base Camp Stay','Door-to-Door Transit','Select Sights','Daily Schedule','Trip Overview'];

const STEP_MAP = {
  1: 1, // wstep-1 Base Camp Stays
  2: 2, // wstep-2 Door-to-Door Transit Hub
  3: 3, // wstep-3 Select Sights
  4: 4, // wstep-4 Daily Schedule
  5: 5  // wstep-5 Trip Overview
};

function resolveDestinationCoords(name) {
  const q = (name || '').toLowerCase().trim();
  const MAP = {
    // Karnataka
    'coorg': { lat: 12.4244, lon: 75.7382 },
    'madikeri': { lat: 12.4244, lon: 75.7382 },
    'kodagu': { lat: 12.4244, lon: 75.7382 },
    'chikmagalur': { lat: 13.3161, lon: 75.7720 },
    'chikkamagaluru': { lat: 13.3161, lon: 75.7720 },
    'samse': { lat: 13.2389, lon: 75.3856 },
    'kalasa': { lat: 13.2389, lon: 75.3856 },
    'kudremukh': { lat: 13.2167, lon: 75.2500 },
    'kudremukha': { lat: 13.2167, lon: 75.2500 },
    'hampi': { lat: 15.3350, lon: 76.4600 },
    'gokarna': { lat: 14.5479, lon: 74.3188 },
    'mysore': { lat: 12.2958, lon: 76.6394 },
    'mysuru': { lat: 12.2958, lon: 76.6394 },
    'bengaluru': { lat: 12.9716, lon: 77.5946 },
    'bangalore': { lat: 12.9716, lon: 77.5946 },
    'sakleshpur': { lat: 12.9440, lon: 75.7865 },
    'dandeli': { lat: 15.2415, lon: 74.6223 },
    'badami': { lat: 15.9189, lon: 75.6766 },
    'pattadakal': { lat: 15.9483, lon: 75.8160 },
    'bandipur': { lat: 11.6664, lon: 76.6291 },
    'kabini': { lat: 11.9324, lon: 76.2730 },
    'udupi': { lat: 13.3409, lon: 74.7421 },
    'mangalore': { lat: 12.9141, lon: 74.8560 },

    // Kerala
    'munnar': { lat: 10.0889, lon: 77.0595 },
    'alleppey': { lat: 9.4981, lon: 76.3388 },
    'alappuzha': { lat: 9.4981, lon: 76.3388 },
    'wayanad': { lat: 11.6854, lon: 76.1320 },
    'varkala': { lat: 8.7379, lon: 76.7163 },
    'kochi': { lat: 9.9312, lon: 76.2673 },
    'cochin': { lat: 9.9312, lon: 76.2673 },
    'thekkady': { lat: 9.6031, lon: 77.1615 },
    'periyar': { lat: 9.6031, lon: 77.1615 },
    'kovalam': { lat: 8.4004, lon: 76.9787 },
    'kumarakom': { lat: 9.6175, lon: 76.4301 },

    // Goa
    'goa': { lat: 15.2993, lon: 74.1240 },
    'panaji': { lat: 15.4909, lon: 73.8278 },
    'north goa': { lat: 15.5494, lon: 73.7535 },
    'south goa': { lat: 15.2048, lon: 73.9856 },

    // Tamil Nadu
    'ooty': { lat: 11.4102, lon: 76.6950 },
    'udhagamandalam': { lat: 11.4102, lon: 76.6950 },
    'kodaikanal': { lat: 10.2381, lon: 77.4892 },
    'pondicherry': { lat: 11.9416, lon: 79.8083 },
    'puducherry': { lat: 11.9416, lon: 79.8083 },
    'madurai': { lat: 9.9252, lon: 78.1198 },
    'rameshwaram': { lat: 9.2876, lon: 79.3129 },
    'mahabalipuram': { lat: 12.6269, lon: 80.1927 },
    'chennai': { lat: 13.0827, lon: 80.2707 },
    'kanyakumari': { lat: 8.0883, lon: 77.5385 },

    // Himachal Pradesh & Jammu/Kashmir
    'manali': { lat: 32.2396, lon: 77.1887 },
    'shimla': { lat: 31.1048, lon: 77.1734 },
    'dharamshala': { lat: 32.2190, lon: 76.3234 },
    'mcleod ganj': { lat: 32.2426, lon: 76.3213 },
    'kasol': { lat: 32.0100, lon: 77.3150 },
    'spiti valley': { lat: 32.2461, lon: 78.0349 },
    'spiti': { lat: 32.2461, lon: 78.0349 },
    'dalhousie': { lat: 32.5387, lon: 75.9710 },
    'khajjiar': { lat: 32.5510, lon: 76.0610 },
    'kullu': { lat: 31.9579, lon: 77.1095 },
    'leh': { lat: 34.1526, lon: 77.5771 },
    'ladakh': { lat: 34.1526, lon: 77.5771 },
    'srinagar': { lat: 34.0837, lon: 74.7973 },
    'gulmarg': { lat: 34.0484, lon: 74.3805 },

    // Uttarakhand
    'rishikesh': { lat: 30.0869, lon: 78.2676 },
    'mussoorie': { lat: 30.4598, lon: 78.0644 },
    'nainital': { lat: 29.3919, lon: 79.4542 },
    'haridwar': { lat: 29.9457, lon: 78.1642 },
    'jim corbett': { lat: 29.5300, lon: 78.7747 },
    'corbett': { lat: 29.5300, lon: 78.7747 },
    'auli': { lat: 30.5310, lon: 79.5694 },
    'dehradun': { lat: 30.3165, lon: 78.0322 },

    // Rajasthan & Central
    'jaipur': { lat: 26.9124, lon: 75.7873 },
    'udaipur': { lat: 24.5854, lon: 73.7125 },
    'jodhpur': { lat: 26.2389, lon: 73.0243 },
    'jaisalmer': { lat: 26.9157, lon: 70.9083 },
    'pushkar': { lat: 26.4899, lon: 74.5511 },
    'ranthambore': { lat: 26.0173, lon: 76.5026 },
    'mount abu': { lat: 24.5925, lon: 72.7156 },
    'pachmarhi': { lat: 22.4674, lon: 78.4346 },
    'khajuraho': { lat: 24.8318, lon: 79.9199 },

    // Maharashtra
    'mumbai': { lat: 19.0760, lon: 72.8777 },
    'pune': { lat: 18.5204, lon: 73.8567 },
    'lonavala': { lat: 18.7557, lon: 73.4091 },
    'mahabaleshwar': { lat: 17.9237, lon: 73.6586 },
    'panchgani': { lat: 17.9237, lon: 73.8016 },
    'alibaug': { lat: 18.6414, lon: 72.8722 },

    // North & East
    'delhi': { lat: 28.7041, lon: 77.1025 },
    'new delhi': { lat: 28.6139, lon: 77.2090 },
    'agra': { lat: 27.1767, lon: 78.0081 },
    'varanasi': { lat: 25.3176, lon: 82.9739 },
    'amritsar': { lat: 31.6340, lon: 74.8723 },
    'darjeeling': { lat: 27.0410, lon: 88.2663 },
    'gangtok': { lat: 27.3389, lon: 88.6065 },
    'shillong': { lat: 25.5788, lon: 91.8933 },
    'puri': { lat: 19.8135, lon: 85.8312 },
    'kolkata': { lat: 22.5726, lon: 88.3639 },
    'kaza': { lat: 32.2244, lon: 78.0723 },
    'tawang': { lat: 27.5861, lon: 91.8594 },
    'bhuj': { lat: 23.2420, lon: 69.6669 },
    'aurangabad': { lat: 19.8762, lon: 75.3433 }
  };

  // 1. Exact match
  if (MAP[q]) return MAP[q];

  // 2. Key contained in query (sort by longest key first)
  const sortedKeys = Object.keys(MAP).sort((a, b) => b.length - a.length);
  for (const k of sortedKeys) {
    if (q.includes(k)) return MAP[k];
  }

  // 3. Query contained in key (only if query is descriptive enough)
  if (q.length >= 4) {
    for (const k of sortedKeys) {
      if (k.includes(q)) return MAP[k];
    }
  }

  // 4. Try window.INDIAN_DESTINATIONS
  if (window.INDIAN_DESTINATIONS && Array.isArray(window.INDIAN_DESTINATIONS)) {
    const found = window.INDIAN_DESTINATIONS.find(d => 
      (d.cleanName && d.cleanName.toLowerCase() === q) ||
      (d.name && d.name.toLowerCase() === q) ||
      (d.cleanName && d.cleanName.toLowerCase().includes(q)) ||
      (d.name && d.name.toLowerCase().includes(q))
    );
    if (found && found.lat && found.lon) return { lat: found.lat, lon: found.lon };
  }

  // 5. Try selectedStay if available
  if (State.selectedStay && State.selectedStay.lat && State.selectedStay.lon) {
    return { lat: parseFloat(State.selectedStay.lat), lon: parseFloat(State.selectedStay.lon) };
  }

  return { lat: 12.4244, lon: 75.7382 };
}

const DEST_TRIVIA = {
  coorg: {
    facts: [
      "🌿 Coorg is known as the 'Scotland of India' for its misty green hills, cool climate, and sprawling coffee plantations.",
      "☕ Coorg produces nearly 40% of India's coffee, predominantly high-grade Arabica and Robusta beans.",
      "🌊 Abbey Falls drops 70 feet over rugged granite into Kaveri river tributaries amidst spice estates.",
      "🐅 Coorg's Nagarhole National Park holds one of the highest densities of Bengal tigers and wild Asian elephants.",
      "🏰 Madikeri Fort was originally built of mud by King Muddu Raja in the 17th century and later rebuilt by Tipu Sultan."
    ],
    quiz: {
      question: "What unique brew is Coorg most celebrated for worldwide?",
      options: ["Darjeeling White Tea", "Shade-Grown Arabica Coffee", "Kashmiri Kahwa", "Assam CTC Tea"],
      correct: 1,
      explanation: "🎉 Spot on! Coorg is celebrated worldwide for its organic, shade-grown Arabica and Robusta coffee!"
    }
  },
  chikmagalur: {
    facts: [
      "☕ Chikmagalur is the birthplace of Indian coffee — Sufi saint Baba Budan smuggled 7 raw beans from Yemen in 1670.",
      "🏔️ Mullayanagiri in Chikmagalur is the highest mountain peak in Karnataka at 1,930 meters (6,330 ft).",
      "🌿 The rare Neelakurinji flower blooms across the hills of Chikmagalur once every 12 years!",
      "🛕 The nearby UNESCO Hoysala temples of Belur & Halebidu feature stone carvings so fine they look carved from ivory.",
      "🌊 Hebbe Falls plunges in two stages from a height of 551 ft inside an emerald coffee sanctuary."
    ],
    quiz: {
      question: "Which saint first planted coffee beans in the hills of Chikmagalur in 1670?",
      options: ["Adi Shankaracharya", "Baba Budan", "Swami Vivekananda", "Basaveshwara"],
      correct: 1,
      explanation: "🎉 Exactly! Baba Budan planted seven magical beans on the slopes now named Baba Budan Giri!"
    }
  },
  default: {
    facts: [
      "🗺️ India has over 42 UNESCO World Heritage Sites and 106 National Parks spanning coastlines to Himalayan glaciers.",
      "🚂 Indian Railways operates 13,000+ passenger trains daily connecting the farthest corners of the subcontinent.",
      "🏨 Yatrika's stay-first algorithm anchors your daily sightseeing within optimal short-distance road loops.",
      "☕ Traditional Indian highway journeys are famous for clay-cup ('kulhad') chai and local regional breakfast spreads.",
      "🌿 Every verified base camp stay is vetted for traveler safety, host reviews, and local emergency connectivity."
    ],
    quiz: {
      question: "What is the best way to explore regional Indian culture?",
      options: ["Staying in verified local homestays", "Rushing through 10 cities in 2 days", "Staying only at the airport", "Avoiding all local food"],
      correct: 0,
      explanation: "🎉 Absolutely! Staying with verified local hosts unlocks authentic meals, hidden trails, and genuine memories!"
    }
  }
};

let activeFactIndex = 0;
let currentTriviaData = null;
let cachedAttractionsDest = '';
let cachedInstantAttractions = [];

function cycleDiscoveryFact() {
  if (!currentTriviaData || !currentTriviaData.facts.length) return;
  activeFactIndex = (activeFactIndex + 1) % currentTriviaData.facts.length;
  const el = document.getElementById('discoveryFactText');
  if (el) {
    el.style.opacity = '0';
    setTimeout(() => {
      el.textContent = currentTriviaData.facts[activeFactIndex];
      el.style.opacity = '1';
    }, 180);
  }
}

function answerDiscoveryQuiz(selectedIndex, correctIndex, explanation) {
  const container = document.getElementById('quizOptions');
  const feedback = document.getElementById('quizFeedback');
  if (!container || !feedback) return;

  const buttons = container.querySelectorAll('.quiz-option-btn');
  buttons.forEach((btn, idx) => {
    btn.disabled = true;
    if (idx === correctIndex) {
      btn.classList.add('correct');
    } else if (idx === selectedIndex) {
      btn.style.borderColor = '#EF4444';
      btn.style.color = '#EF4444';
      btn.style.background = '#FEF2F2';
    }
  });

  feedback.textContent = explanation;
  feedback.classList.remove('d-none');
}

function forceShowAttractions() {
  const dName = (State.dest || 'Coorg').split(',')[0].trim();
  if (cachedAttractionsDest === dName && cachedInstantAttractions && cachedInstantAttractions.length > 0) {
    State.loadedAttractionsDest = dName;
    State.liveAttractions = cachedInstantAttractions;
    renderAttractionGrid(cachedInstantAttractions);
    renderMap();
  } else {
    showToast('⚡ Loading verified attractions...', 'info');
    loadStep2();
  }
}

function renderDiscoveryHub(destName) {
  const clean = (destName || 'Coorg').split(',')[0].trim().toLowerCase();
  currentTriviaData = DEST_TRIVIA[clean] || (clean.includes('coorg') ? DEST_TRIVIA.coorg : clean.includes('chik') ? DEST_TRIVIA.chikmagalur : DEST_TRIVIA.default);
  activeFactIndex = 0;

  return `
    <div class="discovery-hub-card" id="discoveryHubCard">
      <div class="discovery-radar-box">
        <div class="discovery-radar-circle">🛰️</div>
        <div>
          <div class="discovery-title">Discovering Attractions Near ${escapeHTML((destName || 'Coorg').split(',')[0])}...</div>
          <div class="discovery-subtitle">Scanning 80 km radius around Base Camp · Resolving scenic loops &amp; heritage sites</div>
        </div>
      </div>

      <!-- Interactive Trivia & Fun Facts Game -->
      <div class="discovery-game-card">
        <div class="discovery-fact-header">
          <span class="discovery-fact-title"><i class="bi bi-lightbulb-fill"></i> While We Discover... Did You Know?</span>
          <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" style="font-size:.74rem" onclick="cycleDiscoveryFact()">
            <i class="bi bi-shuffle me-1"></i> Next Fact
          </button>
        </div>
        <div class="discovery-fact-text" id="discoveryFactText" style="transition: opacity 0.2s ease;">
          ${currentTriviaData.facts[0]}
        </div>

        <!-- Interactive Mini Quiz -->
        <div class="discovery-quiz-title"><i class="bi bi-question-circle-fill text-turquoise me-1"></i> Quick Quiz: ${escapeHTML(currentTriviaData.quiz.question)}</div>
        <div class="discovery-quiz-options" id="quizOptions">
          ${currentTriviaData.quiz.options.map((opt, idx) => `
            <button type="button" class="quiz-option-btn" onclick="answerDiscoveryQuiz(${idx}, ${currentTriviaData.quiz.correct}, '${escapeHTML(currentTriviaData.quiz.explanation)}')">
              ${escapeHTML(opt)}
            </button>
          `).join('')}
        </div>
        <div class="quiz-feedback-text d-none" id="quizFeedback"></div>
      </div>

      <!-- Scanning Agent Milestones -->
      <div class="discovery-milestones">
        <div class="dm-step done"><i class="bi bi-check-circle-fill text-success"></i> 1. Base Camp Stay Linked</div>
        <div class="dm-step done"><i class="bi bi-check-circle-fill text-success"></i> 2. Geospatial Anchor Set</div>
        <div class="dm-step scanning"><span class="spinner-border spinner-border-sm text-turquoise"></span> 3. Scanning 10,025 Spots</div>
        <div class="dm-step"><i class="bi bi-circle text-muted"></i> 4. Calculating Road Transit</div>
      </div>

      <!-- Quick Instant Load CTA -->
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 pt-2">
        <span class="extra-small text-muted"><i class="bi bi-shield-check text-success me-1"></i> Verified by Yatrika Geospatial Agent</span>
        <button type="button" class="btn-instant-skip" onclick="forceShowAttractions()">
          <i class="bi bi-lightning-charge-fill"></i> Show Verified Attractions Now
        </button>
      </div>
    </div>
  `;
}

async function goToStep(logicalStep) {
  let stepNum = logicalStep;
  if (stepNum > 5) {
    stepNum = 5;
  }

  // Ensure coordinates
  if (!State.destLat || !State.destLon) {
    const dName = (State.dest || 'Coorg').split(',')[0].trim();
    const coords = resolveDestinationCoords(dName);
    State.dest = dName;
    State.destLat = coords.lat;
    State.destLon = coords.lon;
  }

  // Hide all steps, show target step
  for (let s = 1; s <= 5; s++) {
    const el = document.getElementById('wstep-' + s);
    if (el) {
      if (s === stepNum) el.classList.remove('d-none');
      else el.classList.add('d-none');
    }
  }

  State.step = stepNum;
  updateProgressBar(stepNum);

  // Update Studio Toolbar Badge & Title
  const stgBadge = document.getElementById('studioStageBadge');
  const stgTitle = document.getElementById('studioStageTitle');
  if (stgBadge && stgTitle) {
    if (stepNum === 1) {
      stgBadge.textContent = 'STAGE 1';
      stgTitle.innerHTML = `Choose Base Camp Stay · <span id="stayDestName">${State.dest || 'Coorg'}</span>`;
    } else if (stepNum === 2) {
      stgBadge.textContent = 'STAGE 2';
      stgTitle.innerHTML = `Door-to-Door Transit · ${State.selectedStay ? 'to ' + State.selectedStay.name : 'to Base Camp'}`;
    } else if (stepNum === 3) {
      stgBadge.textContent = 'STAGE 3';
      stgTitle.innerHTML = `Select Sights · <span id="dest-name-title">${(State.dest || 'Coorg').split(',')[0]}</span>`;
    } else if (stepNum === 4) {
      stgBadge.textContent = 'STAGE 4';
      stgTitle.innerHTML = `Daily Schedule & Day Planning · ${(State.dest || 'Coorg').split(',')[0]}`;
    } else if (stepNum === 5) {
      stgBadge.textContent = 'FINALIZE';
      stgTitle.innerHTML = `Trip Overview & Booking · ${(State.dest || 'Coorg').split(',')[0]}`;
    }
  }

  if (stepNum === 1) {
    if (!State.availableStays || State.availableStays.length === 0) {
      await fetchDestinationStays(State.dest || 'Coorg');
    }
  }
  if (stepNum === 2) {
    // Stage 2: Transit
    const srcTxt = document.getElementById('transitSourceText');
    const hotelTxt = document.getElementById('transitSelectedHotelText');
    const tStayName = document.getElementById('tSummaryStayName');
    const tStayCost = document.getElementById('tSummaryStayCost');

    if (srcTxt) srcTxt.textContent = State.source || 'Bengaluru';
    if (hotelTxt) hotelTxt.textContent = State.selectedStay ? State.selectedStay.name : 'Your Base Camp';
    if (tStayName && State.selectedStay) tStayName.textContent = State.selectedStay.name;
    if (tStayCost && State.selectedStay) {
      const nights = Math.max(1, (State.days || 3) - 1);
      tStayCost.textContent = `₹${(State.selectedStay.price_per_night * nights).toLocaleString('en-IN')} total stay`;
    }
    await fetchInterCityTransit();
  }
  if (stepNum === 3) {
    // Stage 3: Select Sights (Card grid + selected list)
    const title = document.getElementById('dest-name-title');
    const currentDest = (State.dest || 'Coorg').split(',')[0].trim();
    if (title) title.textContent = currentDest;
    if (!State.liveAttractions || State.liveAttractions.length === 0 || State.loadedAttractionsDest !== currentDest) {
      await loadStep2();
    } else {
      renderAttractionGrid(State.liveAttractions);
      renderMap();
    }
    updateSidebar();
  }
  if (stepNum === 4) {
    // Stage 4: Daily Schedule & Interactive Route Map
    const sel = State.selectedAttractions || [];
    const totalDist = sel.reduce((s, a) => s + (a.dist || 0), 0);
    const s4StayName = document.getElementById('s4StayName');
    const s4SightsCount = document.getElementById('s4SightsCount');
    const s4TotalDrive = document.getElementById('s4TotalDrive');
    const stage4DayCountBadge = document.getElementById('stage4DayCountBadge');

    if (s4StayName) s4StayName.textContent = State.selectedStay ? State.selectedStay.name : (State.dest || 'Base Camp');
    if (s4SightsCount) s4SightsCount.textContent = `${sel.length} Sight${sel.length === 1 ? '' : 's'} Selected`;
    if (!State.activeTimelineDay || State.activeTimelineDay < 1) State.activeTimelineDay = 1;
    if (stage4DayCountBadge) stage4DayCountBadge.textContent = `Day ${State.activeTimelineDay} of ${State.days || 3}`;

    renderTimeline();

    // Initialize and resize interactive route map alongside daily schedule
    setTimeout(() => {
      renderMap();
      if (State.mapInstance) {
        State.mapInstance.resize();
        updateMapMarkersAndRoutes(State.mapInstance);
      }
    }, 150);
  }
  if (stepNum === 5) {
    // Stage 5: Overview
    renderOverview();
  }
}

function updateProgressBar(n) {
  const fill = document.getElementById('progressFill');
  if (fill) fill.style.width = ((n / 5) * 100) + '%';
  document.querySelectorAll('.progress-step').forEach(s => {
    const sn = +s.dataset.step;
    s.classList.remove('active', 'done');
    if (sn === n) s.classList.add('active');
    else if (sn < n) s.classList.add('done');
  });
  ['conn-1', 'conn-2', 'conn-3', 'conn-4'].forEach((id, idx) => {
    const conn = document.getElementById(id);
    if (conn) conn.classList.toggle('done', (idx + 1) < n);
  });
}

/* ── STEP 2 — Load real attractions from Verified 10,025 Database + Overpass ── */
async function loadStep2() {
  const grid  = document.getElementById('attractionGrid');
  const title = document.getElementById('dest-name-title');
  const dName = (State.dest || 'Coorg').split(',')[0].trim();
  if (title) title.textContent = dName;
  if (!grid) return;

  // Ensure coordinates belong to this destination
  if (!State.destLat || !State.destLon || State.loadedAttractionsDest !== dName) {
    const coords = resolveDestinationCoords(dName);
    State.destLat = coords.lat;
    State.destLon = coords.lon;
  }
  // If base camp stay matches dName and has valid coordinates, prefer the base camp anchor
  if (State.selectedStay && State.selectedStay.lat && State.selectedStay.lon) {
    State.destLat = parseFloat(State.selectedStay.lat);
    State.destLon = parseFloat(State.selectedStay.lon);
  }

  // Only use cached attractions IF they were actually loaded for THIS destination
  if (State.loadedAttractionsDest === dName && State.liveAttractions && State.liveAttractions.length > 0) {
    renderAttractionGrid(State.liveAttractions);
    renderMap();
    return;
  }
  if (cachedAttractionsDest === dName && cachedInstantAttractions && cachedInstantAttractions.length > 0) {
    State.loadedAttractionsDest = dName;
    State.liveAttractions = cachedInstantAttractions;
    renderAttractionGrid(cachedInstantAttractions);
    renderMap();
    return;
  }

  State.selectedAttractions = [];
  State.liveAttractions     = [];
  updateSidebar();

  // There IS real loading time now! Mount 3D Orbit Runner: Person running around the globe scouting places
  grid.innerHTML = `
    <div id="wizardPlanetRunnerContainer" class="mb-3" style="grid-column: 1 / -1; width: 100%; min-height: 280px;"></div>
    <div class="text-center py-2 text-muted" style="grid-column: 1 / -1; font-size: 0.85rem;">
      <i class="bi bi-compass text-turquoise me-1"></i> Autonomous Scout is exploring ${dName} — scouting landmarks &amp; verified sights within 80km...
    </div>
  `;

  let scoutRunner = null;
  const runnerBox = document.getElementById('wizardPlanetRunnerContainer');
  if (runnerBox && window.PlanetRunner) {
    try {
      scoutRunner = window.PlanetRunner.mount(runnerBox, {
        destination: dName,
        attractions: [
          { name: `${dName} Scenic Viewpoint & Peaks`, category: "Must-Visit", icon: "🌟" },
          { name: "Historic Heritage Monument", category: "Culture", icon: "🏛️" },
          { name: "Lush Botanical Gardens & Cascades", category: "Nature", icon: "🌿" },
          { name: "Valley Viewpoint & Tea Estates", category: "Viewpoint", icon: "🌅" },
          { name: "Traditional Markets & Local Flavors", category: "Gastronomy", icon: "☕" },
          { name: "Ancient Temple Sanctuary", category: "Spiritual", icon: "🛕" }
        ]
      });
    } catch (e) {
      console.warn("PlanetRunner mount error:", e);
    }
  }

  // Fetch verified attractions (80 km radius) AND Overpass in parallel (Real network loading)
  const verifiedPromise = fetch(`/planner/api/attractions/search?destination=${encodeURIComponent(dName)}&lat=${State.destLat}&lon=${State.destLon}&radius_km=80`)
    .then(r => r.ok ? r.json() : [])
    .catch(() => []);

  const overpassPromise = fetchAttractions(State.destLat, State.destLon)
    .catch(() => []);

  // Wait only for actual network responses (no artificial delay!)
  const [vList, oList] = await Promise.all([
    verifiedPromise,
    Promise.race([
      overpassPromise,
      new Promise(res => setTimeout(() => res([]), 3500))
    ])
  ]);

  // 5. Merge verified + overpass unique items
  let merged = [];
  const seen = new Set();
  
  (vList || []).forEach(a => {
    if (isGenericPlaceholderName(a.name) || isMinorReligiousPlace(a.tags || {}, a.name)) return;
    const k = a.name.toLowerCase().trim();
    if (!seen.has(k)) {
      seen.add(k);
      merged.push(a);
    }
  });

  (oList || []).forEach(a => {
    if (isGenericPlaceholderName(a.name) || isMinorReligiousPlace(a.tags || {}, a.name)) return;
    const k = a.name.toLowerCase().trim();
    if (!seen.has(k)) {
      seen.add(k);
      merged.push(a);
    }
  });

  if (!merged.length && cachedAttractionsDest === dName && cachedInstantAttractions && cachedInstantAttractions.length) {
    merged = cachedInstantAttractions;
  }

  State.loadedAttractionsDest = dName;
  cachedAttractionsDest = dName;
  State.liveAttractions = merged;
  cachedInstantAttractions = merged;

  // Safely cleanup 3D runner and render full attractions cards
  if (scoutRunner && typeof scoutRunner.destroy === 'function') {
    try { scoutRunner.destroy(); } catch (_) {}
  }

  renderAttractionGrid(merged);
  renderMap();
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

  // Stay-First anchor distance calculation
  let distanceHtml = `<div class="ac-meta-item"><i class="bi bi-geo-alt me-1"></i>${a.dist} km away</div>`;
  if (State.selectedStay && State.selectedStay.lat && a.lat) {
    const dStay = haversineKm(State.selectedStay.lat, State.selectedStay.lon, a.lat, a.lon);
    const driveM = Math.max(5, Math.round(dStay * 2.2));
    const stayShort = State.selectedStay.name.split(' ')[0];
    distanceHtml = `<div class="ac-meta-item stay-distance-badge" style="color:#059669; font-weight:600;" title="Distance from Base Camp (${State.selectedStay.name})"><i class="bi bi-geo-alt-fill me-1"></i>${dStay.toFixed(1)} km from ${stayShort} (~${driveM}m)</div>`;
  }

  // Safe image fallback
  const cardImg = (a.img && a.img.trim()) ? a.img : 'https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=600&q=80';

  return `
  <div class="attraction-card ${sel?'selected':''}" data-id="${a.id}">
    <div class="ac-image" style="background-image:url('${cardImg}');background-color:#e5e7eb">
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
        ${distanceHtml}
        <div class="ac-meta-item"><i class="bi bi-people me-1"></i>${a.difficulty}</div>
        ${a.opening !== 'Check locally' ? `<div class="ac-meta-item"><i class="bi bi-door-open me-1"></i>${a.opening}</div>` : ''}
      </div>
      <div class="d-flex gap-2 mt-2">
        <button class="btn btn-sm btn-outline-primary flex-grow-1" onclick="openDrawer('${a.id}'); event.stopPropagation();" style="font-size:0.75rem;"><i class="bi bi-info-circle"></i> Details</button>
        <button class="btn btn-sm ${sel ? 'btn-success' : 'btn-primary'} select-btn-explore" onclick="toggleSelection('${a.id}'); event.stopPropagation();" style="width: 85px; font-size:0.75rem; font-weight:600;">
          ${sel ? '✓ Added' : '+ Add'}
        </button>
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
  updatePreviewCard();
  const card = document.querySelector(`.attraction-card[data-id="${id}"]`);
  if (card) {
    const added = idx === -1;
    card.classList.toggle('selected', added);
    const ind = card.querySelector('.ac-select-indicator');
    if (ind) ind.style.display = added ? 'flex' : 'none';
    const favBtn = card.querySelector('.ac-fav-btn');
    if (favBtn) favBtn.style.display = added ? 'none' : '';
    
    const selectBtn = card.querySelector('.select-btn-explore');
    if (selectBtn) {
      selectBtn.className = `btn btn-sm ${added ? 'btn-success' : 'btn-primary'} select-btn-explore`;
      selectBtn.textContent = added ? '✓ Added' : '+ Add';
    }
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
  let filtered = State.liveAttractions || [];
  if (f !== 'all') {
    filtered = filtered.filter(a => {
      const hasTag = Array.isArray(a.tags) && a.tags.some(t => String(t).toLowerCase().includes(f));
      const hasCat = a.cat && a.cat.toLowerCase().includes(f);
      return hasTag || hasCat;
    });
  }
  if (q) {
    filtered = filtered.filter(a => (a.name && a.name.toLowerCase().includes(q)) || (a.cat && a.cat.toLowerCase().includes(q)));
  }
  renderAttractionGrid(filtered);
  if (State.mapInstance) updateMapMarkersAndRoutes(State.mapInstance);
}
function removeFromSelection(id) {
  const idx = State.selectedAttractions.findIndex(x => x.id === id);
  if (idx > -1) State.selectedAttractions.splice(idx, 1);
  updateSidebar();
  const card = document.querySelector(`.attraction-card[data-id="${id}"]`);
  if (card) {
    card.classList.remove('selected');
    const ind = card.querySelector('.ac-select-indicator');
    if (ind) ind.style.display = 'none';
    const fb = card.querySelector('.ac-fav-btn');
    if (fb) fb.style.display = '';
    const selectBtn = card.querySelector('.select-btn-explore');
    if (selectBtn) {
      selectBtn.className = 'btn btn-sm btn-primary select-btn-explore';
      selectBtn.textContent = '+ Add';
    }
  }
}
function updateSidebar() {
  const sel = State.selectedAttractions || [];
  setText('selectedCount', sel.length + (sel.length === 1 ? ' Sight' : ' Sights'));
  const totalMins = sel.reduce((s, a) => s + (a.dur || 0), 0);
  const totalDist = sel.reduce((s, a) => s + (a.dist || 0), 0);
  const budgetEst = sel.reduce((s, a) => s + (a.fee || 0), 0) + totalDist * 4 + totalMins * 20;
  const avail     = (State.days * 8 * 60) - totalMins;
  setText('totalDuration', fmtHrs(totalMins));
  setText('totalDistance', totalDist.toFixed(1) + ' km');
  setText('estBudget', fmtINR(budgetEst));
  setText('timeLeft', avail > 0 ? fmtHrs(avail) : 'Full!');

  // Render ONLY the places the user has actually selected
  renderSelectedSightsList();

  if (State.mapInstance) {
    updateMapMarkersAndRoutes(State.mapInstance);
  }
}

function renderSelectedSightsList() {
  const sel = State.selectedAttractions || [];
  const cont = document.getElementById('selectedSightsContainer');
  const clearBtn = document.getElementById('btnClearAllSights');
  if (clearBtn) clearBtn.style.display = sel.length > 0 ? 'inline-block' : 'none';

  if (!cont) return;

  if (!sel.length) {
    cont.innerHTML = `
      <div class="text-center py-5 text-muted">
        <div style="font-size:2.4rem; margin-bottom:8px;">📍</div>
        <div class="fw-bold text-navy small mb-1">No sights selected yet</div>
        <div class="extra-small text-muted px-3">Tap any place on the map or click <strong>+ Add Sight</strong> to choose the places you want to visit.</div>
      </div>
    `;
    return;
  }

  const stay = State.selectedStay;
  cont.innerHTML = sel.map((a, i) => {
    let distStr = `${a.dist} km away`;
    if (stay && stay.lat && a.lat) {
      const d = haversineKm(stay.lat, stay.lon, a.lat, a.lon);
      const m = Math.max(5, Math.round(d * 2.2));
      const sName = stay.name.split(' ')[0];
      distStr = `🚗 ${d.toFixed(1)} km from ${sName} (~${m}m)`;
    }
    const cardImg = (a.img && a.img.trim()) ? a.img : 'https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=300&q=80';

    return `
      <div class="selected-sight-item d-flex align-items-center gap-2 p-2 mb-2 rounded-2 border bg-white shadow-sm" data-id="${a.id}">
        <span class="badge bg-primary rounded-circle" style="width:20px; height:20px; display:flex; align-items:center; justify-content:center; font-size:0.65rem; flex-shrink:0;">${i+1}</span>
        <div style="width:48px; height:48px; border-radius:6px; overflow:hidden; flex-shrink:0; background:#e2e8f0;">
          <img src="${cardImg}" alt="${a.name}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=300&q=80'"/>
        </div>
        <div class="flex-grow-1 overflow-hidden" style="line-height:1.2;">
          <div class="fw-bold text-navy small text-truncate" title="${a.name}">${a.name}</div>
          <div class="text-success extra-small fw-semibold mt-1 text-truncate">${distStr}</div>
          <div class="text-muted extra-small mt-1">${a.icon} ${a.cat} · ${fmtHrs(a.dur)}${a.fee > 0 ? ` · ₹${a.fee}` : ' · Free'}</div>
        </div>
        <button type="button" class="btn btn-xs btn-outline-danger border-0 p-1 rounded-circle" onclick="removeFromSelection('${a.id}'); event.stopPropagation();" title="Remove place">
          <i class="bi bi-trash3" style="font-size:0.85rem;"></i>
        </button>
      </div>
    `;
  }).join('');
}

function clearSelectedAttractions() {
  State.selectedAttractions = [];
  updateSidebar();
  document.querySelectorAll('.attraction-card.selected').forEach(c => {
    c.classList.remove('selected');
    const ind = c.querySelector('.ac-select-indicator');
    if (ind) ind.style.display = 'none';
    const btn = c.querySelector('.select-btn-explore');
    if (btn) {
      btn.className = 'btn btn-sm btn-primary select-btn-explore';
      btn.textContent = '+ Add';
    }
  });
  if (State.mapInstance) updateMapMarkersAndRoutes(State.mapInstance);
}
window.clearSelectedAttractions = clearSelectedAttractions;
window.renderSelectedSightsList = renderSelectedSightsList;

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

/* ── Helpers — Distribute attractions across trip days ── */
function getDayPlanArray() {
  const days = Math.max(1, State.days || 3);
  const sel  = State.selectedAttractions || [];
  const DAILY_MINUTES = 11 * 60;  // 660 min
  const BREAKFAST_MIN = 30;
  const LUNCH_MIN     = 60;
  const days_plan = [];

  let hasPlannerAssignments = false;
  if (State.dayPlanner) {
    for (let d = 1; d <= days; d++) {
      const dayObj = State.dayPlanner[d];
      if (dayObj) {
        ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
          if ((dayObj[zone] || []).length > 0) hasPlannerAssignments = true;
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
          const attraction = sel.find(a => a.id === act.id);
          if (attraction && !dayAttractions.includes(attraction)) {
            dayAttractions.push(attraction);
          }
        });
      });
      days_plan.push(dayAttractions);
    }
  } else {
    // Greedy distribution
    let bucket = [];
    let minutesUsed = BREAKFAST_MIN;
    sel.forEach((a) => {
      const travelMin = Math.round(a.dist / 35 * 60);
      const visitMin  = a.dur;
      const needed    = travelMin + visitMin;

      const lunchNeeded = bucket.length > 0 && minutesUsed < (DAILY_MINUTES / 2) &&
                          (minutesUsed + needed) > (DAILY_MINUTES / 2) ? LUNCH_MIN : 0;

      if (days_plan.length < days - 1 && minutesUsed + needed + lunchNeeded > DAILY_MINUTES && bucket.length > 0) {
        days_plan.push(bucket);
        bucket = [];
        minutesUsed = BREAKFAST_MIN;
      }
      bucket.push(a);
      minutesUsed += travelMin + visitMin + lunchNeeded;
    });
    if (bucket.length) days_plan.push(bucket);
    while (days_plan.length < days) days_plan.push([]);
  }
  return days_plan;
}
window.getDayPlanArray = getDayPlanArray;

/* ── STEP 5 — Smart Timeline (check-in 8:00, built from planner) ── */
function renderTimeline() {
  const sel  = State.selectedAttractions || [];
  const cont = document.getElementById('smartTimeline');
  if (!cont) return;

  const days = Math.max(1, State.days || 3);
  if (!State.activeTimelineDay || State.activeTimelineDay < 1 || State.activeTimelineDay > days) {
    State.activeTimelineDay = 1;
  }

  // Render Day Selector Tabs: ONLY Day 1, Day 2, etc. (NO "All Days")
  const ds = document.getElementById('daySelector');
  if (ds) {
    let tabs = '';
    for (let d = 1; d <= days; d++) {
      tabs += `<button type="button" class="day-btn ${State.activeTimelineDay === d ? 'active' : ''}" onclick="switchTimelineDay(${d}, this)">Day ${d}</button>`;
    }
    ds.innerHTML = tabs;
  }

  const stage4DayCountBadge = document.getElementById('stage4DayCountBadge');
  if (stage4DayCountBadge) {
    stage4DayCountBadge.textContent = `Day ${State.activeTimelineDay} of ${days}`;
  }

  if (!sel.length) {
    cont.innerHTML = `
      <div class="text-center py-4 text-muted">
        <div style="font-size:2.2rem; margin-bottom: 6px;">🗺️</div>
        <div class="fw-bold small text-navy mb-1">No attractions selected yet</div>
        <div class="extra-small text-muted">Click <strong>+ Add</strong> on any sight card on the left to add it to your daily schedule.</div>
      </div>`;
    return;
  }

  const days_plan = getDayPlanArray();

  const dayLabels = [
    'Arrival & Explore', 'Deep Exploration', 'Adventure Day',
    'Cultural Immersion', 'Leisure & Relax', 'Hidden Gems',
    'Final Day & Departure'
  ];

  // Strictly show the active selected day (Day 1, Day 2, etc.)
  const visibleDays = [];
  const activeDay = Math.max(1, Math.min(days, State.activeTimelineDay || 1));
  const dIdx = activeDay - 1;
  visibleDays.push({ d: dIdx, attrs: days_plan[dIdx] || [] });

  let hasPlannerAssignments = false;
  if (State.dayPlanner && State.dayPlanner[activeDay]) {
    ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
      if ((State.dayPlanner[activeDay][zone] || []).length > 0) hasPlannerAssignments = true;
    });
  }

  cont.innerHTML = `
    <div class="tl-days-wrap">
      ${visibleDays.map(({ attrs, d }) => `
        <div class="tl-day-col mb-2">
          <div class="tl-day-header">
            <span class="tl-day-num">Day ${d+1}</span>
            <span class="tl-day-label">${dayLabels[d] || ('Exploration Day '+(d+1))}</span>
            <span class="tl-day-count">${attrs.length} stop${attrs.length === 1 ? '' : 's'}</span>
          </div>
          <div class="tl-events">
            ${(hasPlannerAssignments ? buildPlannedDayEvents(d+1, days_plan.length) : buildSmartDayEvents(d+1, attrs, days_plan.length)).map(e => buildEventCard(e)).join('')}
          </div>
        </div>
      `).join('')}
    </div>`;
}

function switchTimelineDay(dayNum, btnEl) {
  State.activeTimelineDay = parseInt(dayNum) || 1;
  const ds = document.getElementById('daySelector');
  if (ds) {
    ds.querySelectorAll('.day-btn').forEach(b => b.classList.remove('active'));
    if (btnEl) {
      btnEl.classList.add('active');
    } else {
      const allBtns = ds.querySelectorAll('.day-btn');
      if (allBtns[State.activeTimelineDay - 1]) allBtns[State.activeTimelineDay - 1].classList.add('active');
    }
  }
  const stage4DayCountBadge = document.getElementById('stage4DayCountBadge');
  if (stage4DayCountBadge) {
    stage4DayCountBadge.textContent = `Day ${State.activeTimelineDay} of ${State.days || 3}`;
  }
  renderTimeline();
  if (State.mapInstance) {
    updateMapMarkersAndRoutes(State.mapInstance);
  }
}
window.switchTimelineDay = switchTimelineDay;

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
  if (!attrs || attrs.length === 0) {
    return [
      {
        time: '10:00',
        type: 'leisure',
        icon: '☕',
        title: 'Leisure Day & Resort Exploration',
        subtitle: `Relaxation, nature walks, and dining at ${State.selectedStay ? State.selectedStay.name : (State.dest || 'Resort')}`,
        priority: 'low',
        duration: 180
      }
    ];
  }

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
      duration: a.dur,
      attractionId: a.id
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
  const removeBtn = e.attractionId
    ? `<button type="button" class="btn btn-xs text-danger border-0 p-0 ms-auto" onclick="toggleSelection('${e.attractionId}'); event.stopPropagation();" title="Remove sight" style="background:transparent; font-size:0.85rem; line-height:1; font-weight:bold; cursor:pointer;">✕</button>`
    : '';

  return `
    <div class="tl-event tl-event-${e.type}">
      <div class="tl-event-time">${e.time}</div>
      <div class="tl-event-dot" style="background:${color}">${e.icon}</div>
      <div class="tl-event-body">
        <div class="tl-event-title d-flex align-items-center justify-content-between">
          <span class="text-truncate">${e.title}</span>
          ${removeBtn}
        </div>
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
  if (!sel.length) { grid.innerHTML=`<div class="text-center py-5 text-muted" style="grid-column:1/-1"><p>No attractions selected. <a href="#" onclick="goToStep(2)">Go back to Destination Explorer</a></p></div>`; return; }
  
  grid.innerHTML = sel.map(a => `
    <div class="dg-card" data-id="${a.id}" style="border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; background: var(--bg-card);">
      <div class="dg-image" style="background-image:url('${a.img}');background-color:#e5e7eb; height: 160px; background-size: cover; position: relative;">
        <div class="dg-overlay" style="position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(transparent, rgba(0,0,0,0.7)); padding: 8px 12px; color: white;"><div class="dg-name" style="font-weight:700; font-size:0.95rem;">${a.name}</div></div>
      </div>
      <div class="dg-body" style="padding: 12px; display: flex; flex-direction: column; gap: 8px;">
        <div class="dg-tags" style="display: flex; gap: 6px; flex-wrap: wrap;">
          <span class="dg-tag" style="background: rgba(0,98,255,0.08); color: #0062FF; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight:600;">${a.icon} ${a.cat}</span>
          <span class="dg-tag" style="background: rgba(0,0,0,0.05); padding: 2px 8px; border-radius: 4px; font-size: 0.72rem;">${a.dist} km</span>
        </div>
        <button class="btn btn-sm btn-outline-primary w-100 mt-2" onclick="openDrawer('${a.id}')" style="font-size:0.8rem;"><i class="bi bi-info-circle"></i> View Details</button>
      </div>
    </div>`).join('');
}

function openDrawer(id) {
  const a = State.selectedAttractions.find(x=>x.id===id) || State.liveAttractions.find(x=>x.id===id);
  if (!a) return;
  const isWikiReal = a.img && (a.img.includes('wikimedia.org') || a.img.includes('wikipedia.org'));
  document.getElementById('drawerContent').innerHTML = `
    <div class="drawer-hero-img" style="position:relative; width:100%; height:220px; border-radius:14px; overflow:hidden; background-color:#1e293b; box-shadow:0 8px 24px rgba(0,0,0,0.12);">
      <img src="${a.img}" alt="${a.name}" style="width:100%; height:100%; object-fit:cover; display:block;" onerror="this.src='https://images.unsplash.com/photo-1506461883276-594a12b11cf3?auto=format&fit=crop&w=600&q=80'" />
      <div style="position:absolute; inset:0; background:linear-gradient(180deg, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.7) 100%);"></div>
      <div style="position:absolute; bottom:12px; left:12px; right:12px; display:flex; justify-content:space-between; align-items:flex-end;">
        <div>
          ${isWikiReal ? `<span class="badge mb-1 d-inline-block" style="background:rgba(15,23,42,0.85); color:#38bdf8; font-size:0.72rem; border:1px solid rgba(56,189,248,0.4);"><i class="bi bi-camera-fill me-1"></i> Authentic Location Photo</span>` : ''}
          <div style="color:#fff; font-weight:800; font-size:1.1rem; line-height:1.2; text-shadow:0 2px 4px rgba(0,0,0,0.6);">${a.icon} ${a.name}</div>
        </div>
        <div style="background:rgba(15,23,42,0.88); border:1px solid rgba(251,191,36,0.3); border-radius:8px; padding:4px 8px; text-align:center;">
          <div style="color:#fbbf24; font-weight:800; font-size:0.95rem; line-height:1;">${a.rating} ★</div>
          <div style="color:#94a3b8; font-size:0.65rem; text-transform:uppercase; letter-spacing:0.5px;">Google</div>
        </div>
      </div>
    </div>
    <div class="drawer-section mt-3">
      <div style="color:var(--wizard-accent);font-weight:700;font-size:.82rem;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px">${a.cat}</div>
      <p style="color:var(--text-muted);font-size:.88rem;line-height:1.7">${a.desc}</p>
    </div>
    <div class="drawer-section">
      <h5>📋 Quick Info</h5>
      <div class="drawer-info-grid">
        <div class="di-item"><div class="di-label">⏰ Visit Duration</div><div class="di-value">${fmtHrs(a.dur)}</div></div>
        ${State.selectedStay && State.selectedStay.lat && a.lat ? `
        <div class="di-item" style="background:rgba(16,185,129,0.12); border-radius:8px; padding:6px 10px;">
          <div class="di-label" style="color:#059669; font-weight:700;">🏡 From Base Camp</div>
          <div class="di-value" style="color:#059669; font-weight:700;">${haversineKm(State.selectedStay.lat, State.selectedStay.lon, a.lat, a.lon).toFixed(1)} km (~${Math.max(5, Math.round(haversineKm(State.selectedStay.lat, State.selectedStay.lon, a.lat, a.lon) * 2.2))}m)</div>
        </div>` : `<div class="di-item"><div class="di-label">📍 Distance</div><div class="di-value">${a.dist} km</div></div>`}
        <div class="di-item"><div class="di-label">⭐ Rating</div><div class="di-value">${a.rating}/5.0</div></div>
        <div class="di-item"><div class="di-label">💪 Difficulty</div><div class="di-value">${a.difficulty}</div></div>
        <div class="di-item"><div class="di-label">🕐 Opening</div><div class="di-value">${a.opening}</div></div>
        ${a.website?`<div class="di-item"><div class="di-label">🌐 Website</div><div class="di-value"><a href="${a.website}" target="_blank" class="text-primary">Visit</a></div></div>`:''}
      </div>
    </div>
    <div class="drawer-section"><h5>💡 Travel Tips</h5>${(a.tips || ['Wear comfortable footwear and carry water.']).map(t=>`<div style="display:flex;gap:8px;margin-bottom:6px;font-size:.85rem"><span>✅</span><span>${t}</span></div>`).join('')}</div>
    <div class="drawer-section"><h5>📦 Packing Suggestions</h5><div style="display:flex;flex-wrap:wrap;gap:6px">${['Comfortable shoes','Water bottle','Sunscreen','Camera','Raincoat','Snacks'].map(p=>`<span class="dg-tag">${p}</span>`).join('')}</div></div>
    <div class="drawer-section">
      <h5>⭐ Verified Reviews & Experiences</h5>
      ${(a.review || [{author:'Google Local Guide', stars:5, text:'Authentic experience, breathtaking views and serene nature.'}]).map(r=>`
        <div class="review-card" style="margin-bottom:10px; padding:10px 12px; background:#f8fafc; border-radius:8px; border-left:3px solid #f59e0b;">
          <div class="review-author" style="font-weight:700; font-size:0.85rem; color:#1e293b; display:flex; justify-content:space-between;">
            <span>${r.author || 'Visitor'}</span>
            <span style="color:#f59e0b;">${'★'.repeat(r.stars || 5)}</span>
          </div>
          <div class="review-text" style="font-size:0.82rem; color:#475569; margin-top:4px; line-height:1.5;">${r.text || ''}</div>
        </div>
      `).join('')}
    </div>
  `;
  document.getElementById('detailDrawer').classList.add('open');
}
function closeDrawer() { document.getElementById('detailDrawer').classList.remove('open'); }
window.openDrawer = openDrawer;
window.closeDrawer = closeDrawer;

function getDayRoutePoints(d) {
  const points = [];
  
  // Anchor daily tour start at Base Camp Stay or destination center
  const anchorLat = State.selectedStay?.lat || State.destLat || State.sourceLat;
  const anchorLon = State.selectedStay?.lon || State.destLon || State.sourceLon;

  if (anchorLat && anchorLon) {
    points.push({ lat: anchorLat, lon: anchorLon, label: State.selectedStay?.name || 'Base Camp' });
  }
  
  let hasAssigned = false;
  if (State.dayPlanner && State.dayPlanner[d]) {
    const dayObj = State.dayPlanner[d];
    ['morning', 'afternoon', 'evening', 'night'].forEach(zone => {
      (dayObj[zone] || []).forEach(act => {
        if (act.id.startsWith('osm_')) {
          const attraction = State.selectedAttractions.find(a => a.id === act.id);
          if (attraction && attraction.lat && attraction.lon) {
            points.push({ lat: attraction.lat, lon: attraction.lon, label: attraction.name });
            hasAssigned = true;
          }
        }
      });
    });
  }
  
  if (!hasAssigned) {
    const dayAttrs = State.selectedAttractions.filter((_, idx) => idx % Math.max(1, State.days) === (d - 1));
    dayAttrs.forEach(a => {
      if (a.lat && a.lon) points.push({ lat: a.lat, lon: a.lon, label: a.name });
    });
  }

  // Loop back to Base Camp Stay at night
  if (anchorLat && anchorLon && points.length > 1) {
    points.push({ lat: anchorLat, lon: anchorLon, label: State.selectedStay?.name || 'Base Camp Return' });
  }
  
  return points;
}

/* ── STEP 7 — Interactive Map-First Explorer with Road Routes & Distance ──────────────── */

function setStudioViewMode(mode) {
  State.studioViewMode = mode;
  const mapWrap = document.getElementById('studioMapExplorerWrap');
  const gridWrap = document.getElementById('attractionsScrollArea');
  const btnMap = document.getElementById('btnViewMap');
  const btnGrid = document.getElementById('btnViewGrid');

  if (mode === 'grid') {
    if (mapWrap) mapWrap.classList.add('d-none');
    if (gridWrap) gridWrap.classList.remove('d-none');
    if (btnMap) btnMap.classList.remove('active');
    if (btnGrid) btnGrid.classList.add('active');
  } else {
    if (mapWrap) mapWrap.classList.remove('d-none');
    if (gridWrap) gridWrap.classList.add('d-none');
    if (btnMap) btnMap.classList.add('active');
    if (btnGrid) btnGrid.classList.remove('active');
    if (State.mapInstance) {
      setTimeout(() => { State.mapInstance.resize(); }, 150);
    } else {
      renderMap();
    }
  }
}
window.setStudioViewMode = setStudioViewMode;

function buildMapPlacePopupHtml(a, isSel, orderNum) {
  const stay = State.selectedStay;
  let distText = `${a.dist} km away`;
  let driveText = '';
  if (stay && stay.lat && a.lat) {
    const dStay = haversineKm(stay.lat, stay.lon, a.lat, a.lon);
    const driveM = Math.max(5, Math.round(dStay * 2.2));
    const stayShort = stay.name.split(' ')[0];
    distText = `🚗 ${dStay.toFixed(1)} km from ${stayShort}`;
    driveText = `~${driveM}m drive`;
  }
  const imgUrl = (a.img && a.img.trim()) ? a.img : 'https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=400&q=80';

  return `
    <div class="map-place-popup-card p-1">
      <div class="mpp-img rounded-2" style="background-image:url('${imgUrl}'); background-size:cover; background-position:center; height:100px; position:relative; overflow:hidden;">
        <div style="position:absolute; inset:0; background:linear-gradient(180deg, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.65) 100%);"></div>
        <div style="position:absolute; top:6px; left:6px;">
          <span class="badge bg-dark-subtle text-white extra-small" style="backdrop-filter:blur(4px); font-size:0.65rem;">${a.icon} ${a.cat}</span>
        </div>
        <div style="position:absolute; bottom:6px; right:6px; background:rgba(0,0,0,0.75); color:#FFB703; font-weight:800; font-size:0.68rem; padding:1px 6px; border-radius:4px;">
          ★ ${a.rating}
        </div>
        ${isSel ? `<div style="position:absolute; top:6px; right:6px; background:#10B981; color:#fff; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:0.75rem; box-shadow:0 2px 6px rgba(0,0,0,0.3);">✓</div>` : ''}
      </div>
      <div class="mpp-body pt-2 px-1">
        <div class="fw-bold text-navy small text-truncate" title="${a.name}">${isSel ? `<span class="badge bg-success me-1">#${orderNum}</span>` : ''}${a.name}</div>
        <div class="d-flex align-items-center justify-content-between mt-1 mb-2 extra-small">
          <span class="text-success fw-bold"><i class="bi bi-geo-alt-fill me-1"></i>${distText}</span>
          ${driveText ? `<span class="badge bg-body-tertiary text-dark border">${driveText}</span>` : ''}
        </div>
        <div class="d-flex gap-2">
          <button type="button" class="btn btn-xs btn-outline-secondary flex-grow-1 py-1" onclick="openDrawer('${a.id}'); event.stopPropagation();" style="font-size:0.72rem;">
            <i class="bi bi-info-circle me-1"></i>Details
          </button>
          <button type="button" class="btn btn-xs ${isSel ? 'btn-success' : 'btn-primary'} flex-grow-1 py-1 fw-bold" onclick="toggleSelection('${a.id}'); event.stopPropagation();" style="font-size:0.72rem;">
            ${isSel ? '✓ Added' : '+ Add Sight'}
          </button>
        </div>
      </div>
    </div>
  `;
}

function updateMapMarkersAndRoutes(map) {
  if (!map) return;

  // Clean existing markers
  if (!State.activeMapMarkers) State.activeMapMarkers = [];
  State.activeMapMarkers.forEach(m => m.remove());
  State.activeMapMarkers = [];

  const bounds = new maplibregl.LngLatBounds();
  const sel = State.selectedAttractions || [];
  const allPlaces = State.liveAttractions || [];

  // Update places count badge
  const countBadge = document.getElementById('mapPlacesCountBadge');
  if (countBadge) countBadge.textContent = `${allPlaces.length} Places · ${sel.length} Selected`;

  // 1. Plot Base Camp Stay if selected
  if (State.selectedStay && State.selectedStay.lat && State.selectedStay.lon) {
    const stayEl = document.createElement('div');
    stayEl.className = 'custom-map-stay-marker';
    stayEl.innerHTML = `
      <div class="stay-marker-beacon">
        <span class="stay-beacon-icon">🏡</span>
      </div>
      <div class="stay-marker-label">${State.selectedStay.name.split(' ')[0]}</div>
    `;
    const stayPopup = new maplibregl.Popup({ offset: 25, closeButton: false }).setHTML(`
      <div class="p-2 extra-small">
        <div class="fw-bold text-navy"><i class="bi bi-house-door-fill text-warning me-1"></i>Base Camp Stay</div>
        <div class="small fw-semibold mt-1">${State.selectedStay.name}</div>
        <div class="text-muted mt-1">₹${State.selectedStay.price_per_night}/night · ${State.selectedStay.type}</div>
      </div>
    `);
    const stayMarker = new maplibregl.Marker({ element: stayEl })
      .setLngLat([State.selectedStay.lon, State.selectedStay.lat])
      .setPopup(stayPopup)
      .addTo(map);

    stayEl.addEventListener('mouseenter', () => stayPopup.addTo(map));
    stayEl.addEventListener('mouseleave', () => stayPopup.remove());

    State.activeMapMarkers.push(stayMarker);
    bounds.extend([State.selectedStay.lon, State.selectedStay.lat]);
  }

  const daysPlan = getDayPlanArray();
  const dIdx = Math.max(0, (State.activeTimelineDay || 1) - 1);
  const activeDayAttrs = (State.step === 4 && daysPlan[dIdx]) ? daysPlan[dIdx] : sel;

  // 2. Plot ALL Attractions as Interactive Pins
  allPlaces.forEach(a => {
    if (!a.lat || !a.lon) return;

    const daySelIndex = activeDayAttrs.findIndex(x => x.id === a.id);
    const overallSelIndex = sel.findIndex(x => x.id === a.id);
    const isSel = (State.step === 4) ? (daySelIndex > -1) : (overallSelIndex > -1);
    const orderNum = (State.step === 4) ? (daySelIndex + 1) : (overallSelIndex + 1);

    const pinEl = document.createElement('div');
    pinEl.className = `custom-map-place-pin ${isSel ? 'selected' : ''}`;
    pinEl.innerHTML = `
      <div class="pin-bubble">
        <span class="pin-icon">${a.icon}</span>
        ${isSel ? `<span class="pin-num">${orderNum}</span>` : ''}
      </div>
      ${isSel ? `<div class="pin-pulse"></div>` : ''}
    `;

    const popupHtml = buildMapPlacePopupHtml(a, isSel, orderNum);
    const popup = new maplibregl.Popup({ offset: 22, maxWidth: '250px' })
      .setHTML(popupHtml);

    const marker = new maplibregl.Marker({ element: pinEl })
      .setLngLat([a.lon, a.lat])
      .setPopup(popup)
      .addTo(map);

    // Hover preview support
    pinEl.addEventListener('mouseenter', () => {
      popup.setHTML(buildMapPlacePopupHtml(a, isSel, orderNum));
      popup.addTo(map);
    });

    State.activeMapMarkers.push(marker);
    if (isSel) bounds.extend([a.lon, a.lat]);
  });

  // 3. Highlighted Road Routing with Distance Computation
  drawHighlightedRoadRoute(map, bounds);
}

async function drawHighlightedRoadRoute(map, bounds) {
  if (!map) return;
  const sel = State.selectedAttractions || [];
  const distBanner = document.getElementById('mapDistanceBanner');
  const distText = document.getElementById('mapRouteDistText');
  const timeText = document.getElementById('mapRouteTimeText');

  // Remove previous route layers and sources
  ['studio-active-route-casing', 'studio-active-route-line'].forEach(id => {
    if (map.getLayer(id)) map.removeLayer(id);
  });
  if (map.getSource('studio-active-route')) map.removeSource('studio-active-route');

  const daysPlan = getDayPlanArray();
  const dIdx = Math.max(0, (State.activeTimelineDay || 1) - 1);
  const activeDayAttrs = (State.step === 4 && daysPlan[dIdx]) ? daysPlan[dIdx] : sel;

  if (activeDayAttrs.length === 0) {
    if (distBanner) {
      if (distText && timeText && State.step === 4) {
        distText.textContent = `Day ${State.activeTimelineDay || 1}: Leisure Day`;
        timeText.textContent = `At Base Camp`;
        distBanner.style.display = 'block';
      } else {
        distBanner.style.display = 'none';
      }
    }
    return;
  }

  // Build waypoints: Base Camp -> Sight 1 -> Sight 2 -> ... -> Base Camp
  const waypoints = [];
  if (State.selectedStay && State.selectedStay.lat && State.selectedStay.lon) {
    waypoints.push({ lat: State.selectedStay.lat, lon: State.selectedStay.lon, label: State.selectedStay.name });
  } else if (State.destLat && State.destLon) {
    waypoints.push({ lat: State.destLat, lon: State.destLon, label: State.dest });
  }

  activeDayAttrs.forEach(a => {
    if (a.lat && a.lon) waypoints.push({ lat: a.lat, lon: a.lon, label: a.name });
  });

  // Loop back if more than 1 sight
  if (waypoints.length > 2) {
    waypoints.push(waypoints[0]);
  }

  if (waypoints.length < 2) return;

  const coords = waypoints.map(p => `${p.lon},${p.lat}`).join(';');
  const proxyUrl = `/planner/api/osrm?profile=car&coords=${encodeURIComponent(coords)}&overview=full&geometries=geojson`;

  try {
    const res = await fetch(proxyUrl);
    const data = await res.json();
    if (data.code === 'Ok' && data.routes && data.routes[0]) {
      const route = data.routes[0];
      const distKm = (route.distance / 1000).toFixed(1);
      const durMin = Math.round(route.duration / 60);
      const durHrs = durMin >= 60 ? `${Math.floor(durMin / 60)}h ${durMin % 60}m` : `${durMin} min`;

      // Update Floating Distance Banner Overlay
      if (distBanner && distText && timeText) {
        const dayPrefix = (State.step === 4 && State.activeTimelineDay >= 1) ? `Day ${State.activeTimelineDay} · ` : '';
        distText.textContent = `${dayPrefix}${distKm} km road`;
        timeText.textContent = `~${durHrs} drive`;
        distBanner.style.display = 'block';
      }

      // Add Source
      map.addSource('studio-active-route', {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: route.geometry
        }
      });

      // Add Glowing Route Casing (Dark outline)
      map.addLayer({
        id: 'studio-active-route-casing',
        type: 'line',
        source: 'studio-active-route',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': '#0B1F33',
          'line-width': 7,
          'line-opacity': 0.75
        }
      });

      // Add Vibrant Neon Route Line
      map.addLayer({
        id: 'studio-active-route-line',
        type: 'line',
        source: 'studio-active-route',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': '#00A896',
          'line-width': 4,
          'line-opacity': 0.95
        }
      });

      // Update total distance in bottom stat bar
      const tdEl = document.getElementById('totalDistance');
      if (tdEl) tdEl.textContent = `${distKm} km`;
    }
  } catch (err) {
    console.warn('OSRM routing fetch failed', err);
  }

  // Smooth fit to route bounds if user selected attractions
  if (bounds && !bounds.isEmpty()) {
    map.fitBounds(bounds, { padding: 60, maxZoom: 13, duration: 1000 });
  }
}

function renderMap() {
  if (typeof maplibregl === 'undefined') {
    const el = document.getElementById('mapLibreMap');
    if (el) el.innerHTML = '<div class="d-flex align-items-center justify-content-center h-100 text-muted">Map loading…</div>';
    return;
  }

  const sel = State.selectedAttractions || [];
  const center = (State.selectedStay && State.selectedStay.lat)
    ? [State.selectedStay.lon, State.selectedStay.lat]
    : sel.length ? [sel[0].lon, sel[0].lat]
    : (State.destLon ? [State.destLon, State.destLat] : [75.7382, 12.4244]);

  if (!State.mapInstance) {
    const map = new maplibregl.Map({
      container: 'mapLibreMap',
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center,
      zoom: 11,
      attributionControl: true,
    });
    State.mapInstance = map;
    State.mapSatellite = false;
    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    map.on('load', () => {
      updateMapMarkersAndRoutes(map);
    });
  } else {
    // Already created, update markers and routes seamlessly!
    if (center && (!sel || sel.length === 0)) {
      try {
        State.mapInstance.flyTo({ center, zoom: 11, speed: 1.4 });
      } catch (_) {}
    }
    if (State.mapInstance.loaded()) {
      updateMapMarkersAndRoutes(State.mapInstance);
    } else {
      State.mapInstance.once('load', () => updateMapMarkersAndRoutes(State.mapInstance));
    }
  }
}

function mapFlyToRoute() {
  if (!State.mapInstance) return;
  const bounds = new maplibregl.LngLatBounds();
  if (State.selectedStay && State.selectedStay.lat) bounds.extend([State.selectedStay.lon, State.selectedStay.lat]);
  (State.selectedAttractions || []).forEach(a => {
    if (a.lat && a.lon) bounds.extend([a.lon, a.lat]);
  });
  if (!bounds.isEmpty()) {
    State.mapInstance.fitBounds(bounds, { padding: 60, maxZoom: 13, duration: 1000 });
  } else if (State.destLon) {
    State.mapInstance.flyTo({ center: [State.destLon, State.destLat], zoom: 11, speed: 1.2 });
  }
}

function mapToggleSatellite() {
  if (!State.mapInstance) return;
  State.mapSatellite = !State.mapSatellite;
  const style = State.mapSatellite
    ? 'https://tiles.openfreemap.org/styles/positron'
    : 'https://tiles.openfreemap.org/styles/liberty';
  State.mapInstance.setStyle(style);
  State.mapInstance.once('style.load', () => {
    updateMapMarkersAndRoutes(State.mapInstance);
  });
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
        actObject = { id: attraction.id, icon: attraction.icon, name: attraction.name, dur: fmtHrs(attraction.dur), type: 'attraction', category: attraction.cat || '', fee: attraction.fee || 0 };
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
  updateSidebar();
  updatePreviewCard();
  
  showToast('🚀 Route optimized using AI nearest-neighbor algorithm to minimize travel distance!', 'success');
}

/* ── STEP 9 — Analytics ──────────────────────────────────────────── */
function renderAnalytics() {
  const sel  = State.selectedAttractions;
  const grid = document.getElementById('analyticsGrid');
  if (!grid) return;
  const rd   = State.routeData || {};
  const totalMins  = sel.reduce((s,a)=>s+a.dur,0);

  const trav = Math.max(1, State.travelers || 1);
  const transitCostPerPerson = State.transitCostPerPerson || Math.round((State.transitCost || rd.fuelCost || 1200) / trav);
  
  // Accurate Base Camp Stay Cost (Per Person share)
  const nights = Math.max(1, (State.days || 1) - 1);
  const hotelCostTotal = State.selectedStay ? (State.selectedStay.price_per_night * nights) : (State.days * 2000);
  const hotelCostPerPerson = Math.round(hotelCostTotal / trav);
  
  const entryCostPerPerson = sel.reduce((s,a)=>s+(a.fee||0),0);
  const foodCostPerPerson = (State.days || 3) * 600;
  const shoppingCostPerPerson = 500;
  const perPersonSpend = transitCostPerPerson + hotelCostPerPerson + entryCostPerPerson + foodCostPerPerson + shoppingCostPerPerson;
  const totalGroupSpend = perPersonSpend * trav;
  const perPersonBudget = State.budgetPerPerson || State.budget || 15000;

  const distKm     = rd.distKm || sel.reduce((s,a)=>s+a.dist,0);
  const driveMin   = rd.driveMin || Math.round(+distKm/45*60);

  grid.innerHTML = [
    {grad:'ac-grad-blue',   icon:'🛣️', val:distKm+' km',                label:'Transit Distance',    sub:'OSRM / Road & Rail'},
    {grad:'ac-grad-gold',   icon:'🏡', val:fmtINR(hotelCostPerPerson),   label:'Stay (1 Person Share)', sub:State.selectedStay?.name ? `${State.selectedStay.name.slice(0,14)}… (${nights}N)` : `${nights}N · ₹${fmtINR(hotelCostTotal)} room`},
    {grad:'ac-grad-sunset', icon:'🚆', val:fmtINR(transitCostPerPerson), label:'Transit (1 Seat / Share)', sub:State.transitDetails?.mode_title || State.transport},
    {grad:'ac-grad-green',  icon:'👁️', val:fmtHrs(totalMins),          label:'Sightseeing Time',    sub:'Total at attractions'},
    {grad:'ac-grad-purple', icon:'🎟️', val:fmtINR(entryCostPerPerson),  label:'Entry Fees / Person',  sub:sel.length+' places selected'},
    {grad:'ac-grad-blue',   icon:'💸', val:fmtINR(perPersonSpend),      label:'Per Traveler Spend',   sub:`Group: ₹${fmtINR(totalGroupSpend)} for ${trav}`},
    {grad:'ac-grad-green',  icon:'💰', val:fmtINR(Math.max(0,perPersonBudget-perPersonSpend)), label:'Remaining / Person', sub:'From '+fmtINR(perPersonBudget)},
    {grad:'ac-grad-gold',   icon:'📍', val:sel.length,                  label:'Attractions',         sub:'OSM real places'},
  ].map(c=>`<div class="analytics-card ${c.grad}" data-icon="${c.icon}"><div class="ac-val">${c.val}</div><div class="ac-label">${c.label}</div><div class="ac-sub">${c.sub}</div></div>`).join('');

  setTimeout(()=>{
    ['budgetChart','timeChart'].forEach(id=>{const el=document.getElementById(id);if(el&&State.charts[id])State.charts[id].destroy();});
    const bc=document.getElementById('budgetChart');
    if(bc) {
      State.charts.budgetChart=new Chart(bc,{
        type:'doughnut',
        data:{
          labels:[
            'Transit / Seat',
            'Stay Share (' + nights + 'N)',
            'Entry Fees',
            'Food & Dining',
            'Misc & Shopping'
          ],
          datasets:[{
            data:[transitCostPerPerson, hotelCostPerPerson, entryCostPerPerson, foodCostPerPerson, shoppingCostPerPerson],
            backgroundColor:['#0062FF','#f59e0b','#10b981','#8b5cf6','#ec4899'],
            borderWidth:0,
            hoverOffset:8
          }]
        },
        options:{
          plugins:{
            legend:{position:'bottom'}
          },
          cutout:'65%'
        }
      });
    }
    const tc=document.getElementById('timeChart');
    if(tc&&sel.length) {
      State.charts.timeChart=new Chart(tc,{
        type:'bar',
        data:{
          labels:sel.map(a=>a.name.split(' ')[0]),
          datasets:[{
            label:'Minutes',
            data:sel.map(a=>a.dur),
            backgroundColor:'#0062FFcc',
            borderRadius:6,
            borderWidth:0
          }]
        },
        options:{
          plugins:{legend:{display:false}},
          scales:{y:{beginAtZero:true},x:{grid:{display:false}}}
        }
      });
    }
  },300);
}

/* ── STEP 10 / STAGE 5 — Luxury Travel Dossier & AI Final Overview ──── */
function renderOverview() {
  const sel  = State.selectedAttractions || [];
  const body = document.getElementById('overviewBody');
  const rd   = State.routeData || {};
  if (!body) return;

  try {

  const destCity = (State.dest || 'Coorg').split(',')[0].trim();
  const srcCity  = (State.source || 'Bengaluru').split(',')[0].trim();
  const dLower   = destCity.toLowerCase();

  // Dynamic High-Resolution Destination Image
  let heroImg = 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1600&q=85&auto=format&fit=crop';
  if (dLower.includes('ooty')) heroImg = 'https://images.unsplash.com/photo-1589182373726-e4f658ab50f0?w=1600&q=85&auto=format&fit=crop';
  else if (dLower.includes('munnar')) heroImg = 'https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=1600&q=85&auto=format&fit=crop';
  else if (dLower.includes('coorg') || dLower.includes('kodagu') || dLower.includes('madikeri')) heroImg = 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1600&q=85&auto=format&fit=crop';
  else if (dLower.includes('jaipur')) heroImg = 'https://images.unsplash.com/photo-1599661046289-e31897846e41?w=1600&q=85&auto=format&fit=crop';
  else if (dLower.includes('manali')) heroImg = 'https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?w=1600&q=85&auto=format&fit=crop';
  else if (dLower.includes('goa')) heroImg = 'https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=1600&q=85&auto=format&fit=crop';
  else if (dLower.includes('kodaikanal')) heroImg = 'https://images.unsplash.com/photo-1628157582853-a796fa650a6a?w=1600&q=85&auto=format&fit=crop';
  else if (dLower.includes('hampi')) heroImg = 'https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?w=1600&q=85&auto=format&fit=crop';

  const days = Math.max(1, State.days || 3);
  const nights = Math.max(1, days - 1);
  const trav = Math.max(1, State.travelers || 1);

  // Agent 4: Base Camp Stay Info (Per Person Share)
  const baseStay = State.selectedStay || (State.availableStays && State.availableStays[0]) || {
    name: `${destCity} Heritage Sanctuary Resort`,
    address: `${destCity}, Karnataka, India`,
    price_per_night: 2800,
    safety_score: 9.6,
    rating: 4.8
  };
  const stayName = baseStay.name;
  const stayAddress = baseStay.address || `${destCity} Scenic Valley`;
  const staySafety = baseStay.safety_score || 9.5;
  const stayPrice = baseStay.price_per_night || 2800;
  const stayCostTotal = stayPrice * nights;
  const stayCost = stayCostTotal;
  const stayCostPerPerson = Math.round(stayCostTotal / trav);
  const stayImg = baseStay.image || baseStay.image_url || getStayImage(baseStay);

  // Agent 1: Transit Info (Per Person Share)
  const transitMode = (State.transitMode || State.transport || 'Cab').toUpperCase();
  const transitTitle = State.transitDetails?.mode_title || `${transitMode} Connector`;
  const transitDist = State.transitDetails?.distance_km || Math.round(rd.distKm || 280);
  const transitDuration = State.transitDetails?.duration_hours || '5.5';
  const transitFareTotal = State.transitCost || State.transitDetails?.estimated_fare || (transitDist * 10);
  const transitFare = transitFareTotal;
  const transitCostPerPerson = State.transitCostPerPerson || Math.round(transitFareTotal / trav);

  // Agent 3: Financials (Per Person Architecture)
  const entryCostPerPerson = sel.reduce((s, a) => s + (a.fee || 0), 0);
  const entryCostTotal = entryCostPerPerson * trav;
  const foodCostPerPerson = days * 600;
  const foodCostTotal = foodCostPerPerson * trav;
  const miscCostPerPerson = 500;
  const miscCostTotal = miscCostPerPerson * trav;
  
  const perPersonSpend = stayCostPerPerson + transitCostPerPerson + entryCostPerPerson + foodCostPerPerson + miscCostPerPerson;
  const grandTotal = perPersonSpend * trav;
  const totalSpend = grandTotal;
  const perPersonBudget = State.budgetPerPerson || State.budget || 15000;
  const totalBudget = perPersonBudget * trav;

  const pctStay = Math.round((stayCostPerPerson / Math.max(1, perPersonSpend)) * 100);
  const pctTransit = Math.round((transitCostPerPerson / Math.max(1, perPersonSpend)) * 100);
  const pctEntry = Math.round((entryCostPerPerson / Math.max(1, perPersonSpend)) * 100);
  const pctFood = Math.round((foodCostPerPerson / Math.max(1, perPersonSpend)) * 100);
  const pctMisc = Math.max(3, 100 - (pctStay + pctTransit + pctEntry + pctFood));

  const weather = State.weatherData?.current;
  const temp = weather?.temperature || 24;
  const desc = (weather?.description || 'Pleasant & clear');

  const tDate = document.getElementById('w_travel_date')?.value || 'Upcoming';
  const rDate = document.getElementById('w_return_date')?.value || 'Departure';

  const daysPlan = getDayPlanArray();
  const dayLabels = [
    'Arrival & Scenic First Impressions',
    'Deep Landscape & Heritage Exploration',
    'Cultural Sanctum & Hidden Trails',
    'High Elevation Vistas & Nature Serenity',
    'Departure & Leisure Farewell'
  ];

  // Smart Packing Items
  const isRain = desc.toLowerCase().includes('rain') || ((weather?.humidity || 0) > 75);
  const isCold = temp < 18;
  const isHot = temp > 30;

  const packingItems = [
    { label: 'Govt Photo ID / Aadhaar Card', cat: 'essential' },
    { label: 'Smartphone & Rapid Charger', cat: 'essential' },
    { label: 'Power Bank (10,000mAh)', cat: 'essential' },
    { label: 'Emergency Cash (₹2,000 in notes)', cat: 'essential' },
    { label: 'Comfortable Trek/Walking Shoes', cat: 'essential' },
    { label: 'Personal Prescription Medications', cat: 'essential' }
  ];

  if (isRain) {
    packingItems.push(
      { label: 'Rain Poncho / Compact Umbrella', cat: 'weather' },
      { label: 'Waterproof Phone Pouch', cat: 'weather' },
      { label: 'Insect / Leech Repellent', cat: 'weather' }
    );
  } else if (isCold) {
    packingItems.push(
      { label: 'Thermal Fleece / Woolen Pullover', cat: 'weather' },
      { label: 'Warm Beanie & Muffler', cat: 'weather' }
    );
  } else if (isHot) {
    packingItems.push(
      { label: 'Sunscreen SPF 50+ & UV Sunglasses', cat: 'weather' },
      { label: 'Electrolyte ORS Sachets', cat: 'weather' }
    );
  }

  if (State.style === 'Adventure') {
    packingItems.push({ label: 'Trek Pole & LED Headlamp', cat: 'style' }, { label: 'Muscle Relief Spray', cat: 'style' });
  } else if (State.style === 'Family') {
    packingItems.push({ label: 'Motion Sickness Tablets', cat: 'style' }, { label: 'Kids Sanitizer & Healthy Snacks', cat: 'style' });
  }

  body.innerHTML = `
    <!-- ══════ 1. LUXURY 2-PART BOARDING PASS EXPEDITION TICKET ══════ -->
    <div class="dossier-boarding-pass shadow-2xl" id="dossierTicket">
      <!-- Left: Main Boarding Pass (72%) -->
      <div class="ticket-main-body">
        <!-- Header: Operator & PNR -->
        <div class="ticket-header-row">
          <div class="ticket-airline-brand">
            <i class="bi ${transitMode === 'FLIGHT' ? 'bi-airplane-engines-fill' : (transitMode === 'TRAIN' ? 'bi-train-front-fill' : 'bi-bus-front-fill')} text-turquoise fs-5"></i>
            <span class="ticket-brand-text">YATRIKA EXPEDITION BOARDING PASS</span>
            <span class="ticket-carrier-pill">✓ IRCTC / RTC VERIFIED</span>
          </div>
          <div class="ticket-pnr-badge">
            <span class="pnr-lbl">PNR</span>
            <span class="pnr-code">YTR-${Math.floor(100000 + Math.random() * 900000)}</span>
          </div>
        </div>

        <!-- Route Corridor -->
        <div class="ticket-corridor-row">
          <div class="corridor-station origin-station">
            <div class="station-code">${srcCity.slice(0, 3).toUpperCase()}</div>
            <div class="station-city">${srcCity}</div>
            <div class="station-sub"><i class="bi bi-geo-alt-fill text-turquoise me-1"></i>Origin Terminal</div>
          </div>

          <div class="corridor-path-wrapper">
            <div class="corridor-duration-badge">
              <i class="bi bi-clock-history me-1"></i>${transitDuration || '5.5'}h Direct Transit · ~${transitDist} km
            </div>
            <div class="corridor-flight-line">
              <div class="corridor-dot start-dot"></div>
              <div class="corridor-track"></div>
              <div class="corridor-transit-icon">
                <i class="bi ${transitMode === 'FLIGHT' ? 'bi-airplane-fill' : (transitMode === 'TRAIN' ? 'bi-train-front-fill' : 'bi-bus-front-fill')}"></i>
              </div>
              <div class="corridor-track"></div>
              <div class="corridor-dot end-dot"></div>
            </div>
            <div class="corridor-mode-pill">
              ${transitTitle}
            </div>
          </div>

          <div class="corridor-station dest-station text-end">
            <div class="station-code text-turquoise">${destCity.slice(0, 3).toUpperCase()}</div>
            <div class="station-city">${destCity}</div>
            <div class="station-sub"><i class="bi bi-flag-fill text-coral me-1"></i>Base Camp Gate</div>
          </div>
        </div>

        <!-- Specs Row -->
        <div class="ticket-specs-row">
          <div class="spec-col">
            <div class="spec-lbl">Travel Dates</div>
            <div class="spec-val">${tDate} → ${rDate}</div>
          </div>
          <div class="spec-col">
            <div class="spec-lbl">Duration</div>
            <div class="spec-val">${days} Days · ${nights} Nights</div>
          </div>
          <div class="spec-col">
            <div class="spec-lbl">Travelers</div>
            <div class="spec-val">${trav} Traveler${trav > 1 ? 's' : ''} (Confirmed)</div>
          </div>
          <div class="spec-col">
            <div class="spec-lbl">Base Camp Stay</div>
            <div class="spec-val text-truncate text-turquoise" style="max-width: 190px;" title="${stayName}">${stayName}</div>
          </div>
        </div>
      </div>

      <!-- Center: Perforated Tear-Off Divider with Cutout Notches -->
      <div class="ticket-perforation-divider">
        <div class="notch-cutout notch-top"></div>
        <div class="perforation-dashed-line"></div>
        <div class="notch-cutout notch-bottom"></div>
      </div>

      <!-- Right: Passenger Tear-off Stub (28%) -->
      <div class="ticket-stub-body">
        <div class="stub-header">
          <span class="stub-tag">PASSENGER STUB</span>
          <span class="stub-class-badge">${State.transitClass || (transitMode === 'FLIGHT' ? 'ECONOMY PREMIER' : (transitMode === 'TRAIN' ? 'EXECUTIVE CHAIR' : 'DELUXE COACH'))}</span>
        </div>

        <!-- Authentic SVG Vector QR Code Tile -->
        <div class="stub-qr-container">
          <div class="stub-qr-box">
            <svg viewBox="0 0 33 33" width="66" height="66" fill="#07192F" xmlns="http://www.w3.org/2000/svg">
              <rect x="0" y="0" width="11" height="11" rx="2" fill="#07192F"/>
              <rect x="2" y="2" width="7" height="7" rx="1" fill="#FFFFFF"/>
              <rect x="4" y="4" width="3" height="3" fill="#07192F"/>
              <rect x="22" y="0" width="11" height="11" rx="2" fill="#07192F"/>
              <rect x="24" y="2" width="7" height="7" rx="1" fill="#FFFFFF"/>
              <rect x="26" y="4" width="3" height="3" fill="#07192F"/>
              <rect x="0" y="22" width="11" height="11" rx="2" fill="#07192F"/>
              <rect x="2" y="24" width="7" height="7" rx="1" fill="#FFFFFF"/>
              <rect x="4" y="26" width="3" height="3" fill="#07192F"/>
              <rect x="13" y="1" width="2" height="2"/>
              <rect x="17" y="1" width="2" height="2"/>
              <rect x="13" y="5" width="2" height="2"/>
              <rect x="17" y="5" width="2" height="2"/>
              <rect x="15" y="7" width="2" height="2"/>
              <rect x="13" y="9" width="2" height="2"/>
              <rect x="1" y="13" width="2" height="2"/>
              <rect x="5" y="13" width="2" height="2"/>
              <rect x="9" y="13" width="2" height="2"/>
              <rect x="13" y="13" width="3" height="3"/>
              <rect x="18" y="13" width="2" height="2"/>
              <rect x="22" y="13" width="2" height="2"/>
              <rect x="26" y="13" width="2" height="2"/>
              <rect x="30" y="13" width="2" height="2"/>
              <rect x="3" y="17" width="2" height="2"/>
              <rect x="7" y="17" width="2" height="2"/>
              <rect x="14" y="17" width="2" height="2"/>
              <rect x="18" y="17" width="3" height="3"/>
              <rect x="24" y="17" width="2" height="2"/>
              <rect x="28" y="17" width="2" height="2"/>
              <rect x="13" y="22" width="2" height="2"/>
              <rect x="17" y="22" width="2" height="2"/>
              <rect x="23" y="22" width="2" height="2"/>
              <rect x="27" y="22" width="2" height="2"/>
              <rect x="15" y="26" width="2" height="2"/>
              <rect x="19" y="26" width="2" height="2"/>
              <rect x="25" y="26" width="2" height="2"/>
              <rect x="29" y="26" width="2" height="2"/>
              <rect x="13" y="30" width="3" height="2"/>
              <rect x="18" y="30" width="2" height="2"/>
              <rect x="22" y="30" width="2" height="2"/>
              <rect x="26" y="30" width="3" height="2"/>
            </svg>
          </div>
          <div class="stub-pnr-micro font-monospace">VERIFIED PASS</div>
        </div>

        <!-- Fare Block -->
        <div class="stub-fare-block">
          <div class="stub-fare-lbl">1-PERSON FARE</div>
          <div class="stub-fare-val">₹${perPersonSpend.toLocaleString('en-IN')}</div>
          <div class="stub-fare-group">Group Total: ₹${grandTotal.toLocaleString('en-IN')} (${trav} pax)</div>
        </div>

        <!-- Quick Action Dock -->
        <div class="stub-actions-dock">
          <button type="button" class="btn-stub btn-save-trip" onclick="saveCustomWizardTripDirectly()">
            <i class="bi bi-floppy-fill"></i> Save Trip to Dashboard
          </button>
          <div class="d-flex gap-2">
            <button type="button" class="btn-stub btn-outline-stub" onclick="window.print()" style="flex:1;">
              <i class="bi bi-printer"></i> Print
            </button>
            <button type="button" class="btn-stub btn-outline-stub" onclick="shareToWhatsApp()" style="flex:1;">
              <i class="bi bi-whatsapp text-success"></i> WhatsApp
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════ 2. THE 4-PILLAR EXPEDITION INTELLIGENCE SPOTLIGHT ══════ -->
    <section class="bento-briefing-grid">
      <!-- 1: Base Camp Stay -->
      <div class="bento-briefing-card card-stay">
        <div>
          <div class="bento-card-badge">
            <i class="bi bi-house-check-fill text-success"></i> Curated Sanctuary
          </div>
          <div class="bento-card-val text-truncate" title="${stayName}">
            ${stayName}
          </div>
          <div class="bento-card-desc mb-2 text-truncate" title="${stayAddress}">
            <i class="bi bi-geo-alt me-1 text-success"></i>${stayAddress}
          </div>
        </div>
        <div class="bento-card-footer">
          <span class="badge bg-success-subtle text-success border border-success-subtle small">
            🛡️ Safety Index: ${staySafety}/10
          </span>
          <span class="fw-bold text-success">
            ₹${stayCostPerPerson.toLocaleString('en-IN')}<span class="text-muted small"> / person (${nights}N)</span>
          </span>
        </div>
      </div>

      <!-- 2: Door-to-Door Transit -->
      <div class="bento-briefing-card card-transit">
        <div>
          <div class="bento-card-badge">
            <i class="bi bi-signpost-2-fill text-primary"></i> Connected Transit
          </div>
          <div class="bento-card-val text-truncate">
            ${transitTitle}
          </div>
          <div class="bento-card-desc mb-2">
            ${srcCity} ➔ ${destCity} · ~${transitDist} km (~${transitDuration} hrs)
          </div>
        </div>
        <div class="bento-card-footer">
          <span class="badge bg-info-subtle text-info border border-info-subtle small">${State.isRoundTrip ? 'Round-Trip' : 'Direct Corridor'}</span>
          <span class="fw-bold text-primary">₹${transitCostPerPerson.toLocaleString('en-IN')}<span class="text-muted small"> / seat</span></span>
        </div>
      </div>

      <!-- 3: Financial & Expense Estimator -->
      <div class="bento-briefing-card card-budget">
        <div>
          <div class="bento-card-badge">
            <i class="bi bi-wallet2 text-warning"></i> Financial Blueprint
          </div>
          <div class="bento-card-val text-warning">
            ₹${perPersonSpend.toLocaleString('en-IN')} <span class="text-muted fs-6 fw-normal">/ traveler</span>
          </div>
          <div class="bento-card-desc mb-2">
            Group Grand Total: ₹${grandTotal.toLocaleString('en-IN')} for ${trav} traveler${trav > 1 ? 's' : ''}.
          </div>
        </div>
        <div class="bento-card-footer">
          <span class="badge ${perPersonBudget >= perPersonSpend ? 'bg-success-subtle text-success' : 'bg-warning-subtle text-warning'} border small">
            ${perPersonBudget >= perPersonSpend ? '✓ Under Target' : 'Review Allocation'}
          </span>
          <span class="fw-bold text-secondary small">Target: ₹${perPersonBudget.toLocaleString('en-IN')}</span>
        </div>
      </div>

      <!-- 4: Sightseeing Footprint -->
      <div class="bento-briefing-card card-sights">
        <div>
          <div class="bento-card-badge">
            <i class="bi bi-compass-fill text-purple" style="color: #8B5CF6;"></i> Curated Sight Loops
          </div>
          <div class="bento-card-val">
            ${sel.length} Verified Sights
          </div>
          <div class="bento-card-desc mb-2">
            Stay-grounded clustering (&lt; 45 km radius) with 0 backtracking loops.
          </div>
        </div>
        <div class="bento-card-footer">
          <span class="badge bg-primary-subtle text-primary border border-primary-subtle small">10,025 Spot Dataset</span>
          <span class="fw-bold small" style="color: #8B5CF6;">Random Forest ML</span>
        </div>
      </div>
    </section>

    <!-- ══════ 3. CONSOLIDATED 6-PILLAR LUXURY TAB NAVIGATION ══════ -->
    <div class="pillar-tabs-container" id="wizardOverviewTabs" role="tablist">
      <a class="pillar-tab-btn active" data-bs-toggle="pill" href="#wo-tab-itinerary" onclick="switchOverviewPillar('itinerary')">
        <i class="bi bi-compass-fill"></i> 1. Master Itinerary
      </a>
      <a class="pillar-tab-btn" data-bs-toggle="pill" href="#wo-tab-planner" onclick="switchOverviewPillar('planner')">
        <i class="bi bi-calendar3-week"></i> 2. Day Schedule
      </a>
      <a class="pillar-tab-btn" data-bs-toggle="pill" href="#wo-tab-map" onclick="switchOverviewPillar('map')">
        <i class="bi bi-map-fill"></i> 3. Route &amp; Sights
      </a>
      <a class="pillar-tab-btn" data-bs-toggle="pill" href="#wo-tab-hotels" onclick="switchOverviewPillar('hotels')">
        <i class="bi bi-house-door-fill"></i> 4. Base Camp &amp; Stays
      </a>
      <a class="pillar-tab-btn" data-bs-toggle="pill" href="#wo-tab-budget" onclick="switchOverviewPillar('budget')">
        <i class="bi bi-pie-chart-fill"></i> 5. Budget &amp; Expenses
      </a>
      <a class="pillar-tab-btn" data-bs-toggle="pill" href="#wo-tab-packing" onclick="switchOverviewPillar('packing')">
        <i class="bi bi-bag-check-fill"></i> 6. Packing Checklist
      </a>
    </div>

    <!-- ══════ 4. TAB CONTENT MODULES ══════ -->
    <div class="tab-content" id="woTabContent">

      <!-- ╔══════════════════════════════════════════════════════════╗
           ║ PILLAR 1: MASTER ITINERARY & SIGHTSEEING LOOPS         ║
           ╚══════════════════════════════════════════════════════════╝ -->
      <div class="tab-pane fade show active" id="wo-tab-itinerary">
        <div class="row g-4">
          <!-- Left: Narrative & Daily Loops -->
          <div class="col-lg-8">
            <!-- Curated Trip Narrative -->
            <div class="dossier-section-card">
              <h3 class="dossier-section-title">
                <i class="bi bi-book text-turquoise"></i> Curated Expedition Narrative
              </h3>
              <p class="mb-3" style="color: #1E293B; line-height: 1.75; font-size: 0.98rem; font-weight: 500;">
                Customized multi-day exploration of <strong>${destCity}</strong> anchored to <strong>${stayName}</strong>.
                Each day balances scenic landmarks, natural heritage, and cultural discovery with optimized door-to-door transit to minimize road fatigue and avoid backtrack loops.
              </p>
              <div class="d-flex flex-wrap gap-2 pt-3 border-top" style="border-color: #E2E8F0 !important;">
                <span class="badge rounded-pill small px-3 py-2 fw-semibold" style="background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0;">
                  🌸 Best Time: October to May
                </span>
                <span class="badge rounded-pill small px-3 py-2 fw-semibold" style="background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;">
                  🗣️ Languages: Regional &amp; English
                </span>
                <span class="badge rounded-pill small px-3 py-2 fw-semibold" style="background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A;">
                  ₹ Currency: INR (₹)
                </span>
                <span class="badge rounded-pill small px-3 py-2 fw-semibold" style="background: #F5F3FF; color: #6D28D9; border: 1px solid #DDD6FE;">
                  🕒 Timezone: IST (UTC+05:30)
                </span>
              </div>
            </div>

            <!-- Day-by-Day Loop Briefing -->
            <div class="dossier-section-card">
              <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                <h3 class="dossier-section-title mb-0">
                  <i class="bi bi-calendar-range text-turquoise"></i> Day-by-Day Itinerary Loops
                </h3>
                <span class="small fw-semibold" style="color: #64748B;">Anchored to Base Camp</span>
              </div>

              ${daysPlan.map((dayAttrs, d) => {
                const dayNum = d + 1;
                const dayTitle = dayLabels[d] || `Day ${dayNum} Exploration`;
                const dayDist = dayAttrs.reduce((sum, a) => sum + (a.dist || 0), 0);

                return `
                  <div class="daily-loop-card">
                    <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom" style="border-color: #E2E8F0 !important;">
                      <div class="d-flex align-items-center gap-2">
                        <span class="badge rounded-pill bg-turquoise text-dark fw-bold px-3 py-1">Day ${dayNum}</span>
                        <h5 class="fw-bold mb-0" style="color: #0F172A;">${dayTitle}</h5>
                      </div>
                      <span class="small fw-medium d-none d-sm-inline" style="color: #64748B;">
                        <i class="bi bi-house me-1 text-turquoise"></i>${stayName}
                      </span>
                    </div>

                    <!-- Morning Kickoff / Breakfast -->
                    <div class="slot-row-item">
                      <span class="slot-time-badge">🌅 Morning</span>
                      <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-center">
                          <strong style="color: #0F172A; font-weight: 700;">Breakfast &amp; Base Camp Departure</strong>
                          <span class="badge extra-small px-2 py-1 fw-bold" style="background: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1;">08:00 AM</span>
                        </div>
                        <div class="small mt-1" style="color: #475569; font-weight: 450;">Enjoy authentic local breakfast at ${stayName} before setting out on the morning circuit.</div>
                      </div>
                    </div>

                    ${dayAttrs.length === 0 ? `
                      <div class="p-3 my-2 text-center rounded-3 small" style="background: #F8FAFC; border: 1.5px solid #E2E8F0; color: #475569;">
                        <i class="bi bi-cup-hot me-1 text-warning"></i>
                        <strong style="color: #0F172A;">Leisure &amp; Scenic Relaxation:</strong> Unwind at base camp, explore neighborhood plantation walks, and enjoy panoramic sunset vistas.
                      </div>
                    ` : dayAttrs.map((a, i) => {
                      const cardImg = (a.img && a.img.trim()) ? a.img : 'https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=300&q=80';
                      return `
                        ${i > 0 ? `
                          <div class="dossier-drive-connector">
                            <i class="bi bi-arrow-down-short"></i>
                            <span style="color: #0284C7; font-weight: 600;">🚗 ~${Math.max(3, Math.round(a.dist || 6))} km drive (~${Math.max(10, Math.round((a.dist || 6) * 2.2))} mins)</span>
                          </div>
                        ` : ''}
                        <div class="slot-row-item">
                          <span class="slot-time-badge" style="color: #B45309; background: #FEF3C7; border-color: #FDE68A;">
                            Stop ${i + 1}
                          </span>
                          <img src="${cardImg}" alt="${a.name}" class="dossier-stop-img" onerror="this.src='https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=300&q=80'"/>
                          <div class="flex-grow-1 overflow-hidden">
                            <div class="d-flex justify-content-between align-items-center">
                              <strong class="text-truncate" style="color: #0F172A; font-weight: 700;">${a.name}</strong>
                              <span class="badge extra-small ms-2 fw-bold" style="background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A;">${fmtHrs(a.dur || 60)}</span>
                            </div>
                            <div class="small mt-1" style="color: #475569; font-weight: 450;">${a.icon || '📍'} ${a.cat || 'Attraction'} · Proximity ~${(a.dist || 5).toFixed(1)} km from Base Camp</div>
                          </div>
                          <div class="text-end extra-small flex-shrink-0 ms-2">
                            <span class="badge fw-semibold" style="background: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1;">${a.fee > 0 ? `₹${a.fee}` : 'Free'}</span>
                          </div>
                        </div>
                      `;
                    }).join('')}

                    <!-- Evening Return / Dinner -->
                    <div class="slot-row-item">
                      <span class="slot-time-badge" style="color: #6D28D9; background: #EDE9FE; border-color: #DDD6FE;">🌆 Evening</span>
                      <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-center">
                          <strong style="color: #0F172A; font-weight: 700;">Base Camp Return &amp; Authentic Dinner</strong>
                          <span class="badge extra-small px-2 py-1 fw-bold" style="background: #F5F3FF; color: #6D28D9; border: 1px solid #DDD6FE;">08:00 PM</span>
                        </div>
                        <div class="small mt-1" style="color: #475569; font-weight: 450;">Return to ${stayName} for culinary dinner and leisurely evening around the fireplace.</div>
                      </div>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>

            <!-- Tourist Attractions Pill Grid -->
            <div class="dossier-section-card">
              <h3 class="dossier-section-title">
                <i class="bi bi-geo-alt-fill text-coral"></i> Top Sights Selected by AI Planner
              </h3>
              <div class="row g-3">
                ${sel.slice(0, 10).map((a, idx) => `
                  <div class="col-sm-6">
                    <div class="p-3 rounded-4 d-flex align-items-center gap-3" style="background: #F8FAFC; border: 1.5px solid #E2E8F0;">
                      <span style="font-size: 1.8rem;">${a.icon || '📍'}</span>
                      <div class="overflow-hidden">
                        <div class="fw-bold text-truncate" style="color: #0F172A;" title="${a.name}">${idx + 1}. ${a.name}</div>
                        <div class="small text-truncate" style="color: #64748B;">${a.cat || 'Sight'} · ⭐ ${a.rating || '4.6'} · ~${(a.dist || 4.5).toFixed(1)} km</div>
                      </div>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>

          <!-- Right: Trip Statistics & Helplines -->
          <div class="col-lg-4">
            <!-- Expedition Parameters -->
            <div class="dossier-section-card mb-4">
              <h4 class="dossier-section-title" style="font-size: 1.05rem;">
                <i class="bi bi-speedometer2 text-turquoise"></i> Expedition Parameters
              </h4>
              <div class="row g-2">
                <div class="col-6">
                  <div class="stat-grid-card">
                    <div class="stat-icon">📅</div>
                    <div class="stat-val text-truncate">${days} Days</div>
                    <div class="stat-lbl">Duration</div>
                  </div>
                </div>
                <div class="col-6">
                  <div class="stat-grid-card">
                    <div class="stat-icon">👥</div>
                    <div class="stat-val text-truncate">${State.travelers} Person${State.travelers > 1 ? 's' : ''}</div>
                    <div class="stat-lbl">Travelers</div>
                  </div>
                </div>
                <div class="col-6">
                  <div class="stat-grid-card">
                    <div class="stat-icon">💰</div>
                    <div class="stat-val text-truncate text-warning">₹${totalSpend.toLocaleString('en-IN')}</div>
                    <div class="stat-lbl">Projected Spend</div>
                  </div>
                </div>
                <div class="col-6">
                  <div class="stat-grid-card">
                    <div class="stat-icon">🚆</div>
                    <div class="stat-val text-truncate">${transitMode}</div>
                    <div class="stat-lbl">Transit Mode</div>
                  </div>
                </div>
                <div class="col-6">
                  <div class="stat-grid-card">
                    <div class="stat-icon">🎯</div>
                    <div class="stat-val text-truncate">${State.style}</div>
                    <div class="stat-lbl">Travel Style</div>
                  </div>
                </div>
                <div class="col-6">
                  <div class="stat-grid-card">
                    <div class="stat-icon">🛡️</div>
                    <div class="stat-val text-truncate text-success">${staySafety}/10</div>
                    <div class="stat-lbl">Stay Safety</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 24/7 Helplines -->
            <div class="dossier-section-card mb-4">
              <h4 class="dossier-section-title" style="font-size: 1.05rem;">
                <i class="bi bi-shield-fill-exclamation text-coral"></i> 24/7 National Emergency Helplines
              </h4>
              <div class="d-flex flex-column gap-2">
                <div class="emergency-row-item">
                  <div>
                    <div class="fw-bold small" style="color: #0F172A;">Police Support</div>
                    <div class="extra-small" style="color: #64748B;">National Emergency</div>
                  </div>
                  <a href="tel:100" class="emergency-call-btn">100</a>
                </div>
                <div class="emergency-row-item">
                  <div>
                    <div class="fw-bold small" style="color: #0F172A;">Medical Ambulance</div>
                    <div class="extra-small" style="color: #64748B;">Emergency Healthcare</div>
                  </div>
                  <a href="tel:108" class="emergency-call-btn">108</a>
                </div>
                <div class="emergency-row-item">
                  <div>
                    <div class="fw-bold small" style="color: #0F172A;">Tourist Helpline</div>
                    <div class="extra-small" style="color: #64748B;">Toll-Free Support</div>
                  </div>
                  <a href="tel:1363" class="emergency-call-btn">1363</a>
                </div>
                <div class="emergency-row-item">
                  <div>
                    <div class="fw-bold small" style="color: #0F172A;">Disaster Operations</div>
                    <div class="extra-small" style="color: #64748B;">State Helpline</div>
                  </div>
                  <a href="tel:1070" class="emergency-call-btn">1070</a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ╔══════════════════════════════════════════════════════════╗
           ║ PILLAR 2: DAY SCHEDULE VIEW                            ║
           ╚══════════════════════════════════════════════════════════╝ -->
      <div class="tab-pane fade" id="wo-tab-planner">
        <div class="dossier-section-card">
          <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
            <div>
              <h3 class="dossier-section-title mb-1">
                <i class="bi bi-calendar3-week text-turquoise"></i> Daily Schedule Matrix
              </h3>
              <p class="text-white-50 small mb-0">Structured slots for Morning, Afternoon, and Evening across your multi-day expedition.</p>
            </div>
            <!-- Day selector pills -->
            <div class="d-flex gap-2 flex-wrap">
              ${Array.from({ length: days }, (_, i) => i + 1).map(d => `
                <button type="button" class="btn btn-sm ${d === 1 ? 'btn-turquoise text-dark' : 'btn-outline-light'} rounded-pill px-3 py-1 fw-bold wo-day-pill" id="woDayBtn-${d}" onclick="switchOverviewDay(${d})">
                  Day ${d}
                </button>
              `).join('')}
            </div>
          </div>

          ${Array.from({ length: days }, (_, i) => {
            const d = i + 1;
            const dayAttrs = daysPlan[i] || [];
            const morningActs = dayAttrs.slice(0, 1);
            const afternoonActs = dayAttrs.slice(1, 3);
            const eveningActs = dayAttrs.slice(3);

            return `
              <div class="wo-day-schedule-view ${d === 1 ? '' : 'd-none'}" id="woDayView-${d}">
                <div class="row g-3">
                  <!-- Morning -->
                  <div class="col-md-4">
                    <div class="time-column-custom h-100">
                      <div class="time-col-header-custom">
                        <span>🌅 Morning</span>
                        <span class="text-white-50 small">6:00 AM – 12:00 PM</span>
                      </div>
                      ${morningActs.length ? morningActs.map(a => `
                        <div class="activity-card">
                          <span style="font-size:1.2rem">${a.icon || '📍'}</span>
                          <div class="overflow-hidden">
                            <div class="fw-bold text-truncate">${a.name}</div>
                            <div class="text-white-50 extra-small">${a.cat || 'Sight'} · ${fmtHrs(a.dur || 60)}</div>
                          </div>
                        </div>
                      `).join('') : `
                        <div class="activity-card text-white-50">
                          <span>☕</span>
                          <div>Breakfast at ${stayName}</div>
                        </div>
                      `}
                    </div>
                  </div>

                  <!-- Afternoon -->
                  <div class="col-md-4">
                    <div class="time-column-custom h-100">
                      <div class="time-col-header-custom">
                        <span>☀️ Afternoon</span>
                        <span class="text-white-50 small">12:00 PM – 5:00 PM</span>
                      </div>
                      ${afternoonActs.length ? afternoonActs.map(a => `
                        <div class="activity-card">
                          <span style="font-size:1.2rem">${a.icon || '📍'}</span>
                          <div class="overflow-hidden">
                            <div class="fw-bold text-truncate">${a.name}</div>
                            <div class="text-white-50 extra-small">${a.cat || 'Sight'} · ${fmtHrs(a.dur || 60)}</div>
                          </div>
                        </div>
                      `).join('') : `
                        <div class="activity-card text-white-50">
                          <span>🍽️</span>
                          <div>Local Dining &amp; Heritage Walks</div>
                        </div>
                      `}
                    </div>
                  </div>

                  <!-- Evening -->
                  <div class="col-md-4">
                    <div class="time-column-custom h-100">
                      <div class="time-col-header-custom">
                        <span>🌆 Evening</span>
                        <span class="text-white-50 small">5:00 PM – 9:30 PM</span>
                      </div>
                      ${eveningActs.length ? eveningActs.map(a => `
                        <div class="activity-card">
                          <span style="font-size:1.2rem">${a.icon || '📍'}</span>
                          <div class="overflow-hidden">
                            <div class="fw-bold text-truncate">${a.name}</div>
                            <div class="text-white-50 extra-small">${a.cat || 'Sight'} · ${fmtHrs(a.dur || 60)}</div>
                          </div>
                        </div>
                      `).join('') : `
                        <div class="activity-card text-white-50">
                          <span>🏡</span>
                          <div>Return to ${stayName} &amp; Dinner</div>
                        </div>
                      `}
                    </div>
                  </div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>

      <!-- ╔══════════════════════════════════════════════════════════╗
           ║ PILLAR 3: ROUTE & SIGHTS                               ║
           ╚══════════════════════════════════════════════════════════╝ -->
      <div class="tab-pane fade" id="wo-tab-map">
        <div class="row g-4">
          <div class="col-lg-7">
            <div class="dossier-section-card h-100">
              <h4 class="dossier-section-title">
                <i class="bi bi-signpost-split text-turquoise"></i> Pinned Expedition Waypoints
              </h4>
              <div class="p-3 rounded-4 mb-3" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08);">
                <div class="d-flex align-items-center gap-3">
                  <div class="p-2 rounded-circle bg-primary-subtle text-primary fs-4"><i class="bi bi-geo-alt-fill"></i></div>
                  <div>
                    <div class="fw-bold text-white">Origin Station</div>
                    <div class="text-white-50 small">${srcCity}</div>
                  </div>
                </div>
              </div>

              <div class="p-3 rounded-4 mb-3" style="background: rgba(20, 184, 166, 0.1); border: 1px solid rgba(20, 184, 166, 0.25);">
                <div class="d-flex align-items-center gap-3">
                  <div class="p-2 rounded-circle bg-turquoise text-dark fs-4"><i class="bi bi-house-door-fill"></i></div>
                  <div>
                    <div class="fw-bold text-white">${stayName} (Base Camp Anchor)</div>
                    <div class="text-white-50 small">${stayAddress}</div>
                  </div>
                </div>
              </div>

              <div class="d-flex flex-column gap-2 mt-3">
                <h6 class="text-white-50 small text-uppercase fw-bold mb-1">Waypoints &amp; Distances from Base Camp:</h6>
                ${sel.map((a, i) => `
                  <div class="p-2 rounded-3 d-flex justify-content-between align-items-center" style="background: rgba(255, 255, 255, 0.03);">
                    <div class="d-flex align-items-center gap-2 text-truncate">
                      <span class="badge bg-dark text-turquoise border">${i + 1}</span>
                      <span class="text-white small text-truncate">${a.name}</span>
                    </div>
                    <span class="text-white-50 extra-small flex-shrink-0 ms-2">🚗 ~${(a.dist || 5).toFixed(1)} km</span>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>

          <div class="col-lg-5">
            <div class="dossier-section-card mb-4">
              <h4 class="dossier-section-title" style="font-size: 1.05rem;">
                <i class="bi bi-car-front text-turquoise"></i> Journey Highway Metrics
              </h4>
              <div class="p-3 rounded-4" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08);">
                <div class="d-flex justify-content-between py-2 border-bottom border-white border-opacity-10 small">
                  <span class="text-white-50">Direct Highway Distance:</span>
                  <strong class="text-white">~${transitDist} km</strong>
                </div>
                <div class="d-flex justify-content-between py-2 border-bottom border-white border-opacity-10 small">
                  <span class="text-white-50">Estimated Drive Duration:</span>
                  <strong class="text-white">~${transitDuration} hours</strong>
                </div>
                <div class="d-flex justify-content-between py-2 border-bottom border-white border-opacity-10 small">
                  <span class="text-white-50">Local Sightseeing Mileage:</span>
                  <strong class="text-white">~${sel.reduce((s, a) => s + (a.dist || 0), 0).toFixed(1)} km road</strong>
                </div>
                <div class="d-flex justify-content-between pt-2 small">
                  <span class="text-white-50">Transit Estimated Cost:</span>
                  <strong class="text-turquoise">₹${transitFare.toLocaleString('en-IN')}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ╔══════════════════════════════════════════════════════════╗
           ║ PILLAR 4: BASE CAMP & STAYS                            ║
           ╚══════════════════════════════════════════════════════════╝ -->
      <div class="tab-pane fade" id="wo-tab-hotels">
        <!-- Spotlight on Locked Base Camp -->
        <div class="dossier-section-card mb-4" style="border-left: 5px solid var(--dossier-teal);">
          <div class="d-flex justify-content-between align-items-start mb-2 flex-wrap gap-2">
            <div>
              <span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-1 mb-2">
                <i class="bi bi-house-check me-1"></i> Locked Base Camp Anchor
              </span>
              <h3 class="fw-bold text-white mb-1">${stayName}</h3>
              <div class="text-white-50 small"><i class="bi bi-geo-alt me-1 text-turquoise"></i>${stayAddress}</div>
            </div>
            <div class="text-end">
              <div class="fs-4 fw-extrabold text-turquoise">₹${stayPrice.toLocaleString('en-IN')}</div>
              <div class="text-white-50 extra-small">per night (${nights} nights = ₹${stayCost.toLocaleString('en-IN')})</div>
            </div>
          </div>
          <div class="d-flex gap-3 align-items-center mt-3">
            <img src="${stayImg}" alt="${stayName}" class="rounded-4" style="width: 110px; height: 90px; object-fit: cover;" onerror="this.src='https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=400&q=80'"/>
            <div>
              <div class="badge bg-dark text-turquoise border border-secondary mb-2">🛡️ Safety Rating: ${staySafety} / 10</div>
              <p class="text-white-50 small mb-0">High-speed Wi-Fi, 24/7 security reception, dedicated parking, and centralized access to all scheduled sights.</p>
            </div>
          </div>
        </div>

        <!-- Alternative Recommended Stays in destination -->
        ${(State.availableStays && State.availableStays.length > 1) ? `
          <div class="d-flex align-items-center gap-2 mb-3 mt-4">
            <span class="badge rounded-pill bg-dark text-turquoise border border-secondary px-3 py-1">Alternative Curated Stays in ${destCity}</span>
          </div>
          <div class="row g-3">
            ${State.availableStays.slice(1, 4).map(h => `
              <div class="col-md-4">
                <div class="p-3 rounded-4 h-100 d-flex flex-column" style="background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08);">
                  <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="fw-bold text-white mb-0 text-truncate" title="${h.name}">${h.name}</h6>
                    <span class="text-turquoise fw-bold small ms-2">₹${h.price_per_night || 2400}<span class="text-white-50 extra-small">/nt</span></span>
                  </div>
                  <div class="text-white-50 extra-small mb-2 text-truncate">${h.address || destCity}</div>
                  <div class="mt-auto d-flex justify-content-between align-items-center pt-2 border-top border-white border-opacity-10">
                    <span class="text-warning small">⭐ ${h.rating || 4.5}</span>
                    <span class="badge bg-dark text-white-50 border border-secondary extra-small">Verified</span>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        ` : ''}
      </div>

      <!-- ╔══════════════════════════════════════════════════════════╗
           ║ PILLAR 5: BUDGET & EXPENSES                            ║
           ╚══════════════════════════════════════════════════════════╝ -->
      <div class="tab-pane fade" id="wo-tab-budget">
        <div class="row g-4">
          <!-- Segmented Meter & Allocation (Per Person) -->
          <div class="col-lg-5">
            <div class="dossier-section-card h-100">
              <h4 class="dossier-section-title">
                <i class="bi bi-pie-chart text-turquoise"></i> Budget Meter (1 Traveler)
              </h4>

              <!-- Segmented Bar -->
              <div class="budget-segmented-bar">
                <div class="bsb-segment bsb-stay" style="width: ${pctStay}%" title="Stay: ₹${stayCostPerPerson}"></div>
                <div class="bsb-segment bsb-transit" style="width: ${pctTransit}%" title="Transit: ₹${transitCostPerPerson}"></div>
                <div class="bsb-segment bsb-entry" style="width: ${pctEntry}%" title="Entry: ₹${entryCostPerPerson}"></div>
                <div class="bsb-segment bsb-food" style="width: ${pctFood}%" title="Food: ₹${foodCostPerPerson}"></div>
                <div class="bsb-segment bsb-misc" style="width: ${pctMisc}%" title="Misc: ₹${miscCostPerPerson}"></div>
              </div>

              <div class="dossier-budget-legend">
                <span class="dbl-item"><span class="dbl-dot bsb-stay"></span> Stay ₹${stayCostPerPerson.toLocaleString('en-IN')} (${pctStay}%)</span>
                <span class="dbl-item"><span class="dbl-dot bsb-transit"></span> Transit ₹${transitCostPerPerson.toLocaleString('en-IN')} (${pctTransit}%)</span>
                <span class="dbl-item"><span class="dbl-dot bsb-entry"></span> Sights ₹${entryCostPerPerson.toLocaleString('en-IN')} (${pctEntry}%)</span>
                <span class="dbl-item"><span class="dbl-dot bsb-food"></span> Food ₹${foodCostPerPerson.toLocaleString('en-IN')} (${pctFood}%)</span>
              </div>

              <div class="p-3 rounded-4 mt-3" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08);">
                <div class="d-flex justify-content-between py-1 border-bottom border-white border-opacity-10 small">
                  <span class="text-white-50">Per Traveler Spend:</span>
                  <strong class="text-warning">₹${perPersonSpend.toLocaleString('en-IN')}</strong>
                </div>
                <div class="d-flex justify-content-between py-1 border-bottom border-white border-opacity-10 small">
                  <span class="text-white-50">Per Traveler Budget:</span>
                  <strong class="text-white">₹${perPersonBudget.toLocaleString('en-IN')}</strong>
                </div>
                <div class="d-flex justify-content-between py-1 border-bottom border-white border-opacity-10 small">
                  <span class="text-white-50">Status:</span>
                  <strong class="${perPersonBudget >= perPersonSpend ? 'text-success' : 'text-warning'}">
                    ${perPersonBudget >= perPersonSpend ? '✓ On Budget' : '! Exceeds Budget'}
                  </strong>
                </div>
                <div class="d-flex justify-content-between pt-1 extra-small text-white-50">
                  <span>Group Total:</span>
                  <span class="text-turquoise fw-bold">₹${grandTotal.toLocaleString('en-IN')} for ${trav} travelers</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Itemized Breakdown & Grand Multiplier -->
          <div class="col-lg-7">
            <div class="dossier-section-card">
              <h4 class="dossier-section-title">
                <i class="bi bi-card-checklist text-turquoise"></i> Per-Traveler Expense Ledger
              </h4>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1 small">
                  <span class="fw-bold text-white">Base Camp Accommodation (${nights} Nights)</span>
                  <span class="text-end">
                    <strong class="text-turquoise">₹${stayCostPerPerson.toLocaleString('en-IN')}</strong>
                    <span class="text-white-50 extra-small">/ traveler</span>
                  </span>
                </div>
                <div class="progress bg-dark" style="height: 6px; border-radius: 999px;">
                  <div class="progress-bar bg-warning" style="width: ${pctStay}%"></div>
                </div>
                <div class="text-white-50 extra-small mt-1">₹${stayPrice.toLocaleString('en-IN')}/nt room · Room total ₹${stayCostTotal.toLocaleString('en-IN')}</div>
              </div>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1 small">
                  <span class="fw-bold text-white">Inter-City Transit (${transitMode})</span>
                  <span class="text-end">
                    <strong class="text-turquoise">₹${transitCostPerPerson.toLocaleString('en-IN')}</strong>
                    <span class="text-white-50 extra-small">/ seat</span>
                  </span>
                </div>
                <div class="progress bg-dark" style="height: 6px; border-radius: 999px;">
                  <div class="progress-bar bg-info" style="width: ${pctTransit}%"></div>
                </div>
                <div class="text-white-50 extra-small mt-1">${transitTitle} · Group total ₹${transitFareTotal.toLocaleString('en-IN')}</div>
              </div>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1 small">
                  <span class="fw-bold text-white">Sightseeing Entry Fees</span>
                  <span class="text-end">
                    <strong class="text-turquoise">₹${entryCostPerPerson.toLocaleString('en-IN')}</strong>
                    <span class="text-white-50 extra-small">/ person</span>
                  </span>
                </div>
                <div class="progress bg-dark" style="height: 6px; border-radius: 999px;">
                  <div class="progress-bar" style="background: #a855f7; width: ${pctEntry}%"></div>
                </div>
                <div class="text-white-50 extra-small mt-1">${sel.length} attractions selected</div>
              </div>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1 small">
                  <span class="fw-bold text-white">Food &amp; Dining (${days} Days)</span>
                  <span class="text-end">
                    <strong class="text-turquoise">₹${foodCostPerPerson.toLocaleString('en-IN')}</strong>
                    <span class="text-white-50 extra-small">/ person</span>
                  </span>
                </div>
                <div class="progress bg-dark" style="height: 6px; border-radius: 999px;">
                  <div class="progress-bar bg-turquoise" style="width: ${pctFood}%"></div>
                </div>
                <div class="text-white-50 extra-small mt-1">₹600/day daily allowance</div>
              </div>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1 small">
                  <span class="fw-bold text-white">Misc &amp; Contingency</span>
                  <span class="text-end">
                    <strong class="text-turquoise">₹${miscCostPerPerson.toLocaleString('en-IN')}</strong>
                    <span class="text-white-50 extra-small">/ person</span>
                  </span>
                </div>
                <div class="progress bg-dark" style="height: 6px; border-radius: 999px;">
                  <div class="progress-bar bg-secondary" style="width: ${pctMisc}%"></div>
                </div>
              </div>

              <!-- Grand Total Multiplier Box -->
              <div class="grand-total-multiplier-box mt-4 p-3 rounded-4" style="background: linear-gradient(135deg, rgba(0, 168, 150, 0.15) 0%, rgba(11, 31, 51, 0.6) 100%); border: 1.5px solid rgba(0, 168, 150, 0.4); box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);">
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-2 pb-2 border-bottom border-white border-opacity-10">
                  <div class="d-flex align-items-center gap-2">
                    <span class="badge text-dark fw-bold px-2 py-1" style="background: #00A896;"><i class="bi bi-calculator me-1"></i> GROUP MULTIPLIER</span>
                    <span class="text-white-50 small">Final Group Reconciled Settlement</span>
                  </div>
                  <span class="badge bg-success-subtle text-success extra-small fw-bold">ML Verified</span>
                </div>
                <div class="row align-items-center text-center g-2">
                  <div class="col-12 col-sm-4">
                    <div class="text-white-50 extra-small text-uppercase fw-semibold mb-1">Per Traveler Cost</div>
                    <div class="fs-4 fw-bolder text-turquoise">₹${perPersonSpend.toLocaleString('en-IN')}</div>
                    <div class="text-white-50 extra-small">All items included</div>
                  </div>
                  <div class="col-12 col-sm-1 d-flex justify-content-center">
                    <div class="fs-3 text-white-50 fw-bold">×</div>
                  </div>
                  <div class="col-12 col-sm-3">
                    <div class="text-white-50 extra-small text-uppercase fw-semibold mb-1">Travelers</div>
                    <div class="fs-4 fw-bolder text-white">${trav} Travelers</div>
                    <div class="text-white-50 extra-small">In your party</div>
                  </div>
                  <div class="col-12 col-sm-1 d-flex justify-content-center">
                    <div class="fs-3 text-white-50 fw-bold">=</div>
                  </div>
                  <div class="col-12 col-sm-3">
                    <div class="text-warning extra-small text-uppercase fw-bold mb-1">Grand Group Total</div>
                    <div class="fs-3 fw-black text-warning">₹${grandTotal.toLocaleString('en-IN')}</div>
                    <div class="text-white-50 extra-small">₹${totalBudget.toLocaleString('en-IN')} group budget</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ╔══════════════════════════════════════════════════════════╗
           ║ PILLAR 6: PACKING CHECKLIST                            ║
           ╚══════════════════════════════════════════════════════════╝ -->
      <div class="tab-pane fade" id="wo-tab-packing">
        <div class="dossier-section-card">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="dossier-section-title mb-0">
              <i class="bi bi-backpack text-warning"></i> Smart Tailored Packing Checklist
            </h4>
            <span class="badge bg-dark text-turquoise border border-secondary">
              ${temp}°C · ${State.style} Style
            </span>
          </div>

          <div class="row g-3">
            ${packingItems.map(item => `
              <div class="col-md-6 col-lg-4">
                <div class="p-3 rounded-4 d-flex align-items-center gap-2" style="background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08);">
                  <input type="checkbox" class="form-check-input mt-0 me-2" style="cursor: pointer;"/>
                  <span class="text-white small">${item.label}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

    </div>
  `;
  } catch (err) {
    console.error('Error rendering trip overview:', err);
    body.innerHTML = `
      <div class="alert alert-warning p-4 rounded-4 my-3 text-white" style="background: rgba(245, 158, 11, 0.15); border: 1.5px solid rgba(245, 158, 11, 0.4);">
        <h5 class="fw-bold"><i class="bi bi-info-circle me-2"></i>Trip Overview Initializing</h5>
        <p class="small mb-3">Please ensure your journey details and stay are selected. Click below to refresh your itinerary overview.</p>
        <button type="button" class="btn btn-sm btn-warning rounded-pill px-4 fw-bold" onclick="renderOverview()">Refresh Overview</button>
      </div>
    `;
  }
}

// Global Tab Switcher Helpers for Overview
window.switchOverviewPillar = function(tabKey) {
  document.querySelectorAll('#wizardOverviewTabs .pillar-tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  document.querySelectorAll('#woTabContent .tab-pane').forEach(pane => {
    pane.classList.remove('show', 'active');
  });
  const activeBtn = document.querySelector(`#wizardOverviewTabs [href="#wo-tab-${tabKey}"]`);
  if (activeBtn) activeBtn.classList.add('active');
  const activePane = document.getElementById(`wo-tab-${tabKey}`);
  if (activePane) activePane.classList.add('show', 'active');
};

window.switchOverviewDay = function(dayNum) {
  document.querySelectorAll('.wo-day-pill').forEach(btn => {
    btn.classList.remove('btn-turquoise', 'text-dark');
    btn.classList.add('btn-outline-light');
  });
  document.querySelectorAll('.wo-day-schedule-view').forEach(view => {
    view.classList.add('d-none');
  });
  const activeBtn = document.getElementById(`woDayBtn-${dayNum}`);
  if (activeBtn) {
    activeBtn.classList.add('btn-turquoise', 'text-dark');
    activeBtn.classList.remove('btn-outline-light');
  }
  const activeView = document.getElementById(`woDayView-${dayNum}`);
  if (activeView) activeView.classList.remove('d-none');
};


/* ── Download / Share / Clear / Save ────────────────────────────── */
function downloadItinerary() {
  const sel = State.selectedAttractions;
  const rd  = State.routeData || {};
  const td  = document.getElementById('w_travel_date')?.value || 'TBD';
  const ret = document.getElementById('w_return_date')?.value || 'TBD';
  const nights = Math.max(1, (State.days || 1) - 1);
  const stayCost = State.selectedStay ? (State.selectedStay.price_per_night * nights) : (State.days * 2000);
  const transitCost = State.transitCost || rd.fuelCost || 2500;
  const entryCost = sel.reduce((s,a)=>s+(a.fee||0),0);
  const foodCost = State.travelers * State.days * 600;
  const totalCost = stayCost + transitCost + entryCost + foodCost + State.travelers * 500;

  const lines = [
    `SMART TRAVEL ITINERARY & BASE CAMP DISPATCH`,
    `${'='.repeat(55)}`,
    `Destination : ${State.dest}`,
    `From        : ${State.source}`,
    `Dates       : ${td} → ${ret} (${State.days} Days · ${State.travelers} Travelers)`,
    `Travel Style: ${State.style}`,
    ``,
    `BASE CAMP ACCOMMODATION (Anchor Stay)`,
    `${'─'.repeat(55)}`,
    `Stay Name   : ${State.selectedStay ? State.selectedStay.name : 'Base Stay'}`,
    `Stay Type   : ${State.selectedStay?.type || 'Homestay / Resort'}`,
    `Tariff      : ${State.selectedStay ? fmtINR(State.selectedStay.price_per_night) : '₹2,000'}/night x ${nights} Nights = ${fmtINR(stayCost)}`,
    `Timing      : Check-in: 12:00 PM | Check-out: 11:00 AM`,
    ``,
    `INTER-CITY TRANSIT BOOKING`,
    `${'─'.repeat(55)}`,
    `Transit     : ${State.transitDetails?.mode_title || State.transport.toUpperCase()}`,
    `Details     : ${State.transitDetails?.details_summary || 'Direct Route'}`,
    `Arrival     : ~${State.arrivalTime || '12:00'} (Directly at Base Camp Stay)`,
    `Fare        : ${fmtINR(transitCost)} (${State.isRoundTrip ? 'Round-Trip' : 'Onward'})`,
    ``,
    `ESTIMATED BUDGET BREAKDOWN`,
    `${'─'.repeat(55)}`,
    `Transit Fare       : ${fmtINR(transitCost)}`,
    `Stay Cost          : ${fmtINR(stayCost)}`,
    `Sightseeing Entry  : ${fmtINR(entryCost)}`,
    `Food & Dining      : ${fmtINR(foodCost)}`,
    `Misc & Shopping    : ${fmtINR(State.travelers * 500)}`,
    `Total Est. Spend   : ${fmtINR(totalCost)} (Budget: ${fmtINR(State.budget)})`,
    ``,
    `ATTRACTIONS SCHEDULE (Door-to-door from Base Camp)`,
    `${'─'.repeat(55)}`,
    ...sel.map((a,i)=>`${i+1}. ${a.name}\n   Category: ${a.cat} | Visit: ${fmtHrs(a.dur)} | Rating: ${a.rating}★\n   Location: ${a.lat ? a.lat.toFixed(4)+','+a.lon.toFixed(4) : 'Coordinates pending'}`),
    ``,
    `EMERGENCY CONTACTS`,
    `${'─'.repeat(55)}`,
    `Police: 100 | Ambulance: 108 | Fire: 101 | Tourist Helpline: 1363`,
    ``,
    `Generated by AI Travel Planner · Powered by Real Live Transit & OpenStreetMap`
  ];
  const blob = new Blob([lines.join('\n')], {type:'text/plain'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `itinerary_${(State.dest.split(',')[0]).replace(/\s+/g,'_')}_${td}.txt`;
  a.click();
  showToast('✅ Detailed itinerary downloaded!', 'success');
}

function shareToWhatsApp() {
  const td = document.getElementById('w_travel_date')?.value || 'TBD';
  const ret = document.getElementById('w_return_date')?.value || 'TBD';
  const stayName = State.selectedStay ? State.selectedStay.name : `${State.dest.split(',')[0]} Base Camp`;
  const transitTitle = State.transitDetails?.mode_title || State.transport;
  const transitSummary = State.transitDetails?.details_summary || '';
  const sel = State.selectedAttractions || [];
  const topPlaces = sel.slice(0, 4).map((a, i) => `${i + 1}. ${a.name}`).join('\n');
  const nights = Math.max(1, (State.days || 1) - 1);
  const stayTotal = (State.selectedStay ? State.selectedStay.price_per_night : 2000) * nights;
  const transitCost = State.transitCost || State.routeData?.fuelCost || 2500;
  const totalEst = stayTotal + transitCost + sel.reduce((s, a) => s + (a.fee || 0), 0) + State.travelers * State.days * 600;

  const msg = `🌟 *Travel Plan: ${State.dest.split(',')[0]}* 🌟\n` +
    `📍 Route: ${State.source} ➔ ${State.dest}\n` +
    `📅 Dates: ${td} to ${ret} (${State.days} Days · ${State.travelers} Travelers)\n` +
    `🎯 Style: ${State.style}\n\n` +
    `🏡 *Base Camp Stay:*\n${stayName} (${nights} Nights @ ${State.selectedStay ? fmtINR(State.selectedStay.price_per_night) : '₹2,000'}/N)\n\n` +
    `🚆 *Transit Booking:*\n${transitTitle} (Arrives ~${State.arrivalTime || '12:00'} directly at stay entrance)\n${transitSummary ? transitSummary + '\n' : ''}\n` +
    `🏞️ *Key Attractions:*\n${topPlaces}\n\n` +
    `💰 *Estimated Total Spend:* ${fmtINR(totalEst)}\n\n` +
    `Created with AI Travel Planner 🚀`;

  const waUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`;
  window.open(waUrl, '_blank');
  showToast('📲 Opening WhatsApp to share your itinerary...', 'success');
}

function shareTrip() {
  const text = `🗺️ I'm planning a trip to ${State.dest.split(',')[0]} from ${State.source.split(',')[0]}!\n📅 ${State.days} days · 👥 ${State.travelers} travelers · 🎯 ${State.style}\n🏡 Base Camp: ${State.selectedStay ? State.selectedStay.name : State.dest}\n🚆 Transit: ${State.transitDetails?.mode_title || State.transport}\n📍 Attractions: ${State.selectedAttractions.slice(0,3).map(a=>a.name).join(', ')}${State.selectedAttractions.length>3?'…':''}`;
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
/* ── Inter-City Transit Functions ────────────────────────────────── */
/* ── Base Camp (Stay/Hotel) Functions ────────────────────────────── */
async function fetchDestinationStays(dest) {
  const container = document.getElementById('staysListContainer');
  if (!container || !dest) return;

  container.innerHTML = `
    <div class="col-12 py-3 text-center text-muted small">
      <span class="spinner-border spinner-border-sm me-2 text-primary" role="status"></span>
      Searching verified base camps &amp; homestays in ${dest}...
    </div>
  `;

  try {
    const res = await fetch(`/planner/api/stays/search?destination=${encodeURIComponent(dest)}`);
    if (res.ok) {
      const stays = await res.json();
      State.availableStays = stays || [];
      renderDestinationStays(stays);
    }
  } catch (e) {
    console.warn('Failed to fetch destination stays:', e);
  }
}

function getStayImage(stay) {
  if (stay.image_url) return stay.image_url;
  const stayImages = [
    'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1540541338287-41700207dee6?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1584132967334-10e028bd69f7?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1510312305653-8ed496efae75?w=600&auto=format&fit=crop&q=80'
  ];
  let hash = 0;
  const str = (stay.id || '') + (stay.name || '');
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  const idx = Math.abs(hash) % stayImages.length;
  return stayImages[idx];
}

function formatStayAddress(addr, dest) {
  if (!addr) return dest || 'Scenic Location';
  let clean = addr.replace(/\d{6}/g, '').replace(/Karnataka/gi, '').trim();
  const parts = clean.split(',').map(p => p.trim()).filter(Boolean);
  if (parts.length > 1) {
    return `${parts[0]}, ${parts[1]}`.trim();
  }
  return clean.length > 32 ? clean.substring(0, 30).trim() + '…' : clean;
}

function filterStays(category, btnEl) {
  document.querySelectorAll('.stay-filter-tabs .filter-pill').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');

  const allStays = State.availableStays || [];
  if (category === 'all') {
    renderDestinationStays(allStays);
    return;
  }
  const filtered = allStays.filter(s => {
    const text = ((s.type || '') + ' ' + (s.badge || '') + ' ' + (s.name || '')).toLowerCase();
    if (category === 'resort') return text.includes('resort') || text.includes('luxury');
    if (category === 'homestay') return text.includes('homestay') || text.includes('estate');
    if (category === 'boutique') return text.includes('boutique') || text.includes('villa') || text.includes('heritage');
    if (category === 'budget') return s.price_per_night < 2500 || text.includes('camp') || text.includes('hostel');
    return true;
  });
  renderDestinationStays(filtered);
}
window.filterStays = filterStays;

function renderDestinationStays(stays) {
  const container = document.getElementById('staysListContainer');
  if (!container) return;

  if (!stays || stays.length === 0) {
    container.innerHTML = `
      <div class="col-12 py-4 text-center text-muted small bg-surface border rounded-4">
        <i class="bi bi-house-exclamation fs-3 text-warning mb-2 d-block"></i>
        No stays found matching this filter in ${State.dest || 'destination'}.
      </div>
    `;
    return;
  }

  const numDays = State.days || 3;
  const nights = Math.max(1, numDays - 1);
  const trav = Math.max(1, State.travelers || 1);

  container.innerHTML = stays.map(s => {
    const isSelected = State.selectedStay && State.selectedStay.id === s.id;
    const totalStayCost = s.price_per_night * nights;
    const stayPerPerson = Math.round(totalStayCost / trav);
    const imgUrl = getStayImage(s);
    const cleanAddr = formatStayAddress(s.address, State.dest);
    const amenitiesList = (s.amenities || ['Free WiFi', 'Scenic View', 'Room Service']).slice(0, 2).map(am => `<span class="stay-amenity-tag">${am}</span>`).join('');

    return `
      <div class="col-12 col-md-6 col-xl-4">
        <div class="stay-card-redesign ${isSelected ? 'selected' : ''}" onclick="selectBaseCampStay('${s.id}', true)">
          <div class="stay-card-img-wrap">
            <img src="${imgUrl}" alt="${s.name}" class="stay-card-img" loading="lazy" />
            <div class="stay-card-img-overlay"></div>
            <span class="stay-badge-pill ${isSelected ? 'selected' : ''}">${s.badge || s.type || 'Verified Stay'}</span>
            <span class="stay-rating-pill">★ ${s.rating || '4.8'}</span>
          </div>

          <div class="stay-card-body">
            <div class="stay-card-title text-navy" title="${s.name}">${s.name}</div>
            <div class="stay-card-location">
              <i class="bi bi-geo-alt-fill text-turquoise me-1"></i>${cleanAddr}
            </div>

            <div class="d-flex flex-wrap gap-1 my-1">
              ${amenitiesList}
            </div>

            <div class="d-flex justify-content-between align-items-end mt-auto pt-2 border-top">
              <div>
                <span class="stay-price-val">₹${stayPerPerson.toLocaleString('en-IN')}</span>
                <span class="text-muted extra-small">/ traveler (${nights}n)</span>
                <div class="extra-small text-muted">₹${s.price_per_night.toLocaleString('en-IN')}/nt room · ₹${totalStayCost.toLocaleString('en-IN')} group</div>
              </div>
              <button type="button" class="btn btn-sm stay-select-btn ${isSelected ? 'btn-success text-white' : 'btn-outline-primary'}">
                ${isSelected ? '✓ Selected' : 'Select →'}
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function selectBaseCampStay(stayId, showNotice = true) {
  const stay = (State.availableStays || []).find(s => s.id === stayId);
  if (!stay) return;

  State.selectedStay = stay;
  if (stay.lat && stay.lon) {
    State.destLat = parseFloat(stay.lat);
    State.destLon = parseFloat(stay.lon);
  }
  renderDestinationStays(State.availableStays);
  updatePreviewCard();

  const badge = document.getElementById('staySelectedBadge');
  if (badge) {
    badge.innerHTML = `<i class="bi bi-check-circle-fill me-1"></i>Base Camp: <strong>${stay.name}</strong>`;
    badge.className = 'badge bg-success text-white small';
  }

  // Update Preview & Summary Bars
  const pcStayName = document.getElementById('pc_stay_name');
  const pcStayCost = document.getElementById('pc_stay_cost');
  const nights = Math.max(1, (State.days || 3) - 1);
  const totalCost = stay.price_per_night * nights;
  const trav = Math.max(1, State.travelers || 1);
  const perPersonCost = Math.round(totalCost / trav);

  if (pcStayName) pcStayName.textContent = stay.name;
  if (pcStayCost) pcStayCost.textContent = `₹${perPersonCost.toLocaleString('en-IN')}`;

  const tStayName = document.getElementById('tSummaryStayName');
  const tStayCost = document.getElementById('tSummaryStayCost');
  if (tStayName) tStayName.textContent = stay.name;
  if (tStayCost) tStayCost.textContent = `₹${perPersonCost.toLocaleString('en-IN')} / person (₹${totalCost.toLocaleString('en-IN')} room)`;

  const pcDest = document.getElementById('pc_dest');
  if (pcDest) pcDest.textContent = `${State.dest} (${stay.name})`;

  if (showNotice) {
    showToast(`🏡 Selected Stay: ${stay.name}! Unlocking door-to-door transit…`, 'success');
  }

  // Smoothly glide to Stage 2 (Transit) after a brief selection confirmation
  setTimeout(() => {
    goToStep(2);
  }, 450);
}


/* ── Multimodal Tab & Sort Controls ──────────────────────────────── */
function switchTransitTab(tabMode) {
  State.activeTransitTab = tabMode;
  document.querySelectorAll('.d2d-tab-btn, .ixigo-tab-btn').forEach(btn => btn.classList.remove('active'));
  const targetBtn = document.getElementById(`tab_${tabMode}`);
  if (targetBtn) targetBtn.classList.add('active');

  renderActiveTransitOptions();
}

function setTransitDirection(dir) {
  State.transitDirection = dir;
  document.getElementById('btnTransitOnward')?.classList.toggle('active', dir === 'onward');
  document.getElementById('btnTransitReturn')?.classList.toggle('active', dir === 'return');
  renderActiveTransitOptions();
}

function toggleRoundTripBudget(checked) {
  State.includeReturnBudget = checked;
  updateBudgetLabels(State.budget || 15000);
  renderActiveTransitOptions();
}

function sortTransitList(sortMode) {
  State.transitSortMode = sortMode;
  ['cheap', 'fast', 'eco', 'night'].forEach(s => {
    document.getElementById(`sort_${s}`)?.classList.toggle('active', s === sortMode);
  });
  renderActiveTransitOptions();
}

/* ── Inter-City Transit Fetch & Update ────────────────────────────── */
async function fetchInterCityTransit(forcedMode, forcedClass) {
  const mode = forcedMode || State.transitMode || 'train';
  const cls  = forcedClass || State.transitClass || null;
  State.transitMode = mode;
  if (!State.activeTransitTab) State.activeTransitTab = mode;
  if (cls) State.transitClass = cls;
  if (!State.source || !State.dest) return;

  try {
    const res = await fetch('/planner/api/transit/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source: State.source,
        destination: State.dest,
        selected_mode: mode,
        selected_class: cls,
        travelers: State.travelers
      })
    });
    if (res.ok) {
      const data = await res.json();
      State.transitCost = data.transit_cost || 0;
      State.transitCostPerPerson = Math.round(State.transitCost / Math.max(1, State.travelers || 1));
      State.arrivalTime = data.arrival_time || '10:00';
      State.transitDetails = data.chosen_details || {};
      State.transitOptions = data.all_options || {};
      State.transitClass = data.selected_class || data.chosen_details?.selected_class || cls;
      updateTransitUI(data);
    }
  } catch (e) {
    console.warn('Inter-City transit fetch failed:', e);
  }
}

function updateBudgetLabels(val) {
  const numVal = parseInt(val) || 15000;
  State.budget = numVal;
  State.budgetPerPerson = numVal;
  const trav = State.travelers || 2;
  const bVal = document.getElementById('w_budget_val');
  if (bVal) bVal.textContent = '₹' + numVal.toLocaleString('en-IN') + ' / traveler';
  const groupHint = document.getElementById('w_group_total_hint');
  if (groupHint) groupHint.textContent = `Group: ₹${(numVal * trav).toLocaleString('en-IN')} for ${trav}`;
  const pBadge = document.getElementById('w_per_person_badge');
  if (pBadge) pBadge.textContent = '₹' + numVal.toLocaleString('en-IN') + ' / person';
  const sumBudget = document.getElementById('sumBudget');
  if (sumBudget) sumBudget.textContent = `₹${numVal.toLocaleString('en-IN')} / person`;
  updatePreviewCard();
  saveStateToLS();
}

function selectTransitClass(clsName) {
  State.transitClass = clsName;
  fetchInterCityTransit(State.transitMode, clsName);
}

function updateTransitUI(data) {
  const opts = data.all_options || {};
  State.transitOptions = opts;

  // Update tab starting price badges
  const trainMin = opts.train?.min_fare_per_seat || opts.train?.fare_per_traveler || 240;
  const busMin   = opts.bus?.min_fare_per_seat || opts.bus?.fare_per_traveler || 390;
  const carTotal = opts.car?.total_cost || 2406;
  const flMin    = opts.flight?.min_fare_per_seat || opts.flight?.fare_per_traveler || 4200;

  const bTrain = document.getElementById('badge_train_fare');
  const bBus   = document.getElementById('badge_bus_fare');
  const bCar   = document.getElementById('badge_car_fare');
  const bFl    = document.getElementById('badge_flight_fare');

  if (bTrain) bTrain.textContent = `from ₹${trainMin.toLocaleString('en-IN')}`;
  if (bBus)   bBus.textContent   = `from ₹${busMin.toLocaleString('en-IN')}`;
  if (bCar)   bCar.textContent   = `₹${carTotal.toLocaleString('en-IN')} total`;
  if (bFl)    bFl.textContent    = `from ₹${flMin.toLocaleString('en-IN')}`;

  // Smart group break-even tip
  const groupTip = document.getElementById('transitGroupTip');
  if (groupTip) {
    if ((State.travelers || 1) >= 3) {
      const perCar = Math.round(carTotal / State.travelers);
      groupTip.innerHTML = `💡 Group Insight: Own car / Outstation cab is ~₹${perCar}/person for ${State.travelers} travelers!`;
    } else {
      groupTip.textContent = '';
    }
  }

  // Set default active tab if not set
  if (!State.activeTransitTab) {
    State.activeTransitTab = 'train';
  }

  renderActiveTransitOptions();
}

/* ── Multi-Class Helpers (GN, 2S, SL, 3A, 2A, 1A & Bus/Flight tiers) ── */
function getFullTrainClasses(baseFare, rawClasses) {
  const defaults = [
    { code: 'GN', name: 'General', mult: 0.45, defaultStatus: 'GN-AVL' },
    { code: '2S', name: '2nd Sitting', mult: 0.65, defaultStatus: 'AVL 54' },
    { code: 'SL', name: 'Sleeper', mult: 1.25, defaultStatus: 'AVL 38' },
    { code: '3A', name: '3-Tier AC', mult: 3.20, defaultStatus: 'AVL 22' },
    { code: '2A', name: '2-Tier AC', mult: 4.60, defaultStatus: 'RAC 04' },
    { code: '1A', name: '1st AC', mult: 7.50, defaultStatus: 'WL 06' }
  ];

  const map = {};
  if (Array.isArray(rawClasses)) {
    rawClasses.forEach(c => {
      if (c && c.code) map[c.code.toUpperCase()] = c;
    });
  }

  return defaults.map(d => {
    const existing = map[d.code];
    let fare = existing && existing.fare ? existing.fare : Math.round(baseFare * d.mult);
    if (d.code === 'GN') fare = Math.max(65, fare);
    if (d.code === '2S') fare = Math.max(120, fare);
    if (d.code === 'SL') fare = Math.max(260, fare);
    if (d.code === '3A') fare = Math.max(680, fare);
    if (d.code === '2A') fare = Math.max(980, fare);
    if (d.code === '1A') fare = Math.max(1650, fare);

    const status = existing?.status || d.defaultStatus;
    let tag = 'avl';
    if (status.includes('WL')) tag = 'wl';
    else if (status.includes('RAC')) tag = 'rac';

    return {
      code: d.code,
      name: d.name,
      fare: fare,
      status: status,
      tag: tag
    };
  });
}

function getBusClasses(baseFare) {
  return [
    { code: 'Seater', name: 'Express Seater', fare: Math.round(baseFare), status: 'AVL 22', tag: 'avl' },
    { code: 'Semi-Sleeper', name: 'Semi-Sleeper', fare: Math.round(baseFare * 1.35), status: 'AVL 14', tag: 'avl' },
    { code: 'AC Sleeper', name: 'Multi-Axle AC Sleeper', fare: Math.round(baseFare * 1.80), status: 'AVL 08', tag: 'avl' }
  ];
}

function getFlightClasses(baseFare) {
  return [
    { code: 'Economy', name: 'Economy Saver', fare: Math.round(baseFare), status: 'Cabin 7kg', tag: 'avl' },
    { code: 'Flexi', name: 'Flexi Check-in', fare: Math.round(baseFare * 1.25), status: '15kg + Meal', tag: 'avl' },
    { code: 'Business', name: 'Business Class', fare: Math.round(baseFare * 2.35), status: '25kg + Lounge', tag: 'avl' }
  ];
}

function filterTransitByTime(period, btnEl) {
  State.transitTimeFilter = period;
  document.querySelectorAll('.d2d-sort-pills .d2d-sort-pill').forEach(btn => {
    if (btn.id && btn.id.startsWith('time_')) btn.classList.remove('active');
  });
  if (btnEl) btnEl.classList.add('active');
  else {
    const el = document.getElementById(`time_${period}`);
    if (el) el.classList.add('active');
  }
  renderActiveTransitOptions();
}

function matchesTransitTimeFilter(depTime) {
  if (!State.transitTimeFilter || State.transitTimeFilter === 'all') return true;
  if (!depTime) return true;
  const match = depTime.match(/(\d\d?):(\d\d)/);
  if (!match) return true;
  const h = parseInt(match[1]);
  if (State.transitTimeFilter === 'morning') {
    return h >= 4 && h < 12;
  } else if (State.transitTimeFilter === 'afternoon') {
    return h >= 12 && h < 18;
  } else if (State.transitTimeFilter === 'overnight') {
    return h >= 18 || h < 4;
  }
  return true;
}

function selectCardClass(cardId, classCode, farePerPerson, status, event) {
  if (event) event.stopPropagation();
  const card = document.getElementById(cardId) || document.querySelector(`[data-card-id="${cardId}"]`);
  if (!card) return;

  // Toggle active class pill
  card.querySelectorAll('.d2d-class-pill').forEach(p => p.classList.remove('active'));
  const clickedPill = event ? event.currentTarget : card.querySelector(`[data-class-code="${classCode}"]`);
  if (clickedPill) clickedPill.classList.add('active');

  // Update card data & fare text strictly to 1 person fare
  card.setAttribute('data-selected-class', classCode);
  card.setAttribute('data-selected-fare', farePerPerson);

  const fareEl = card.querySelector('.d2d-stub-fare');
  if (fareEl) fareEl.textContent = `₹${farePerPerson.toLocaleString('en-IN')}`;

  const ppEl = card.querySelector('.d2d-stub-pp');
  if (ppEl) ppEl.textContent = `1 person fare (1 seat)`;

  const mode = card.getAttribute('data-mode') || 'train';
  const baseTitle = card.getAttribute('data-base-title') || card.getAttribute('data-transit-title');
  const fullTitle = `${baseTitle} (${classCode})`;
  const arrivalTime = card.getAttribute('data-arrival-time') || '12:00';
  const cat = card.getAttribute('data-category') || 'Transit Option';
  const waypointsJSON = card.getAttribute('data-waypoints') || '';

  // Immediately select this transit option and progressively fill the line to the stay door
  selectSpecificTransit(mode, fullTitle, farePerPerson, arrivalTime, cat, waypointsJSON, classCode);
}

function renderActiveTransitOptions() {
  const container = document.getElementById('transitOptionsList');
  const stepperContainer = document.getElementById('d2dStepperContainer');
  if (!container || !State.transitOptions) return;

  const tab = State.activeTransitTab || 'train';
  const data = State.transitOptions[tab] || {};
  const travelers = State.travelers || 1;
  const roundMultiplier = State.includeReturnBudget ? 2 : 1;
  const stayName = State.selectedStay?.name || `${State.dest} Stay Gate`;
  const isConfirmed = !!(State.transitConfirmed && State.transitDetails?.mode_title);

  let html = '';
  let activeWaypoints = [];
  let activeRouteTitle = '';

  // ──────────────────────────────────────────────────────────────────────────
  // 1. TRAIN TAB (WITH MULTIMODAL GHAT BUS & SHUTTLE CONNECTORS)
  // ──────────────────────────────────────────────────────────────────────────
  if (tab === 'train') {
    const multimodalLegs = data.multimodal_legs || [];
    const schedules = data.schedules || [];

    // A) If multimodal legs exist (e.g. Dharwad -> Kadur Jn -> Kadur Bus Stand -> Kalasa -> Samse)
    if (multimodalLegs.length > 0) {
      const depTime = multimodalLegs[0]?.departure || '20:30';
      if (matchesTransitTimeFilter(depTime)) {
        const baseFare = data.fare_per_traveler || 240;
        const arrivalTime = data.arrival_time || '04:56';
        const baseTitle = `${multimodalLegs[0]?.operator || 'Train'} + Connecting Bus`;
        const selectedClass = State.transitClass || '2S';
        const multimodalTitle = `${baseTitle} (${selectedClass})`;
        const isSelected = isConfirmed && State.transitDetails?.mode === 'train' && State.transitDetails?.mode_title?.startsWith(baseTitle);

        // Build waypoint milestones for the stepper line
        const wp1 = { name: multimodalLegs[0]?.from_point || `${State.source} Station`, time: `Dep ${depTime}`, role: 'Origin Station', icon: '🚉', type: 'origin' };
        const wp2 = { name: multimodalLegs[0]?.to_point?.split('—')[0]?.trim() || 'Kadur Junction', time: `Arr ${multimodalLegs[0]?.arrival || '01:24'}`, role: 'Railway Hub Transfer', icon: '📍', type: 'hub-transfer' };
        const wp3 = { name: multimodalLegs[2]?.from_point || 'Kadur KSRTC Bus Stand', time: `Dep ${multimodalLegs[2]?.departure || '01:51'}`, role: 'Ghat Bus Terminal', icon: '🚏', type: 'bus-stand' };
        const wp4 = { name: multimodalLegs[2]?.to_point || 'Kalasa Bus Stop', time: `Arr ${multimodalLegs[2]?.arrival || '04:21'}`, role: 'Mountain Town Stop', icon: '🛑', type: 'town-stop' };
        const wp5 = { name: `🏡 Doorstep of ${stayName}`, time: `Reaches ${multimodalLegs[3]?.arrival || arrivalTime}`, role: 'Stay Doorstep', icon: '🏡', type: 'stay-gate' };

        const connectors = [
          { type: 'train', label: `🚆 #${multimodalLegs[0]?.train_number || '12658'} (${multimodalLegs[0]?.duration || '4h 54m'})` },
          { type: 'walk', label: `🚶 5m Walk · 27m safe buffer` },
          { type: 'bus', label: `🚌 KSRTC Ghat Bus (${multimodalLegs[2]?.duration || '2h 30m'})` },
          { type: 'shuttle', label: `🚙 Doorstep Link (${multimodalLegs[3]?.duration || '20m'})` }
        ];

        activeWaypoints = [
          { node: wp1, conn: connectors[0] },
          { node: wp2, conn: connectors[1] },
          { node: wp3, conn: connectors[2] },
          { node: wp4, conn: connectors[3] },
          { node: wp5, conn: null }
        ];
        activeRouteTitle = `🚆 Train + 🚌 Ghat Bus + 🚙 Doorstep Shuttle to ${stayName}`;

        const waypointsJSON = encodeURIComponent(JSON.stringify(activeWaypoints));
        const trainClasses = getFullTrainClasses(baseFare, multimodalLegs[0]?.classes_info);
        const activeClassObj = trainClasses.find(c => c.code === selectedClass) || trainClasses[1];
        const activeClassFare = (activeClassObj.fare + 115 + 20) * roundMultiplier;

        html += `
          <div class="d2d-ticket-card ${isSelected ? 'selected-ticket' : ''}" id="card_multimodal_train" data-card-id="card_multimodal_train" data-mode="train" data-base-title="${baseTitle}" data-transit-title="${multimodalTitle}" data-arrival-time="${arrivalTime}" data-category="Multimodal Train + Ghat Bus" data-waypoints="${waypointsJSON}" data-default-text="Select Ticket →" onclick="selectCardClass('card_multimodal_train', '${activeClassObj.code}', ${activeClassFare}, '${activeClassObj.status}', event)">
            <div class="d2d-ticket-main">
              <div class="d2d-ticket-header">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                  <span class="badge bg-primary text-white extra-small"><i class="bi bi-stars me-1"></i>Official Recommended Transit</span>
                  <span class="fw-bold text-body small">🚆 ${multimodalLegs[0]?.operator || 'Superfast Express'} #${multimodalLegs[0]?.train_number || '12658'}</span>
                  <span class="badge bg-success-subtle text-success extra-small fw-bold">★ 4.9 IRCTC Verified</span>
                  <span class="buffer-badge-safe"><i class="bi bi-shield-check me-1"></i>🟢 Safe 27m Platform Buffer</span>
                </div>
                <span class="badge bg-secondary-subtle text-body extra-small">${data.travel_duration || '6h 35m'} Door-to-Door</span>
              </div>

              <!-- Route Flightline / Stepper Summary -->
              <div class="d2d-ticket-flightline my-2">
                <div class="d2d-time-point">
                  <div class="d2d-time-val">${depTime}</div>
                  <div class="d2d-station-val text-truncate">${multimodalLegs[0]?.from_point || State.source}</div>
                </div>

                <div class="d2d-flightpath">
                  <span class="extra-small text-muted mb-1 font-monospace">4 Connected Legs · Direct Transfer Buffer</span>
                  <div class="d2d-flightpath-line"></div>
                  <span class="d2d-flightpath-icon text-muted extra-small">🚆 Station ➔ 🚶 Walk ➔ 🚌 Ghat Bus ➔ 🏡 Stay Door</span>
                </div>

                <div class="d2d-time-point arr">
                  <div class="d2d-time-val text-success">${arrivalTime}</div>
                  <div class="d2d-station-val text-truncate">${stayName}</div>
                </div>
              </div>

              <!-- Available Class Selector Pills & Last-Mile Indicator -->
              <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 pt-2 border-top">
                <div class="d-flex align-items-center gap-1 flex-wrap">
                  <span class="extra-small text-muted me-1 fw-bold">Select Class:</span>
                  <div class="d2d-class-selector-wrap">
                    ${trainClasses.map(c => {
                      const classFare = (c.fare + 115 + 20) * roundMultiplier;
                      const isActive = c.code === activeClassObj.code;
                      return `
                        <button type="button" class="d2d-class-pill ${isActive ? 'active' : ''}" data-class-code="${c.code}" onclick="selectCardClass('card_multimodal_train', '${c.code}', ${classFare}, '${c.status}', event)">
                          <span>${c.code}</span>
                          <span class="pill-fare">₹${classFare}</span>
                          <span class="pill-status status-${c.tag}">${c.status}</span>
                        </button>
                      `;
                    }).join('')}
                  </div>
                </div>
                <span class="last-mile-badge"><i class="bi bi-geo-alt-fill me-1"></i>Last-Mile: ~24 km to ${stayName} (~35m shuttle)</span>
              </div>
            </div>

            <div class="d2d-ticket-divider"></div>

            <!-- Boarding Pass Stub (Strictly 1 Person Fare) -->
            <div class="d2d-ticket-stub">
              <div class="extra-small text-muted text-uppercase fw-bold">1 Person Fare</div>
              <div class="d2d-stub-fare">₹${activeClassFare.toLocaleString('en-IN')}</div>
              <div class="d2d-stub-pp">1 person fare (1 seat)</div>
              <button type="button" class="btn btn-xs ${isSelected ? 'btn-success' : 'btn-outline-primary'} w-100 rounded-pill py-1 fw-bold" onclick="selectCardClass('card_multimodal_train', '${activeClassObj.code}', ${activeClassFare}, '${activeClassObj.status}', event)">
                ${isSelected ? '✓ Confirmed' : 'Select Ticket →'}
              </button>
            </div>
          </div>
        `;
      }
    }

    // B) Additional Express Trains & 2-Train Connecting Alternatives
    schedules.forEach((s, idx) => {
      if (!matchesTransitTimeFilter(s.departure)) return;

      const cardId = `card_train_${idx}`;
      const defaultBtnText = s.is_connecting ? 'Select 2-Train →' : 'Select Train →';
      const baseFare = s.fare_per_seat || 240;
      const trainClasses = getFullTrainClasses(baseFare, s.classes_info);
      const selectedClass = State.transitClass || (s.is_connecting ? 'SL' : '2S');
      const activeClassObj = trainClasses.find(c => c.code === selectedClass) || trainClasses[1];
      const activeClassFare = activeClassObj.fare * roundMultiplier;
      const baseTitle = s.train_name;
      const fullTitle = `${baseTitle} (${activeClassObj.code})`;
      const isScheduleSelected = isConfirmed && State.transitDetails?.mode === 'train' && State.transitDetails?.mode_title?.startsWith(baseTitle);

      let sWaypoints = [];
      if (s.is_connecting && s.connecting_legs && s.connecting_legs.length >= 3) {
        const leg1 = s.connecting_legs[0];
        const layover = s.connecting_legs[1];
        const leg2 = s.connecting_legs[2];

        const w1 = { name: leg1.from_point || s.origin_station, time: `Dep ${leg1.departure}`, role: 'Origin Station', icon: '🚉', type: 'origin' };
        const w2 = { name: leg1.to_point || s.connecting_hub, time: `Arr ${leg1.arrival}`, role: 'Interchange Hub', icon: '📍', type: 'hub-transfer' };
        const w3 = { name: leg2.to_point || s.dest_station, time: `Arr ${leg2.arrival}`, role: 'Destination Station', icon: '🛑', type: 'town-stop' };
        const w4 = { name: `🏡 Doorstep of ${stayName}`, time: `Reaches Stay`, role: 'Stay Doorstep', icon: '🏡', type: 'stay-gate' };

        sWaypoints = [
          { node: w1, conn: { type: 'train', label: `🚆 #${leg1.train_number} (${leg1.duration})` } },
          { node: w2, conn: { type: 'walk', label: `🚶 Transfer (${layover.duration})` } },
          { node: w3, conn: { type: 'shuttle', label: `🚖 Pre-paid Cab to Stay (~1h 15m)` } },
          { node: w4, conn: null }
        ];
      } else {
        const sWp1 = { name: s.origin_station || `${State.source} Station`, time: `Dep ${s.departure}`, role: 'Origin Station', icon: '🚉', type: 'origin' };
        const sWp2 = { name: s.dest_station || `${State.dest} Junction`, time: `Arr ${s.arrival}`, role: 'Destination Station', icon: '📍', type: 'hub-transfer' };
        const sWp3 = { name: `🏡 Doorstep of ${stayName}`, time: `Reaches Gate`, role: 'Stay Doorstep', icon: '🏡', type: 'stay-gate' };
        const sConnectors = [
          { type: 'train', label: `🚆 ${s.train_type || 'Superfast'} (${s.duration})` },
          { type: 'shuttle', label: `🚖 Pre-paid Station Cab (45m)` }
        ];
        sWaypoints = [
          { node: sWp1, conn: sConnectors[0] },
          { node: sWp2, conn: sConnectors[1] },
          { node: sWp3, conn: null }
        ];
      }

      if (activeWaypoints.length === 0) {
        activeWaypoints = sWaypoints;
        activeRouteTitle = `🚆 ${s.train_name} ➔ Doorstep Cab to ${stayName}`;
      }

      const sWaypointsJSON = encodeURIComponent(JSON.stringify(sWaypoints));

      html += `
        <div class="d2d-ticket-card ${isScheduleSelected ? 'selected-ticket' : ''}" id="${cardId}" data-card-id="${cardId}" data-mode="train" data-base-title="${baseTitle}" data-transit-title="${fullTitle}" data-arrival-time="${s.arrival}" data-category="Train Service" data-waypoints="${sWaypointsJSON}" data-default-text="${defaultBtnText}" onclick="selectCardClass('${cardId}', '${activeClassObj.code}', ${activeClassFare}, '${activeClassObj.status}', event)">
          <div class="d2d-ticket-main">
            <div class="d2d-ticket-header">
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="fw-bold text-body small">🚆 ${s.train_name}</span>
                <span class="badge bg-secondary ms-1">#${s.train_number}</span>
                ${s.is_connecting ? `<span class="badge bg-warning text-dark extra-small fw-bold"><i class="bi bi-shuffle me-1"></i>2-Train Route via ${s.connecting_hub?.split('(')[0]?.trim() || 'Interchange'}</span>` : `<span class="badge bg-secondary-subtle text-body extra-small">${s.train_type || 'Daily Express'}</span>`}
                ${s.is_connecting ? '<span class="buffer-badge-safe"><i class="bi bi-clock-history me-1"></i>🟢 Safe 45m Transfer Buffer</span>' : ''}
                ${s.is_overnight ? '<span class="badge bg-purple text-white extra-small" style="background:#7c3aed">🌙 Saves 1 Night Hotel</span>' : ''}
              </div>
              <span class="badge bg-secondary-subtle text-body extra-small">${s.duration}</span>
            </div>

            <div class="d2d-ticket-flightline my-2">
              <div class="d2d-time-point">
                <div class="d2d-time-val">${s.departure}</div>
                <div class="d2d-station-val text-truncate">${s.origin_station || State.source}</div>
              </div>
              <div class="d2d-flightpath">
                <span class="extra-small text-muted mb-1 font-monospace">${s.is_connecting ? '2-Train Hop with Safe Layover' : 'Direct IRCTC Rail Corridor'}</span>
                <div class="d2d-flightpath-line"></div>
                <span class="d2d-flightpath-icon text-muted extra-small">${s.is_connecting ? '🚆 Train 1 ➔ 📍 Interchange ➔ 🚆 Train 2 ➔ 🏡 Stay Door' : '🚆 Railway Track ➔ 🚖 Station Cab ➔ 🏡 Stay Door'}</span>
              </div>
              <div class="d2d-time-point arr">
                <div class="d2d-time-val text-success">${s.arrival}</div>
                <div class="d2d-station-val text-truncate">${s.dest_station || State.dest}</div>
              </div>
            </div>

            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 pt-2 border-top">
              <div class="d-flex align-items-center gap-1 flex-wrap">
                <span class="extra-small text-muted me-1 fw-bold">Select Class:</span>
                <div class="d2d-class-selector-wrap">
                  ${trainClasses.map(c => {
                    const classFare = c.fare * roundMultiplier;
                    const isActive = c.code === activeClassObj.code;
                    return `
                      <button type="button" class="d2d-class-pill ${isActive ? 'active' : ''}" data-class-code="${c.code}" onclick="selectCardClass('${cardId}', '${c.code}', ${classFare}, '${c.status}', event)">
                        <span>${c.code}</span>
                        <span class="pill-fare">₹${classFare}</span>
                        <span class="pill-status status-${c.tag}">${c.status}</span>
                      </button>
                    `;
                  }).join('')}
                </div>
              </div>
              <span class="last-mile-badge"><i class="bi bi-geo-alt-fill me-1"></i>Last-Mile: ~38 km to ${stayName} (~55m cab)</span>
            </div>
          </div>

          <div class="d2d-ticket-divider"></div>

          <div class="d2d-ticket-stub">
            <div class="extra-small text-muted text-uppercase fw-bold">1 Person Fare</div>
            <div class="d2d-stub-fare">₹${activeClassFare.toLocaleString('en-IN')}</div>
            <div class="d2d-stub-pp">1 person fare (1 seat)</div>
            <button type="button" class="btn btn-xs ${isScheduleSelected ? 'btn-success' : 'btn-outline-primary'} w-100 rounded-pill py-1 fw-bold" onclick="selectCardClass('${cardId}', '${activeClassObj.code}', ${activeClassFare}, '${activeClassObj.status}', event)">
              ${isScheduleSelected ? '✓ Confirmed' : defaultBtnText}
            </button>
          </div>
        </div>
      `;
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 2. BUS TAB (STATE RTC & PRIVATE SLEEPER FLEET)
  // ──────────────────────────────────────────────────────────────────────────
  else if (tab === 'bus') {
    const schedules = data.schedules || [];
    schedules.forEach((b, idx) => {
      if (!matchesTransitTimeFilter(b.departure)) return;

      const cardId = `card_bus_${idx}`;
      const baseFare = b.fare_per_seat || 450;
      const busClasses = getBusClasses(baseFare);
      const activeClassObj = busClasses[0];
      const activeClassFare = activeClassObj.fare * roundMultiplier;
      const baseTitle = b.operator;
      const fullTitle = `${baseTitle} (${activeClassObj.code})`;
      const isOvernight = (b.departure.startsWith('21') || b.departure.startsWith('22') || b.departure.startsWith('23') || b.departure.startsWith('20'));
      const isSelected = isConfirmed && State.transitDetails?.mode === 'bus' && State.transitDetails?.mode_title?.startsWith(baseTitle);

      const bWp1 = { name: b.boarding_point || `${State.source} Central Bus Stand`, time: `Dep ${b.departure}`, role: 'Origin Bus Stand', icon: '🚏', type: 'origin' };
      const bWp2 = { name: b.dropoff_point || `${State.dest} KSRTC Main Terminal`, time: `Arr ${b.arrival}`, role: 'Destination Terminal', icon: '🛑', type: 'town-stop' };
      const bWp3 = { name: `🏡 Doorstep of ${stayName}`, time: `Reaches ~20m after`, role: 'Stay Doorstep', icon: '🏡', type: 'stay-gate' };
      const bConnectors = [
        { type: 'bus', label: `🚌 ${b.operator} (${b.duration})` },
        { type: 'shuttle', label: `🛺 Auto / Cab Transfer (20m)` }
      ];
      const bWaypoints = [
        { node: bWp1, conn: bConnectors[0] },
        { node: bWp2, conn: bConnectors[1] },
        { node: bWp3, conn: null }
      ];

      if (activeWaypoints.length === 0) {
        activeWaypoints = bWaypoints;
        activeRouteTitle = `🚌 ${b.operator} ➔ Local Cab to ${stayName}`;
      }

      const bWaypointsJSON = encodeURIComponent(JSON.stringify(bWaypoints));

      html += `
        <div class="d2d-ticket-card ${isSelected ? 'selected-ticket' : ''}" id="${cardId}" data-card-id="${cardId}" data-mode="bus" data-base-title="${baseTitle}" data-transit-title="${fullTitle}" data-arrival-time="${b.arrival}" data-category="Bus Service" data-waypoints="${bWaypointsJSON}" data-default-text="Select Bus →" onclick="selectCardClass('${cardId}', '${activeClassObj.code}', ${activeClassFare}, '${activeClassObj.status}', event)">
          <div class="d2d-ticket-main">
            <div class="d2d-ticket-header">
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="fw-bold text-body small">🚌 ${b.operator}</span>
                <span class="badge bg-warning-subtle text-dark extra-small">★ ${b.rating || '4.6'}</span>
                ${isOvernight ? '<span class="badge bg-purple text-white extra-small" style="background:#7c3aed">🌙 Saves 1 Night Hotel</span>' : ''}
              </div>
              <span class="badge bg-secondary-subtle text-body extra-small">${b.duration}</span>
            </div>

            <div class="d2d-ticket-flightline my-2">
              <div class="d2d-time-point">
                <div class="d2d-time-val">${b.departure}</div>
                <div class="d2d-station-val text-truncate">${b.boarding_point || State.source}</div>
              </div>
              <div class="d2d-flightpath">
                <span class="extra-small text-muted mb-1 font-monospace">Express Highway Corridor</span>
                <div class="d2d-flightpath-line"></div>
                <span class="d2d-flightpath-icon text-muted extra-small">🚌 Highway Bus ➔ 🛺 Resort Auto Link ➔ 🏡 Stay Door</span>
              </div>
              <div class="d2d-time-point arr">
                <div class="d2d-time-val text-success">${b.arrival}</div>
                <div class="d2d-station-val text-truncate">${b.dropoff_point || State.dest}</div>
              </div>
            </div>

            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 pt-2 border-top">
              <div class="d-flex align-items-center gap-1 flex-wrap">
                <span class="extra-small text-muted me-1 fw-bold">Select Bus Type:</span>
                <div class="d2d-class-selector-wrap">
                  ${busClasses.map(c => {
                    const classFare = c.fare * roundMultiplier;
                    const isActive = c.code === activeClassObj.code;
                    return `
                      <button type="button" class="d2d-class-pill ${isActive ? 'active' : ''}" data-class-code="${c.code}" onclick="selectCardClass('${cardId}', '${c.code}', ${classFare}, '${c.status}', event)">
                        <span>${c.code}</span>
                        <span class="pill-fare">₹${classFare}</span>
                        <span class="pill-status status-${c.tag}">${c.status}</span>
                      </button>
                    `;
                  }).join('')}
                </div>
              </div>
              <span class="last-mile-badge"><i class="bi bi-geo-alt-fill me-1"></i>Last-Mile: ~9 km to ${stayName} (~18m auto)</span>
            </div>
          </div>

          <div class="d2d-ticket-divider"></div>

          <div class="d2d-ticket-stub">
            <div class="extra-small text-muted text-uppercase fw-bold">1 Person Fare</div>
            <div class="d2d-stub-fare">₹${activeClassFare.toLocaleString('en-IN')}</div>
            <div class="d2d-stub-pp">1 person fare (1 seat)</div>
            <button type="button" class="btn btn-xs ${isSelected ? 'btn-success' : 'btn-outline-primary'} w-100 rounded-pill py-1 fw-bold" onclick="selectCardClass('${cardId}', '${activeClassObj.code}', ${activeClassFare}, '${activeClassObj.status}', event)">
              ${isSelected ? '✓ Confirmed' : 'Select Bus →'}
            </button>
          </div>
        </div>
      `;
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 3. DRIVE & CABS TAB
  // ──────────────────────────────────────────────────────────────────────────
  else if (tab === 'car') {
    const schedules = data.schedules || [];
    schedules.forEach((c, idx) => {
      const cardId = `card_car_${idx}`;
      const totalVehicleFare = (c.fare_per_seat || 2406) * roundMultiplier;
      const cFarePerPerson = Math.round(totalVehicleFare / Math.max(1, travelers));
      const baseTitle = c.operator;
      const isSelected = isConfirmed && State.transitDetails?.mode === 'car' && State.transitDetails?.mode_title?.startsWith(baseTitle);

      const cWp1 = { name: `${State.source} Doorstep`, time: `Dep 06:00 AM`, role: 'Home Pickup', icon: '🏠', type: 'origin' };
      const cWp2 = { name: 'Scenic Mountain Highway', time: `En Route (~${data.distance_km || 318} km)`, role: 'National Highway', icon: '🛣️', type: 'hub-transfer' };
      const cWp3 = { name: `🏡 Doorstep of ${stayName}`, time: `Arr ~12:30 PM`, role: 'Resort Portico', icon: '🏡', type: 'stay-gate' };
      const cConnectors = [
        { type: 'shuttle', label: `🚗 Highway & Ghats (${c.duration || '6h 30m'})` },
        { type: 'shuttle', label: `🚗 Direct Doorstep Entry` }
      ];
      const cWaypoints = [
        { node: cWp1, conn: cConnectors[0] },
        { node: cWp2, conn: cConnectors[1] },
        { node: cWp3, conn: null }
      ];

      if (activeWaypoints.length === 0) {
        activeWaypoints = cWaypoints;
        activeRouteTitle = `🚗 Doorstep Pickup ➔ Direct Resort Drop at ${stayName}`;
      }

      const cWaypointsJSON = encodeURIComponent(JSON.stringify(cWaypoints));

      html += `
        <div class="d2d-ticket-card ${isSelected ? 'selected-ticket' : ''}" id="${cardId}" data-card-id="${cardId}" data-mode="car" data-base-title="${baseTitle}" data-transit-title="${baseTitle}" data-arrival-time="${c.arrival || '12:30'}" data-category="Driving / Cab" data-waypoints="${cWaypointsJSON}" data-default-text="Select Cab →" onclick="selectSpecificTransit('car', '${baseTitle}', ${cFarePerPerson}, '${c.arrival || '12:30'}', 'Driving / Cab', '${cWaypointsJSON}')">
          <div class="d2d-ticket-main">
            <div class="d2d-ticket-header">
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="fw-bold text-body small">🚗 ${c.operator}</span>
                <span class="badge bg-secondary-subtle text-body extra-small">${c.vehicle_model || c.type}</span>
                <span class="badge bg-success-subtle text-success extra-small fw-bold">Zero Transfers · Direct Doorstep Drop</span>
              </div>
              <span class="badge bg-secondary-subtle text-body extra-small">${c.duration || '6h 30m'}</span>
            </div>

            <div class="d2d-ticket-flightline my-2">
              <div class="d2d-time-point">
                <div class="d2d-time-val">Doorstep</div>
                <div class="d2d-station-val text-truncate">${State.source} (Home Pickup)</div>
              </div>
              <div class="d2d-flightpath">
                <span class="extra-small text-muted mb-1 font-monospace">${data.distance_km || 318} km via National Highway</span>
                <div class="d2d-flightpath-line"></div>
                <span class="d2d-flightpath-icon text-muted extra-small">🚗 City Corridor ➔ 🛣️ Scenic Ghat Pass ➔ 🏡 Stay Door</span>
              </div>
              <div class="d2d-time-point arr">
                <div class="d2d-time-val text-success">Doorstep</div>
                <div class="d2d-station-val text-truncate">${stayName} Portico</div>
              </div>
            </div>

            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 pt-2 border-top">
              <div class="extra-small text-muted">${c.details || `Includes Fuel & NHAI Fastag Tolls • AC Vehicle`}</div>
              <span class="last-mile-badge"><i class="bi bi-geo-alt-fill me-1"></i>0 km Last-Mile (Drops at Stay Porch)</span>
            </div>
          </div>

          <div class="d2d-ticket-divider"></div>

          <div class="d2d-ticket-stub">
            <div class="extra-small text-muted text-uppercase fw-bold">1 Person Cost</div>
            <div class="d2d-stub-fare">₹${cFarePerPerson.toLocaleString('en-IN')}</div>
            <div class="d2d-stub-pp">per traveler (split of car)</div>
            <button type="button" class="btn btn-xs ${isSelected ? 'btn-success' : 'btn-outline-primary'} w-100 rounded-pill py-1 fw-bold" onclick="selectSpecificTransit('car', '${baseTitle}', ${cFarePerPerson}, '${c.arrival || '12:30'}', 'Driving / Cab', '${cWaypointsJSON}')">
              ${isSelected ? '✓ Confirmed' : 'Select Cab →'}
            </button>
          </div>
        </div>
      `;
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 4. FLIGHT TAB
  // ──────────────────────────────────────────────────────────────────────────
  else if (tab === 'flight') {
    const schedules = data.schedules || [];
    schedules.forEach((fl, idx) => {
      if (!matchesTransitTimeFilter(fl.departure)) return;

      const cardId = `card_fl_${idx}`;
      const baseFare = fl.price_per_seat || 4200;
      const flightClasses = getFlightClasses(baseFare);
      const activeClassObj = flightClasses[0];
      const activeClassFare = activeClassObj.fare * roundMultiplier;
      const baseTitle = fl.airline;
      const fullTitle = `${baseTitle} (${activeClassObj.code})`;
      const isSelected = isConfirmed && State.transitDetails?.mode === 'flight' && State.transitDetails?.mode_title?.startsWith(baseTitle);

      const flWp1 = { name: data.departure_airport || `${State.source} Airport`, time: `Dep ${fl.departure}`, role: 'Origin Airport', icon: '🛫', type: 'origin' };
      const flWp2 = { name: data.arrival_airport || `Hub Airport`, time: `Lands ${fl.arrival}`, role: 'Landing Hub', icon: '🛬', type: 'hub-transfer' };
      const flWp3 = { name: `🏡 Doorstep of ${stayName}`, time: `Reaches ~2.5h after`, role: 'Stay Doorstep', icon: '🏡', type: 'stay-gate' };
      const flConnectors = [
        { type: 'train', label: `✈️ ${fl.airline} (${fl.type})` },
        { type: 'shuttle', label: `🚖 Pre-paid Ghat Cab (2h 30m)` }
      ];
      const flWaypoints = [
        { node: flWp1, conn: flConnectors[0] },
        { node: flWp2, conn: flConnectors[1] },
        { node: flWp3, conn: null }
      ];

      if (activeWaypoints.length === 0) {
        activeWaypoints = flWaypoints;
        activeRouteTitle = `✈️ ${fl.airline} ➔ Highway Cab to ${stayName}`;
      }

      const flWaypointsJSON = encodeURIComponent(JSON.stringify(flWaypoints));

      html += `
        <div class="d2d-ticket-card ${isSelected ? 'selected-ticket' : ''}" id="${cardId}" data-card-id="${cardId}" data-mode="flight" data-base-title="${baseTitle}" data-transit-title="${fullTitle}" data-arrival-time="${fl.arrival}" data-category="Flight Option" data-waypoints="${flWaypointsJSON}" data-default-text="Select Flight →" onclick="selectCardClass('${cardId}', '${activeClassObj.code}', ${activeClassFare}, '${activeClassObj.status}', event)">
          <div class="d2d-ticket-main">
            <div class="d2d-ticket-header">
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="fw-bold text-body small">✈️ ${fl.airline} (${fl.type})</span>
                <span class="badge bg-secondary-subtle text-body extra-small">${fl.baggage || 'Cabin 7kg + Check-in 15kg'}</span>
              </div>
              <span class="badge bg-secondary-subtle text-body extra-small">Fast Transit</span>
            </div>

            <div class="d2d-ticket-flightline my-2">
              <div class="d2d-time-point">
                <div class="d2d-time-val">${fl.departure}</div>
                <div class="d2d-station-val text-truncate">${data.departure_airport || State.source}</div>
              </div>
              <div class="d2d-flightpath">
                <span class="extra-small text-muted mb-1 font-monospace">Air Corridor + Mountain Cab</span>
                <div class="d2d-flightpath-line"></div>
                <span class="d2d-flightpath-icon text-muted extra-small">🛫 Flight ➔ 🚖 Pre-paid Cab ➔ 🏡 Stay Door</span>
              </div>
              <div class="d2d-time-point arr">
                <div class="d2d-time-val text-success">${fl.arrival}</div>
                <div class="d2d-station-val text-truncate">${data.arrival_airport || State.dest}</div>
              </div>
            </div>

            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 pt-2 border-top">
              <div class="d-flex align-items-center gap-1 flex-wrap">
                <span class="extra-small text-muted me-1 fw-bold">Select Flight Class:</span>
                <div class="d2d-class-selector-wrap">
                  ${flightClasses.map(c => {
                    const classFare = c.fare * roundMultiplier;
                    const isActive = c.code === activeClassObj.code;
                    return `
                      <button type="button" class="d2d-class-pill ${isActive ? 'active' : ''}" data-class-code="${c.code}" onclick="selectCardClass('${cardId}', '${c.code}', ${classFare}, '${c.status}', event)">
                        <span>${c.code}</span>
                        <span class="pill-fare">₹${classFare}</span>
                        <span class="pill-status status-${c.tag}">${c.status}</span>
                      </button>
                    `;
                  }).join('')}
                </div>
              </div>
              <span class="last-mile-badge"><i class="bi bi-geo-alt-fill me-1"></i>Last-Mile: ~92 km to ${stayName} (~2h cab)</span>
            </div>
          </div>

          <div class="d2d-ticket-divider"></div>

          <div class="d2d-ticket-stub">
            <div class="extra-small text-muted text-uppercase fw-bold">1 Person Fare</div>
            <div class="d2d-stub-fare">₹${activeClassFare.toLocaleString('en-IN')}</div>
            <div class="d2d-stub-pp">1 person fare (1 seat)</div>
            <button type="button" class="btn btn-xs ${isSelected ? 'btn-success' : 'btn-outline-primary'} w-100 rounded-pill py-1 fw-bold" onclick="selectCardClass('${cardId}', '${activeClassObj.code}', ${activeClassFare}, '${activeClassObj.status}', event)">
              ${isSelected ? '✓ Confirmed' : 'Select Flight →'}
            </button>
          </div>
        </div>
      `;
    });
  }

  // Render the Progressive Stepper Line above cards
  if (stepperContainer && activeWaypoints.length > 0) {
    renderDoorToDoorStepper(activeWaypoints, activeRouteTitle, isConfirmed);
  }

  if (!html) {
    html = `
      <div class="text-center py-5 border rounded-3 bg-light">
        <i class="bi bi-clock-history fs-2 text-muted mb-2 d-block"></i>
        <h6 class="fw-bold text-body">No schedules found for this departure window</h6>
        <p class="text-muted small mb-3">Try switching to <strong>All Times</strong> or another transit tab.</p>
        <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" onclick="filterTransitByTime('all')">Show All Times</button>
      </div>
    `;
  }

  container.innerHTML = html;
}

/**
 * Renders the Visual Door-to-Door Waypoint Stepper Track
 * If not confirmed: Shows pending dashed track from origin to stay door
 * If confirmed: Progressively fills glowing animated stream all the way to stay door!
 */
function renderDoorToDoorStepper(waypoints, title, isConfirmed) {
  const container = document.getElementById('d2dStepperContainer');
  if (!container || !waypoints || waypoints.length === 0) return;

  const stayName = State.selectedStay?.name || `${State.dest} Stay`;
  let trackHTML = '';

  if (!isConfirmed) {
    // Initial State: Line is NOT directly filled!
    // Origin is ready, remaining connectors & milestones are pending until user selects mode/class below
    waypoints.forEach((item, idx) => {
      const isOrigin = (idx === 0);
      const isStayDoor = (idx === waypoints.length - 1);
      const node = item.node;
      const conn = item.conn;

      trackHTML += `
        <!-- Waypoint Node ${idx + 1} -->
        <div class="d2d-node ${isOrigin ? 'origin' : 'pending'} ${isStayDoor ? 'stay-gate' : ''}">
          <div class="d2d-node-icon">${isOrigin ? (node.icon || '🏠') : (isStayDoor ? '🚪' : '⏳')}</div>
          <div class="d2d-node-name" title="${node.name}">${isOrigin ? node.name : (isStayDoor ? `Doorstep of ${stayName}` : node.role)}</div>
          <div class="d2d-node-role">${isOrigin ? '● Origin Ready' : (isStayDoor ? 'Destination Doorstep' : 'Awaiting Selection')}</div>
          <div class="d2d-node-time">${isOrigin ? node.time : '--:--'}</div>
        </div>
      `;

      if (conn) {
        trackHTML += `
          <div class="d2d-connector pending">
            <span class="d2d-leg-pill">${isOrigin ? '👇 Choose Mode & Class Below' : 'Awaiting Link'}</span>
            <div class="d2d-connector-line"></div>
          </div>
        `;
      }
    });

    container.innerHTML = `
      <div class="d2d-stepper-card is-pending">
        <div class="d2d-stepper-header">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <span class="badge bg-secondary-subtle text-secondary fw-bold extra-small"><i class="bi bi-clock-history me-1"></i> Pathway Pending</span>
            <span class="fw-bold text-body small">Select your transit mode & class below to connect the pathway directly to the door of your stay</span>
          </div>
          <span class="badge bg-warning-subtle text-warning extra-small fw-bold">
            <i class="bi bi-arrow-down-circle me-1"></i>Select Ticket to Complete Line
          </span>
        </div>
        <div class="d2d-track-row">
          ${trackHTML}
        </div>
      </div>
    `;
  } else {
    // Confirmed / Selected State: Filled Glowing Stream to Stay Door
    waypoints.forEach((item, idx) => {
      const isStayDoor = (idx === waypoints.length - 1);
      const node = item.node;
      const conn = item.conn;

      trackHTML += `
        <!-- Waypoint Node ${idx + 1} -->
        <div class="d2d-node ${node.type} ${isStayDoor ? 'stay-gate doorstep-active' : ''}">
          <div class="d2d-node-icon">${node.icon}</div>
          <div class="d2d-node-name" title="${node.name}">${node.name}</div>
          <div class="d2d-node-role">${isStayDoor ? '✓ Reached Doorstep' : node.role}</div>
          <div class="d2d-node-time">${node.time}</div>
        </div>
      `;

      if (conn) {
        trackHTML += `
          <div class="d2d-connector filled ${conn.type}">
            <span class="d2d-leg-pill">${conn.label}</span>
            <div class="d2d-connector-line"></div>
          </div>
        `;
      }
    });

    container.innerHTML = `
      <div class="d2d-stepper-card is-connected">
        <div class="d2d-stepper-header">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <span class="badge bg-teal text-white fw-bold extra-small" style="background:#008779;"><i class="bi bi-geo-alt-fill me-1"></i> Door-to-Door Transfer Route</span>
            <span class="fw-bold text-body small">${title || 'Active Journey'}</span>
          </div>
          <span class="badge bg-success-subtle text-success extra-small fw-bold">
            <i class="bi bi-check2-circle me-1"></i>✓ 100% Connected Doorstep Route
          </span>
        </div>
        <div class="d2d-track-row">
          ${trackHTML}
        </div>
      </div>
    `;
  }
}

function selectSpecificTransit(mode, title, singlePersonFare, arrivalTime, detailsSummary, waypointsEncoded, selectedClass) {
  State.transitConfirmed = true;
  State.transitMode = mode;
  State.transitCostPerPerson = Math.round(singlePersonFare);
  const trav = Math.max(1, State.travelers || 1);
  State.transitCost = State.transitCostPerPerson * trav;
  State.arrivalTime = arrivalTime || '12:00';
  if (selectedClass) State.transitClass = selectedClass;

  State.transitDetails = {
    mode: mode,
    mode_title: title,
    selected_class: selectedClass || State.transitClass || '',
    total_cost: State.transitCost,
    cost_per_person: State.transitCostPerPerson,
    arrival_time: arrivalTime,
    details_summary: detailsSummary
  };

  let waypoints = [];
  if (waypointsEncoded) {
    try {
      waypoints = JSON.parse(decodeURIComponent(waypointsEncoded));
      State.transitWaypoints = waypoints;
    } catch (e) {
      console.warn('Could not parse waypoints:', e);
    }
  }

  // Overnight transit notification
  const isNight = (arrivalTime.startsWith('04:') || arrivalTime.startsWith('05:') || arrivalTime.startsWith('06:') || arrivalTime.startsWith('07:'));
  if (isNight) {
    showToast(`🌙 Overnight route selected! Saved 1 night hotel expense`, 'success');
  } else {
    showToast(`🚆 Route confirmed: ${title}!`, 'success');
  }

  // Update selected banner in Step 1
  const bannerName = document.getElementById('transitActiveName');
  const bannerSum  = document.getElementById('transitActiveSummary');
  const costEl     = document.getElementById('transitCost');
  const costPp     = document.getElementById('transitCostPerPerson');

  if (bannerName) bannerName.innerHTML = `<i class="bi bi-check-circle-fill text-success me-1"></i> ${title}`;
  if (bannerSum)  bannerSum.textContent = `Reaches @ ${arrivalTime} directly at ${State.selectedStay?.name || State.dest}`;
  if (costEl)     costEl.textContent = `₹${State.transitCostPerPerson.toLocaleString('en-IN')}`;
  if (costPp)     costPp.textContent = `(1 seat / traveler)`;

  // Update Stage 2 Sidebar & Preview Card
  const tTrName = document.getElementById('tSummaryTransitName');
  const tTrCost = document.getElementById('tSummaryTransitCost');
  if (tTrName) tTrName.textContent = title;
  if (tTrCost) tTrCost.textContent = `₹${State.transitCostPerPerson.toLocaleString('en-IN')} / person (₹${State.transitCost.toLocaleString('en-IN')} group)`;

  // Update Transfer Milestones in Right Panel
  const tLegs = document.getElementById('tSummaryLegsList');
  if (tLegs && waypoints.length > 0) {
    tLegs.innerHTML = `
      <div class="d-flex flex-column gap-2 py-1">
        ${waypoints.map((item, i) => `
          <div class="d-flex justify-content-between align-items-center">
            <span class="text-white small fw-bold">${item.node.icon} ${item.node.name}</span>
            <span class="text-turquoise extra-small fw-bold">${item.node.time}</span>
          </div>
          ${item.conn ? `<div class="extra-small text-white-50 ps-3" style="font-size:0.65rem;">↳ ${item.conn.label}</div>` : ''}
        `).join('')}
      </div>
    `;
  }

  // Progressively fill the line to the door of the stay with animated sequence!
  if (waypoints.length > 0) {
    renderDoorToDoorStepper(waypoints, title, true);

    // Staggered progressive animation from Origin until Door of Stay
    const connectors = document.querySelectorAll('#d2dStepperContainer .d2d-connector');
    const nodes = document.querySelectorAll('#d2dStepperContainer .d2d-node');
    connectors.forEach((c, idx) => {
      c.classList.remove('filled');
      c.classList.add('pending');
      setTimeout(() => {
        c.classList.remove('pending');
        c.classList.add('filled');
      }, (idx + 1) * 140);
    });
    nodes.forEach((n, idx) => {
      if (idx > 0) {
        n.classList.add('pending');
        setTimeout(() => {
          n.classList.remove('pending');
          if (idx === nodes.length - 1) {
            n.classList.add('doorstep-active');
            const stayName = State.selectedStay?.name || `${State.dest} Stay`;
            showToast(`🏡 Pathway fully connected to the door of ${stayName}!`, 'success');
          }
        }, (idx + 1) * 150);
      }
    });
  }

  // Mutually exclusive transit selection: Reset other cards
  document.querySelectorAll('.d2d-ticket-card').forEach(card => {
    card.classList.remove('selected-ticket');
    const btn = card.querySelector('.d2d-ticket-stub button');
    if (btn) {
      btn.classList.remove('btn-success');
      btn.classList.add('btn-outline-primary');
      const defaultText = card.getAttribute('data-default-text') || 'Select Ticket →';
      btn.textContent = defaultText;
    }
  });

  // Highlight ONLY the chosen transit card
  let targetCard = null;
  const cards = document.querySelectorAll('.d2d-ticket-card');
  for (const c of cards) {
    const cardTitle = c.getAttribute('data-transit-title') || '';
    const baseTitle = c.getAttribute('data-base-title') || '';
    if (cardTitle === title || (baseTitle && title.startsWith(baseTitle))) {
      targetCard = c;
      break;
    }
  }
  if (!targetCard && window.event) {
    targetCard = window.event.target.closest('.d2d-ticket-card');
  }

  if (targetCard) {
    targetCard.classList.add('selected-ticket');
    const btn = targetCard.querySelector('.d2d-ticket-stub button');
    if (btn) {
      btn.classList.remove('btn-outline-primary');
      btn.classList.add('btn-success');
      btn.textContent = '✓ Confirmed';
    }
  }

  const pcTr = document.getElementById('pc_transport');
  const pcArr = document.getElementById('pc_arrival');
  if (pcTr) pcTr.textContent = title;
  if (pcArr) pcArr.textContent = `Arrival: ${arrivalTime}`;

  updatePreviewCard();
  saveStateToLS();
}

async function saveCustomWizardTripDirectly() {
  if (!State.dest) {
    showToast('⚠️ Please complete Journey Details first', 'warning');
    return;
  }

  if (window.PlanetRunner && window.PlanetRunner.showModal) {
    window.PlanetRunner.showModal(
      `Saving ${State.dest} Itinerary to Dashboard...`,
      State.dest,
      "Assembling base camps, transit reservations & curated sights into your permanent dossier"
    );
  }

  showToast('💾 Saving custom itinerary directly to your dashboard…', 'info');

  const payload = {
    destination: State.dest,
    source: State.source || 'Bengaluru',
    start_date: document.getElementById('w_travel_date')?.value || '',
    end_date: document.getElementById('w_return_date')?.value || '',
    num_days: State.days,
    num_travelers: State.travelers,
    budget: State.budget,
    travel_style: State.style.toLowerCase(),
    transport: State.transport,
    transit_mode: State.transitMode || State.transport,
    transit_cost: State.transitCost || 0,
    arrival_time: State.arrivalTime || '10:00',
    transit_details: State.transitDetails || {},
    selected_stay: State.selectedStay || {},
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
      }, 700);
    } else {
      if (window.PlanetRunner && window.PlanetRunner.hideModal) window.PlanetRunner.hideModal();
      showToast(`❌ Save failed: ${result.error}`, 'danger');
    }
  } catch (error) {
    if (window.PlanetRunner && window.PlanetRunner.hideModal) window.PlanetRunner.hideModal();
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
