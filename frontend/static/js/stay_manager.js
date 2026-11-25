/**
 * Yatrika Stay Manager — Interactive Filtering, Steppers, & Floating Map Window
 */

let stayMap = null;
let currentStayData = null;
let hotelMarkers = [];
let destMarker = null;

// Filter & Sort State
let currentSort = 'recommended';
let currentTier = 'all';
let activeFacilities = new Set();

document.addEventListener('DOMContentLoaded', () => {
  // 1. Load initial embedded server state (Results Page)
  try {
    const rawDataEl = document.getElementById('serverStayData');
    if (rawDataEl && rawDataEl.textContent.trim()) {
      currentStayData = JSON.parse(rawDataEl.textContent);
    }
  } catch (err) {
    console.warn('[StayManager] Failed to parse embedded server data:', err);
  }

  // 2. Initialize 3D Card Tilt on Launchpad Hero (Search Mode)
  init3DCardTilt();

  // 3. Initialize Dates and Steppers (Search Mode)
  initStayDates();

  // 4. Keyboard Listener for Floating Map Modal (ESC to close)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeFloatingMap();
    }
  });
});

// ==============================================================================
// 1. Search Mode: 3D Tilt Physics & Stepper Handlers
// ==============================================================================
function init3DCardTilt() {
  const card = document.getElementById('stayLaunchpadCard');
  const wrapper = document.getElementById('card3DWrapper');
  if (!card || !wrapper) return;

  wrapper.addEventListener('mousemove', (e) => {
    const rect = wrapper.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    const rotateX = -(y / rect.height) * 7;
    const rotateY = (x / rect.width) * 7;
    card.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
  });

  wrapper.addEventListener('mouseleave', () => {
    card.style.transform = 'rotateX(0deg) rotateY(0deg)';
  });
}

function initStayDates() {
  const startInput = document.getElementById('tripStartDate');
  const endInput = document.getElementById('tripEndDate');
  const daysInput = document.getElementById('tripDays');

  const today = new Date();
  const defaultCheckin = new Date(today);
  defaultCheckin.setDate(today.getDate() + 2);

  if (startInput && !startInput.value) {
    startInput.value = defaultCheckin.toISOString().split('T')[0];
  }

  updateDatesFromDays();
}

function changeDays(delta) {
  const daysInput = document.getElementById('tripDays');
  const daysBadge = document.getElementById('daysCountBadge');
  if (!daysInput) return;

  let currentDays = parseInt(daysInput.value, 10) || 3;
  currentDays = Math.max(1, Math.min(30, currentDays + delta));

  daysInput.value = currentDays;
  if (daysBadge) {
    daysBadge.textContent = `${currentDays} ${currentDays === 1 ? 'Day' : 'Days'}`;
  }

  updateDatesFromDays();
}

function changeTravelers(delta) {
  const travelersInput = document.getElementById('tripTravelers');
  const travelersBadge = document.getElementById('travelersCountBadge');
  if (!travelersInput) return;

  let count = parseInt(travelersInput.value, 10) || 2;
  count = Math.max(1, Math.min(20, count + delta));

  travelersInput.value = count;
  if (travelersBadge) {
    travelersBadge.textContent = `${count} ${count === 1 ? 'Guest' : 'Guests'}`;
  }
}

function updateDatesFromDays() {
  const startInput = document.getElementById('tripStartDate');
  const endInput = document.getElementById('tripEndDate');
  const daysInput = document.getElementById('tripDays');

  if (!startInput || !endInput || !daysInput) return;

  const startDateStr = startInput.value;
  if (!startDateStr) return;

  const days = parseInt(daysInput.value, 10) || 3;
  const startDate = new Date(startDateStr);
  const endDate = new Date(startDate);
  endDate.setDate(startDate.getDate() + days);

  endInput.value = endDate.toISOString().split('T')[0];
}

function selectQuickOffice(office, origin) {
  const destInput = document.getElementById('tripDestination');
  const srcInput = document.getElementById('tripSource');

  if (destInput) destInput.value = office;
  if (srcInput && origin) srcInput.value = origin;

  const form = document.getElementById('staySearchForm');
  if (form) {
    form.submit();
  }
}

function selectPurpose(purpose, btnEl) {
  const purposeInput = document.getElementById('tripPurpose');
  if (purposeInput) purposeInput.value = purpose;

  document.querySelectorAll('.btn-purpose-pill').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
}

// ==============================================================================
// 2. Results Mode: Dynamic Filters & Sorting (Budget, Luxuries, Facilities)
// ==============================================================================
function setSortMode(mode, btnEl) {
  currentSort = mode;
  document.querySelectorAll('.btn-filter-sort').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  applyStayFilters();
}

function setTierFilter(tier, btnEl) {
  currentTier = tier;
  document.querySelectorAll('.btn-tier-pill').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  applyStayFilters();
}

function toggleFacilityFilter(facility, btnEl) {
  if (activeFacilities.has(facility)) {
    activeFacilities.delete(facility);
    if (btnEl) btnEl.classList.remove('active');
  } else {
    activeFacilities.add(facility);
    if (btnEl) btnEl.classList.add('active');
  }

  // Show or hide Reset button
  const resetBtn = document.getElementById('resetFiltersBtn');
  if (resetBtn) {
    if (activeFacilities.size > 0 || currentTier !== 'all' || currentSort !== 'recommended') {
      resetBtn.classList.remove('d-none');
    } else {
      resetBtn.classList.add('d-none');
    }
  }

  applyStayFilters();
}

function resetAllFilters() {
  activeFacilities.clear();
  currentTier = 'all';
  currentSort = 'recommended';

  document.querySelectorAll('.btn-facility-pill').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.btn-tier-pill').forEach(b => {
    b.classList.toggle('active', b.dataset.tier === 'all');
  });
  document.querySelectorAll('.btn-filter-sort').forEach(b => {
    b.classList.toggle('active', b.dataset.sort === 'recommended');
  });

  const resetBtn = document.getElementById('resetFiltersBtn');
  if (resetBtn) resetBtn.classList.add('d-none');

  applyStayFilters();
}

function applyStayFilters() {
  const container = document.getElementById('stayCardsGrid');
  if (!container) return;

  const cards = Array.from(container.querySelectorAll('.stay-grid-card'));
  let visibleCount = 0;

  cards.forEach(card => {
    const cardTier = card.dataset.tier || '';
    const facilitiesStr = card.dataset.facilities || '';
    const cardFacilities = facilitiesStr.split(',').map(f => f.trim().toLowerCase());

    // 1. Tier Match
    const matchesTier = (currentTier === 'all') || (cardTier.toLowerCase() === currentTier.toLowerCase());

    // 2. Facilities Match (Must include all active filters)
    let matchesFacilities = true;
    for (const reqFac of activeFacilities) {
      if (!cardFacilities.includes(reqFac.toLowerCase())) {
        matchesFacilities = false;
        break;
      }
    }

    if (matchesTier && matchesFacilities) {
      card.style.display = 'flex';
      visibleCount++;
    } else {
      card.style.display = 'none';
    }
  });

  // Update visible count badge
  const countBadge = document.getElementById('visibleCount');
  if (countBadge) countBadge.textContent = visibleCount;

  // Empty state handling
  const emptyState = document.getElementById('noMatchingStaysState');
  if (emptyState) {
    if (visibleCount === 0) {
      emptyState.classList.remove('d-none');
    } else {
      emptyState.classList.add('d-none');
    }
  }

  // 3. Sort visible cards
  const visibleCards = cards.filter(c => c.style.display !== 'none');
  visibleCards.sort((a, b) => {
    const priceA = parseFloat(a.dataset.price) || 0;
    const priceB = parseFloat(b.dataset.price) || 0;
    const distA = parseFloat(a.dataset.dist) || 0;
    const distB = parseFloat(b.dataset.dist) || 0;
    const ratingA = parseFloat(a.dataset.rating) || 0;
    const ratingB = parseFloat(b.dataset.rating) || 0;

    if (currentSort === 'price_asc') {
      return priceA - priceB; // Budget: Low to High
    } else if (currentSort === 'luxury_desc') {
      return priceB - priceA; // Luxuries & Premium: High to Low
    } else if (currentSort === 'distance') {
      return distA - distB; // Nearest to Office
    } else if (currentSort === 'rating') {
      return ratingB - ratingA; // Highest Rated
    }
    return (parseInt(a.dataset.order) || 0) - (parseInt(b.dataset.order) || 0); // AI Recommended (server default)
  });

  visibleCards.forEach(c => container.appendChild(c));
}

// ==============================================================================
// 3. Floating Map Window (Modal Overlay)
// ==============================================================================
function handleMapOverlayClick(event) {
  if (event.target.id === 'floatingMapModal') {
    closeFloatingMap();
  }
}

function closeFloatingMap() {
  const modal = document.getElementById('floatingMapModal');
  if (modal) {
    modal.classList.add('d-none');
  }
}

async function openFloatingMap(stayId, lat, lon, name, price, img, distKm, driveMins) {
  const modal = document.getElementById('floatingMapModal');
  if (!modal) return;

  // 1. Show Modal
  modal.classList.remove('d-none');

  // 2. Set Header & Subtitle Info
  const titleEl = document.getElementById('modalHotelTitle');
  const badgeEl = document.getElementById('modalCommuteBadge');
  const anchorEl = document.getElementById('modalAnchorOffice');

  if (titleEl) titleEl.textContent = name;
  if (badgeEl) badgeEl.textContent = `🚗 ${distKm} km • ~${driveMins} mins to office`;
  if (anchorEl && currentStayData?.destination) {
    anchorEl.textContent = currentStayData.destination;
  }

  // 3. Initialize or Resize MapLibre inside Floating Container
  initOrResizeFloatingMap(lat, lon, name, price, img, distKm, driveMins);
}

function initOrResizeFloatingMap(hotelLat, hotelLon, hotelName, price, img, distKm, driveMins) {
  const mapContainer = document.getElementById('stayMap');
  if (!mapContainer) return;

  const destLat = currentStayData?.dest_coords?.lat || hotelLat;
  const destLon = currentStayData?.dest_coords?.lon || hotelLon;

  if (!stayMap) {
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
      center: [hotelLon, hotelLat],
      zoom: 13
    });

    stayMap.addControl(new maplibregl.NavigationControl(), 'top-right');

    stayMap.on('load', () => {
      // Road route GeoJSON line source & layers
      stayMap.addSource('stay-road-route', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });

      stayMap.addLayer({
        id: 'stay-road-route-casing',
        type: 'line',
        source: 'stay-road-route',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': '#0f172a', 'line-width': 7, 'line-opacity': 0.85 }
      });

      stayMap.addLayer({
        id: 'stay-road-route-line',
        type: 'line',
        source: 'stay-road-route',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': '#0284c7', 'line-width': 4.5 }
      });

      renderFloatingMapMarkersAndRoute(hotelLat, hotelLon, hotelName, price, img, distKm, driveMins, destLat, destLon);
    });
  } else {
    // Already initialized: resize to modal container dimensions & re-render
    setTimeout(() => {
      stayMap.resize();
      renderFloatingMapMarkersAndRoute(hotelLat, hotelLon, hotelName, price, img, distKm, driveMins, destLat, destLon);
    }, 100);
  }
}

async function renderFloatingMapMarkersAndRoute(hotelLat, hotelLon, hotelName, price, img, distKm, driveMins, destLat, destLon) {
  if (!stayMap) return;

  // Clear previous markers
  hotelMarkers.forEach(m => m.remove());
  hotelMarkers = [];
  if (destMarker) {
    destMarker.remove();
    destMarker = null;
  }

  // 1. Destination / Office Marker
  const destEl = document.createElement('div');
  destEl.className = 'custom-dest-pin';
  destEl.innerHTML = '🏢';
  destEl.title = `Office Anchor: ${currentStayData?.destination || 'Office'}`;

  destMarker = new maplibregl.Marker({ element: destEl })
    .setLngLat([destLon, destLat])
    .setPopup(new maplibregl.Popup({ offset: 15 }).setHTML(`
      <div class="p-1">
        <div class="fw-bold extra-small text-coral">🏢 Target Office Anchor</div>
        <div class="small fw-semibold text-navy">${currentStayData?.destination || 'Target Location'}</div>
      </div>
    `))
    .addTo(stayMap);

  // 2. Selected Hotel Marker
  const pinEl = document.createElement('div');
  pinEl.className = 'custom-hotel-pin active-pin';
  const travelersCount = currentStayData?.travelers || 1;
  const perPersonPrice = Math.round(Number(price) / Math.max(1, travelersCount));
  pinEl.innerHTML = `₹${perPersonPrice.toLocaleString('en-IN')}/person/day`;

  const hotelMarker = new maplibregl.Marker({ element: pinEl })
    .setLngLat([hotelLon, hotelLat])
    .setPopup(new maplibregl.Popup({ offset: 20 }).setHTML(`
      <div style="max-width: 220px; padding: 2px;">
        <img src="${img}" style="width: 100%; height: 95px; object-fit: cover; border-radius: 6px; margin-bottom: 6px;" />
        <div class="fw-bold small text-navy leading-tight mb-1">${hotelName}</div>
        <div class="d-flex justify-content-between align-items-center extra-small text-muted mb-1">
          <span class="fw-bold text-success">₹${perPersonPrice.toLocaleString('en-IN')} / person / day</span>
          <span>📍 ${distKm} km</span>
        </div>
        <div class="extra-small text-muted mb-1">Room: ₹${Number(price).toLocaleString('en-IN')} / day</div>
        <div class="extra-small text-turquoise fw-semibold">🚗 ~${driveMins} mins to office</div>
      </div>
    `))
    .addTo(stayMap);

  hotelMarkers.push(hotelMarker);

  // Fit bounds around both hotel and office
  const bounds = new maplibregl.LngLatBounds();
  bounds.extend([destLon, destLat]);
  bounds.extend([hotelLon, hotelLat]);
  stayMap.fitBounds(bounds, { padding: 80, maxZoom: 15, duration: 800 });

  // Open hotel popup
  hotelMarker.togglePopup();

  // 3. Fetch and Render Live OSRM Road Route
  try {
    const resp = await fetch('/stay-manager/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stay_lat: hotelLat,
        stay_lon: hotelLon,
        dest_lat: destLat,
        dest_lon: destLon
      })
    });
    const routeData = await resp.json();
    if (routeData.success && routeData.geometry) {
      if (stayMap.getSource('stay-road-route')) {
        stayMap.getSource('stay-road-route').setData({
          type: 'Feature',
          geometry: routeData.geometry
        });
      }

      // Show Road Circuit Badge
      const summaryChip = document.getElementById('mapRouteSummaryChip');
      if (summaryChip) {
        summaryChip.classList.remove('d-none');
        const titleEl = document.getElementById('mapRouteTitle');
        const detailsEl = document.getElementById('mapRouteDetails');
        if (titleEl) titleEl.textContent = `${hotelName} ➔ ${currentStayData?.destination || 'Office'}`;
        if (detailsEl) detailsEl.textContent = `🛣️ ${routeData.distance_km} km road route • ~${routeData.duration_mins} mins drive`;
      }
    }
  } catch (err) {
    console.warn('[StayManager] Route fetch failed:', err);
  }
}

// ==============================================================================
// 4. Stay Selection & Navigation to Transport Mode
// ==============================================================================
let selectedStayObj = null;

function selectStayCard(stayId, stayName, pricePerNight, pricePerPersonDay, lat, lon, img, address, distKm, driveMins) {
  selectedStayObj = {
    id: stayId,
    name: stayName,
    price_per_night: pricePerNight,
    price_per_person_day: pricePerPersonDay,
    lat: lat,
    lon: lon,
    img: img,
    address: address,
    distance_km: distKm,
    drive_mins: driveMins
  };

  // 1. Highlight selected card
  document.querySelectorAll('.stay-grid-card').forEach(c => {
    if (c.id === `card_${stayId}`) {
      c.classList.add('is-selected');
    } else {
      c.classList.remove('is-selected');
    }
  });

  // 2. Populate and display sticky bottom selection dock
  const dock = document.getElementById('stickyStaySelectionDock');
  const dockImg = document.getElementById('dockStayImg');
  const dockName = document.getElementById('dockStayName');
  const dockCommute = document.getElementById('dockStayCommute');
  const dockPrice = document.getElementById('dockStayPrice');

  if (dock) {
    if (dockImg) dockImg.src = img || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=300&q=80';
    if (dockName) dockName.textContent = stayName;
    if (dockCommute) dockCommute.textContent = `🚗 ${distKm} km • ~${driveMins}m to office`;
    if (dockPrice) dockPrice.textContent = `₹${Number(pricePerPersonDay).toLocaleString('en-IN')}`;
    dock.classList.remove('d-none');
  }
}

function proceedToTransportMode() {
  if (!selectedStayObj && currentStayData?.stays?.length > 0) {
    const first = currentStayData.stays[0];
    selectedStayObj = {
      id: first.id,
      name: first.name,
      price_per_night: first.price_per_night,
      price_per_person_day: first.price_per_person_day || first.price_per_night,
      lat: first.lat,
      lon: first.lon,
      img: first.img,
      address: first.address,
      distance_km: first.distance_km,
      drive_mins: first.drive_mins
    };
  }

  if (!selectedStayObj) {
    alert('Please select a stay first.');
    return;
  }

  const dest = currentStayData?.destination || 'Destination';
  const source = currentStayData?.source || 'Bengaluru';
  const days = currentStayData?.days || 3;
  const travelers = currentStayData?.travelers || 2;
  const budget = currentStayData?.budget_per_night || 2500;
  const checkin = currentStayData?.checkin || '';
  const checkout = currentStayData?.checkout || '';

  // Navigate to dedicated Stay Manager Step 2 (Transport Mode Selection)
  const url = `/stay-manager/transport?destination=${encodeURIComponent(dest)}` +
    `&source=${encodeURIComponent(source)}` +
    `&num_days=${encodeURIComponent(days)}` +
    `&travelers=${encodeURIComponent(travelers)}` +
    `&budget=${encodeURIComponent(budget)}` +
    `&checkin=${encodeURIComponent(checkin)}` +
    `&checkout=${encodeURIComponent(checkout)}` +
    `&stay_id=${encodeURIComponent(selectedStayObj.id)}` +
    `&stay_name=${encodeURIComponent(selectedStayObj.name)}` +
    `&stay_price=${encodeURIComponent(selectedStayObj.price_per_night)}` +
    `&stay_pppd=${encodeURIComponent(selectedStayObj.price_per_person_day)}` +
    `&stay_lat=${encodeURIComponent(selectedStayObj.lat)}` +
    `&stay_lon=${encodeURIComponent(selectedStayObj.lon)}` +
    `&stay_img=${encodeURIComponent(selectedStayObj.img)}` +
    `&stay_address=${encodeURIComponent(selectedStayObj.address)}` +
    `&stay_dist=${encodeURIComponent(selectedStayObj.distance_km)}` +
    `&stay_mins=${encodeURIComponent(selectedStayObj.drive_mins)}`;

  window.location.href = url;
}
