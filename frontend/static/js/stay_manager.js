/**
 * Yatrika Stay Manager — Interactive Map & Real-time AI Hotel Discovery
 */

let stayMap = null;
let currentStayData = null;
let hotelMarkers = [];
let destMarker = null;
let activePurpose = 'all';

document.addEventListener('DOMContentLoaded', () => {
  // 1. Load initial embedded server state
  try {
    const rawDataEl = document.getElementById('serverStayData');
    if (rawDataEl && rawDataEl.textContent.trim()) {
      currentStayData = JSON.parse(rawDataEl.textContent);
    }
  } catch (err) {
    console.warn('[StayManager] Failed to parse embedded server data:', err);
  }

  // 2. Initialize interactive MapLibre map
  initStayMap();
});

function initStayMap() {
  const mapContainer = document.getElementById('stayMap');
  if (!mapContainer) return;

  const initialLat = currentStayData?.dest_coords?.lat || 12.3375;
  const initialLon = currentStayData?.dest_coords?.lon || 75.8069;

  stayMap = new maplibregl.Map({
    container: 'stayMap',
    style: {
      version: 8,
      sources: {
        'osm-tiles': {
          type: 'raster',
          tiles: [
            'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
          ],
          tileSize: 256,
          attribution: '&copy; OpenStreetMap contributors'
        }
      },
      layers: [
        {
          id: 'osm-tiles-layer',
          type: 'raster',
          source: 'osm-tiles',
          minzoom: 0,
          maxzoom: 19
        }
      ]
    },
    center: [initialLon, initialLat],
    zoom: 12
  });

  stayMap.addControl(new maplibregl.NavigationControl(), 'top-right');

  stayMap.on('load', () => {
    // Add GeoJSON line source & layer for OSRM road connection
    stayMap.addSource('stay-road-route', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] }
    });

    stayMap.addLayer({
      id: 'stay-road-route-casing',
      type: 'line',
      source: 'stay-road-route',
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: { 'line-color': '#0f172a', 'line-width': 6, 'line-opacity': 0.8 }
    });

    stayMap.addLayer({
      id: 'stay-road-route-line',
      type: 'line',
      source: 'stay-road-route',
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: { 'line-color': '#0284c7', 'line-width': 4 }
    });

    if (currentStayData) {
      renderMapMarkers(currentStayData);
    }
  });
}

function renderMapMarkers(data) {
  if (!stayMap) return;

  // Clear existing hotel markers
  hotelMarkers.forEach(m => m.remove());
  hotelMarkers = [];
  if (destMarker) {
    destMarker.remove();
    destMarker = null;
  }

  const destLat = data.dest_coords?.lat;
  const destLon = data.dest_coords?.lon;

  // 1. Add Destination / Work Pin
  if (destLat && destLon) {
    const destEl = document.createElement('div');
    destEl.className = 'custom-dest-pin';
    destEl.innerHTML = '★';
    destEl.title = `Destination: ${data.destination}`;

    destMarker = new maplibregl.Marker({ element: destEl })
      .setLngLat([destLon, destLat])
      .setPopup(new maplibregl.Popup({ offset: 15 }).setHTML(`
        <div class="p-1">
          <div class="fw-bold extra-small text-coral">📍 Target Anchor</div>
          <div class="small fw-semibold text-navy">${data.destination}</div>
        </div>
      `))
      .addTo(stayMap);
  }

  // 2. Add Hotel Markers
  const bounds = new maplibregl.LngLatBounds();
  if (destLat && destLon) {
    bounds.extend([destLon, destLat]);
  }

  const stays = data.stays || [];
  stays.forEach(s => {
    if (!s.lat || !s.lon) return;

    const pinEl = document.createElement('div');
    pinEl.className = 'custom-hotel-pin';
    pinEl.id = `marker_${s.id}`;
    pinEl.innerHTML = `₹${s.price_per_night.toLocaleString('en-IN')}`;

    pinEl.addEventListener('click', (e) => {
      e.stopPropagation();
      focusStayOnMap(s.id, s.lat, s.lon, s.name, s.price_per_night, s.img, s.distance_km, s.drive_mins);
    });

    const marker = new maplibregl.Marker({ element: pinEl })
      .setLngLat([s.lon, s.lat])
      .addTo(stayMap);

    hotelMarkers.push(marker);
    bounds.extend([s.lon, s.lat]);
  });

  if (stays.length > 0 && !bounds.isEmpty()) {
    stayMap.fitBounds(bounds, { padding: 50, maxZoom: 14 });
  }
}

async function focusStayOnMap(stayId, lat, lon, name, price, img, distKm, driveMins) {
  if (!stayMap) return;

  // 1. Highlight Card in Left Pane
  document.querySelectorAll('.stay-card').forEach(c => c.classList.remove('active-selected'));
  const targetCard = document.getElementById(`card_${stayId}`);
  if (targetCard) {
    targetCard.classList.add('active-selected');
    targetCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // 2. Highlight Pin on Map
  document.querySelectorAll('.custom-hotel-pin').forEach(p => p.classList.remove('active-pin'));
  const targetPin = document.getElementById(`marker_${stayId}`);
  if (targetPin) {
    targetPin.classList.add('active-pin');
  }

  // 3. Smooth Camera Fly-To
  stayMap.flyTo({
    center: [lon, lat],
    zoom: 14.5,
    duration: 1000
  });

  // 4. Open MapLibre Popup
  new maplibregl.Popup({ offset: 20 })
    .setLngLat([lon, lat])
    .setHTML(`
      <div style="max-width: 200px; padding: 2px;">
        <img src="${img}" style="width: 100%; height: 90px; object-fit: cover; border-radius: 6px; margin-bottom: 6px;" />
        <div class="fw-bold small text-navy leading-tight mb-1">${name}</div>
        <div class="d-flex justify-content-between align-items-center extra-small text-muted mb-1">
          <span class="fw-bold text-success">₹${Number(price).toLocaleString('en-IN')}/nt</span>
          <span>📍 ${distKm} km</span>
        </div>
        <div class="extra-small text-turquoise fw-semibold">🚗 ~${driveMins} mins to destination</div>
      </div>
    `)
    .addTo(stayMap);

  // 5. Fetch & Render OSRM Road Route to Destination
  const destLat = currentStayData?.dest_coords?.lat;
  const destLon = currentStayData?.dest_coords?.lon;

  if (destLat && destLon) {
    try {
      const resp = await fetch('/stay-manager/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stay_lat: lat,
          stay_lon: lon,
          dest_lat: destLat,
          dest_lon: destLon
        })
      });
      const routeData = await resp.json();
      if (routeData.success && routeData.geometry) {
        stayMap.getSource('stay-road-route').setData({
          type: 'Feature',
          geometry: routeData.geometry
        });

        // Show Road Circuit Badge
        const summaryChip = document.getElementById('mapRouteSummaryChip');
        if (summaryChip) {
          summaryChip.classList.remove('d-none');
          document.getElementById('mapRouteTitle').textContent = `${name} ➔ ${currentStayData.destination}`;
          document.getElementById('mapRouteDetails').textContent = `🛣️ ${routeData.distance_km} km • ~${routeData.duration_mins} mins road drive`;
        }
      }
    } catch (e) {
      console.warn('[StayManager] Failed to fetch road route:', e);
    }
  }
}

async function handleStaySearch(event) {
  event.preventDefault();

  const source = document.getElementById('staySourceInput')?.value.trim() || '';
  const destination = document.getElementById('stayDestInput')?.value.trim() || 'Coorg';
  const checkin = document.getElementById('stayCheckinInput')?.value.trim() || '';
  const checkout = document.getElementById('stayCheckoutInput')?.value.trim() || '';
  const budget = document.getElementById('stayBudgetInput')?.value.trim() || '2500';
  const travelers = document.getElementById('stayTravelersInput')?.value || '2';

  const btn = document.getElementById('staySearchBtn');
  const btnText = btn?.querySelector('.btn-text');
  const spinner = btn?.querySelector('.spinner-border');

  if (btn) btn.disabled = true;
  if (btnText) btnText.classList.add('d-none');
  if (spinner) spinner.classList.remove('d-none');

  try {
    const queryParams = new URLSearchParams({
      source,
      destination,
      checkin,
      checkout,
      budget,
      travelers,
      purpose: activePurpose
    });

    const response = await fetch(`/stay-manager/api/search?${queryParams.toString()}`);
    const data = await response.json();

    if (data && data.stays) {
      currentStayData = data;
      renderStayCards(data);
      renderMapMarkers(data);

      // Update AI Engine badge
      const badge = document.getElementById('aiEngineStatusBadge');
      if (badge) {
        if (data.source_engine === 'ibm_granite') {
          badge.innerHTML = `<i class="bi bi-cpu-fill text-turquoise me-1"></i> IBM Granite 4-h-small Active`;
        } else {
          badge.innerHTML = `<i class="bi bi-shield-check text-success me-1"></i> Agent 4 Accommodations Active`;
        }
      }

      // Update results count
      const countLabel = document.getElementById('resultsCountLabel');
      if (countLabel) {
        countLabel.textContent = `${data.stays.length} Stays Near ${data.destination}`;
      }
    }
  } catch (err) {
    console.error('[StayManager] Search error:', err);
  } finally {
    if (btn) btn.disabled = false;
    if (btnText) btnText.classList.remove('d-none');
    if (spinner) spinner.classList.add('d-none');
  }
}

function renderStayCards(data) {
  const container = document.getElementById('stayCardsContainer');
  if (!container) return;

  if (!data.stays || data.stays.length === 0) {
    container.innerHTML = `
      <div class="text-center py-5 bg-white rounded-3 border border-secondary-subtle">
        <i class="bi bi-house-slash fs-2 text-warning mb-2 d-block"></i>
        <div class="fw-bold text-navy">No stays found near ${data.destination}</div>
        <div class="extra-small text-muted">Try adjusting your budget or search radius</div>
      </div>
    `;
    return;
  }

  container.innerHTML = data.stays.map(s => `
    <article class="stay-card" id="card_${s.id}" data-id="${s.id}" data-lat="${s.lat}" data-lon="${s.lon}" data-price="${s.price_per_night}" data-dist="${s.distance_km}" data-rating="${s.rating}">
      <div class="stay-card-thumb-wrap">
        <img src="${s.img}" alt="${s.name}" class="stay-card-thumb" loading="lazy" />
        <span class="stay-thumb-badge">${s.type}</span>
        <span class="stay-thumb-rating">★ ${s.rating}</span>
      </div>

      <div class="stay-card-content">
        <div class="d-flex justify-content-between align-items-start gap-2">
          <h2 class="stay-title text-navy mb-1" title="${s.name}">${s.name}</h2>
          <div class="text-end text-nowrap">
            <span class="stay-price-amount">₹${s.price_per_night.toLocaleString('en-IN')}</span>
            <span class="stay-price-sub">/ nt</span>
          </div>
        </div>

        <div class="stay-distance-line">
          <i class="bi bi-geo-alt-fill text-turquoise me-1"></i>
          <span>${s.distance_km} km to destination (~${s.drive_mins} mins drive)</span>
        </div>

        <p class="stay-address text-muted mb-2">${s.address}</p>

        <div class="d-flex flex-wrap gap-1 mb-2">
          ${(s.amenities || []).map(a => `<span class="stay-amenity-chip">${a}</span>`).join('')}
        </div>

        <div class="stay-card-footer pt-2 border-top d-flex align-items-center justify-content-between gap-2">
          <button type="button" class="btn btn-sm btn-outline-primary btn-map-view py-1 px-2 extra-small fw-semibold"
                  onclick="focusStayOnMap('${s.id}', ${s.lat}, ${s.lon}, '${escapeHtml(s.name)}', '${s.price_per_night}', '${s.img}', '${s.distance_km}', '${s.drive_mins}')">
            <i class="bi bi-map-fill me-1"></i>View on Map
          </button>

          <div class="d-flex align-items-center gap-1">
            <a href="${s.booking_links.agoda}" target="_blank" rel="noopener noreferrer"
               class="btn btn-sm btn-light border py-1 px-2 extra-small text-dark fw-semibold" title="Compare on Agoda">
              Agoda ↗
            </a>
            <a href="${s.booking_links.booking_com}" target="_blank" rel="noopener noreferrer"
               class="btn btn-sm btn-success py-1 px-2 extra-small text-white fw-semibold" title="Book on Booking.com">
              Book ↗
            </a>
          </div>
        </div>
      </div>
    </article>
  `).join('');
}

function selectPurpose(purpose, btnEl) {
  activePurpose = purpose;
  document.querySelectorAll('.btn-purpose-pill').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  const form = document.getElementById('staySearchForm');
  if (form) handleStaySearch(new Event('submit'));
}

function quickFillDest(dest) {
  const destInput = document.getElementById('stayDestInput');
  if (destInput) {
    destInput.value = dest;
    const form = document.getElementById('staySearchForm');
    if (form) handleStaySearch(new Event('submit'));
  }
}

function sortStayCards(criterion) {
  const container = document.getElementById('stayCardsContainer');
  if (!container) return;

  const cards = Array.from(container.querySelectorAll('.stay-card'));
  if (!cards.length) return;

  cards.sort((a, b) => {
    if (criterion === 'price_low') {
      return parseFloat(a.dataset.price) - parseFloat(b.dataset.price);
    } else if (criterion === 'distance') {
      return parseFloat(a.dataset.dist) - parseFloat(b.dataset.dist);
    } else if (criterion === 'rating') {
      return parseFloat(b.dataset.rating) - parseFloat(a.dataset.rating);
    }
    return 0;
  });

  cards.forEach(c => container.appendChild(c));
}

function escapeHtml(str) {
  return (str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
