/**
 * Yatrika — the traveler
 * Smart Place Autocomplete & Rich Recommendations System
 * Provides 0ms instant recommendations, category filters, and live geocoding fallback.
 */

(function () {
  'use strict';

  // ── 1. Curated Indian Destinations Database ────────────────────────
  const INDIAN_DESTINATIONS = [
    // Karnataka
    { name: "Coorg (Kodagu)", cleanName: "Coorg", state: "Karnataka", cat: "hill", icon: "🌿", tag: "Misty Hills & Coffee", tagline: "Scotland of India · Abbey Falls & Raja's Seat", lat: 12.4244, lon: 75.7382, popular: true },
    { name: "Chikmagalur", cleanName: "Chikmagalur", state: "Karnataka", cat: "hill", icon: "☕", tag: "Coffee Country", tagline: "Mullayanagiri Peak, Bababudangiri & Coffee Estates", lat: 13.3161, lon: 75.7720, popular: true },
    { name: "Samse (Kudremukha)", cleanName: "Samse", state: "Karnataka", cat: "nature", icon: "🍃", tag: "Base Camp & Trekking", tagline: "Kudremukha Shola Grasslands, Tea Estates & Waterfalls", lat: 13.2389, lon: 75.3856, popular: true },
    { name: "Hampi", cleanName: "Hampi", state: "Karnataka", cat: "heritage", icon: "🛕", tag: "UNESCO Heritage", tagline: "Vijayanagara Empire Ruins, Virupaksha & Stone Chariot", lat: 15.3350, lon: 76.4600, popular: true },
    { name: "Gokarna", cleanName: "Gokarna", state: "Karnataka", cat: "beach", icon: "🏖️", tag: "Pristine Beaches", tagline: "Om Beach, Kudle Beach & Mahabaleshwar Temple", lat: 14.5479, lon: 74.3188, popular: true },
    { name: "Mysuru (Mysore)", cleanName: "Mysuru", state: "Karnataka", cat: "heritage", icon: "🏰", tag: "Royal Heritage", tagline: "Mysore Palace, Chamundi Hills & Silk Saree Hub", lat: 12.2958, lon: 76.6394, popular: true },
    { name: "Sakleshpur", cleanName: "Sakleshpur", state: "Karnataka", cat: "hill", icon: "🌾", tag: "Western Ghats", tagline: "Bisle Ghat Viewpoint, Manjarabad Star Fort", lat: 12.9440, lon: 75.7865, popular: false },
    { name: "Dandeli", cleanName: "Dandeli", state: "Karnataka", cat: "nature", icon: "🛶", tag: "River Rafting", tagline: "Kali River Safari, Hornbill Reserves & White Water", lat: 15.2415, lon: 74.6223, popular: false },
    { name: "Badami & Pattadakal", cleanName: "Badami", state: "Karnataka", cat: "heritage", icon: "🪨", tag: "Cave Temples", tagline: "Chalukya Rock-Cut Cave Temples & Agastya Lake", lat: 15.9189, lon: 75.6766, popular: false },
    { name: "Bandipur & Kabini", cleanName: "Bandipur", state: "Karnataka", cat: "nature", icon: "🐅", tag: "Tiger Reserve", tagline: "Elephant Safari, Nagarhole & Jungle Lodges", lat: 11.6664, lon: 76.6291, popular: false },
    { name: "Udupi & Malpe", cleanName: "Udupi", state: "Karnataka", cat: "beach", icon: "🥥", tag: "Coastal & Temples", tagline: "St. Mary's Island, Malpe Beach & Krishna Temple", lat: 13.3409, lon: 74.7421, popular: false },

    // Kerala
    { name: "Munnar", cleanName: "Munnar", state: "Kerala", cat: "hill", icon: "🫖", tag: "Tea Hill Station", tagline: "Rolling Tea Valleys, Anamudi Peak & Eravikulam", lat: 10.0889, lon: 77.0595, popular: true },
    { name: "Alleppey (Alappuzha)", cleanName: "Alleppey", state: "Kerala", cat: "beach", icon: "🚣", tag: "Venice of the East", tagline: "Houseboat Cruises, Vembanad Canals & Backwaters", lat: 9.4981, lon: 76.3388, popular: true },
    { name: "Wayanad", cleanName: "Wayanad", state: "Kerala", cat: "hill", icon: "🌲", tag: "Rainforest & Hills", tagline: "Chembra Peak, Edakkal Caves & Banasura Sagar", lat: 11.6854, lon: 76.1320, popular: true },
    { name: "Varkala", cleanName: "Varkala", state: "Kerala", cat: "beach", icon: "🌊", tag: "Cliff Beach", tagline: "Red Sedimentary Cliffs, Arabian Sea Sunset & Cafes", lat: 8.7379, lon: 76.7163, popular: true },
    { name: "Kochi (Fort Cochin)", cleanName: "Kochi", state: "Kerala", cat: "heritage", icon: "⛵", tag: "Colonial Port", tagline: "Chinese Fishing Nets, Jew Town & Mattancherry", lat: 9.9312, lon: 76.2673, popular: false },
    { name: "Thekkady (Periyar)", cleanName: "Thekkady", state: "Kerala", cat: "nature", icon: "🐘", tag: "Spice & Wildlife", tagline: "Periyar Lake Boat Safari & Cardamom Plantations", lat: 9.6031, lon: 77.1615, popular: false },
    { name: "Kovalam", cleanName: "Kovalam", state: "Kerala", cat: "beach", icon: "🏖️", tag: "Lighthouse Beach", tagline: "Crescent Beaches, Ayurvedic Wellness & Catamaran", lat: 8.4004, lon: 76.9787, popular: false },

    // Goa
    { name: "North Goa", cleanName: "North Goa", state: "Goa", cat: "beach", icon: "🏖️", tag: "Beaches & Nightlife", tagline: "Baga, Anjuna, Chapora Fort & Vibrant Beach Shacks", lat: 15.5494, lon: 73.7535, popular: true },
    { name: "South Goa", cleanName: "South Goa", state: "Goa", cat: "beach", icon: "🌴", tag: "Serene Beaches", tagline: "Palolem, Cabo de Rama & UNESCO Old Goa Churches", lat: 15.2048, lon: 73.9856, popular: true },

    // Tamil Nadu
    { name: "Ooty (Udhagamandalam)", cleanName: "Ooty", state: "Tamil Nadu", cat: "hill", icon: "🌸", tag: "Queen of Hill Stations", tagline: "Nilgiri Mountain Toy Train, Botanical Garden & Lake", lat: 11.4102, lon: 76.6950, popular: true },
    { name: "Kodaikanal", cleanName: "Kodaikanal", state: "Tamil Nadu", cat: "hill", icon: "🌺", tag: "Princess of Hills", tagline: "Kodai Star Lake, Pillar Rocks & Coaker's Walk", lat: 10.2381, lon: 77.4892, popular: true },
    { name: "Pondicherry (Puducherry)", cleanName: "Pondicherry", state: "Puducherry", cat: "beach", icon: "🥐", tag: "French Riviera", tagline: "White Town, Promenade Beach & Auroville Matrimandir", lat: 11.9416, lon: 79.8083, popular: true },
    { name: "Madurai", cleanName: "Madurai", state: "Tamil Nadu", cat: "spiritual", icon: "🛕", tag: "Temple Capital", tagline: "Meenakshi Amman Temple & Nayak Palace Architecture", lat: 9.9252, lon: 78.1198, popular: false },
    { name: "Rameshwaram", cleanName: "Rameshwaram", state: "Tamil Nadu", cat: "spiritual", icon: "🌊", tag: "Holy Island", tagline: "Pamban Sea Bridge, Ramanathaswamy & Dhanushkodi", lat: 9.2876, lon: 79.3129, popular: false },
    { name: "Mahabalipuram", cleanName: "Mahabalipuram", state: "Tamil Nadu", cat: "heritage", icon: "🗿", tag: "UNESCO Shore Temples", tagline: "Rock-cut Shore Temple, Pancha Rathas & Stone Carvings", lat: 12.6269, lon: 80.1927, popular: false },

    // Himachal Pradesh
    { name: "Manali", cleanName: "Manali", state: "Himachal Pradesh", cat: "hill", icon: "🏔️", tag: "Snow & Adventure", tagline: "Solang Valley, Rohtang Pass, Beas River & Paragliding", lat: 32.2396, lon: 77.1887, popular: true },
    { name: "Shimla", cleanName: "Shimla", state: "Himachal Pradesh", cat: "hill", icon: "🌲", tag: "Summer Capital", tagline: "The Ridge, Mall Road, Kalka-Shimla Toy Train", lat: 31.1048, lon: 77.1734, popular: true },
    { name: "Dharamshala & McLeod Ganj", cleanName: "Dharamshala", state: "Himachal Pradesh", cat: "spiritual", icon: "🧘", tag: "Little Lhasa", tagline: "Dalai Lama Monastery, Triund Trek & Kangra Valley", lat: 32.2190, lon: 76.3234, popular: true },
    { name: "Kasol & Parvati Valley", cleanName: "Kasol", state: "Himachal Pradesh", cat: "hill", icon: "🏕️", tag: "Trekker's Paradise", tagline: "Parvati River, Kheerganga Hot Springs & Tosh", lat: 32.0100, lon: 77.3150, popular: true },
    { name: "Spiti Valley", cleanName: "Spiti Valley", state: "Himachal Pradesh", cat: "hill", icon: "❄️", tag: "Middle Land", tagline: "Key Monastery, Chandratal Lake, Kunzum Pass", lat: 32.2461, lon: 78.0349, popular: false },
    { name: "Dalhousie & Khajjiar", cleanName: "Dalhousie", state: "Himachal Pradesh", cat: "hill", icon: "🌲", tag: "Mini Switzerland", tagline: "Pine Valley Meadows, Dainkund Peak & Colonial Vibe", lat: 32.5387, lon: 75.9710, popular: false },

    // Uttarakhand
    { name: "Rishikesh", cleanName: "Rishikesh", state: "Uttarakhand", cat: "spiritual", icon: "🧘", tag: "Yoga & Adventure", tagline: "Ganga Aarti, River Rafting & Laxman Jhula Bridge", lat: 30.0869, lon: 78.2676, popular: true },
    { name: "Mussoorie", cleanName: "Mussoorie", state: "Uttarakhand", cat: "hill", icon: "⛰️", tag: "Queen of the Hills", tagline: "Kempty Falls, Gun Hill Ropeway & Mall Road", lat: 30.4598, lon: 78.0644, popular: true },
    { name: "Nainital", cleanName: "Nainital", state: "Uttarakhand", cat: "hill", icon: "⛵", tag: "Lake District", tagline: "Emerald Naini Lake Boating, Snow View & Naina Devi", lat: 29.3919, lon: 79.4542, popular: true },
    { name: "Haridwar", cleanName: "Haridwar", state: "Uttarakhand", cat: "spiritual", icon: "🪔", tag: "Gateway to Gods", tagline: "Har Ki Pauri Evening Ganga Aarti & Sacred Ghats", lat: 29.9457, lon: 78.1642, popular: false },
    { name: "Jim Corbett National Park", cleanName: "Jim Corbett", state: "Uttarakhand", cat: "nature", icon: "🐅", tag: "Bengal Tigers", tagline: "India's First National Park, Dhikala Zone & Safari", lat: 29.5300, lon: 78.7747, popular: false },
    { name: "Auli", cleanName: "Auli", state: "Uttarakhand", cat: "hill", icon: "⛷️", tag: "Skiing Destination", tagline: "Snow Slopes, Gondola Cable Car & Nanda Devi Peak", lat: 30.5310, lon: 79.5694, popular: false },

    // Rajasthan
    { name: "Jaipur (Pink City)", cleanName: "Jaipur", state: "Rajasthan", cat: "heritage", icon: "🏰", tag: "Royal Heritage", tagline: "Amber Fort, Hawa Mahal, City Palace & Jal Mahal", lat: 26.9124, lon: 75.7873, popular: true },
    { name: "Udaipur (City of Lakes)", cleanName: "Udaipur", state: "Rajasthan", cat: "heritage", icon: "👑", tag: "Venice of the East", tagline: "Lake Pichola, City Palace, Jag Mandir & Fateh Sagar", lat: 24.5854, lon: 73.7125, popular: true },
    { name: "Jodhpur (Blue City)", cleanName: "Jodhpur", state: "Rajasthan", cat: "heritage", icon: "🏰", tag: "Sun City", tagline: "Mehrangarh Fort, Umaid Bhawan & Blue Alleys", lat: 26.2389, lon: 73.0243, popular: false },
    { name: "Jaisalmer (Golden City)", cleanName: "Jaisalmer", state: "Rajasthan", cat: "heritage", icon: "🏜️", tag: "Thar Desert", tagline: "Golden Fort Living Citadel, Sam Sand Dunes & Camels", lat: 26.9157, lon: 70.9083, popular: true },
    { name: "Pushkar", cleanName: "Pushkar", state: "Rajasthan", cat: "spiritual", icon: "🐪", tag: "Sacred Oasis", tagline: "Holy Pushkar Lake, Lord Brahma Temple & Desert Fair", lat: 26.4899, lon: 74.5511, popular: false },
    { name: "Ranthambore", cleanName: "Ranthambore", state: "Rajasthan", cat: "nature", icon: "🐯", tag: "Tiger Haven", tagline: "Ancient Hill Fort & Wild Bengal Tiger Safari", lat: 26.0173, lon: 76.5026, popular: false },

    // Ladakh & J&K
    { name: "Leh Ladakh", cleanName: "Leh Ladakh", state: "Ladakh", cat: "hill", icon: "🏔️", tag: "Land of High Passes", tagline: "Pangong Tso, Nubra Valley, Khardung La & Monasteries", lat: 34.1526, lon: 77.5771, popular: true },
    { name: "Srinagar", cleanName: "Srinagar", state: "Jammu & Kashmir", cat: "hill", icon: "🛶", tag: "Paradise on Earth", tagline: "Dal Lake Shikara, Mughal Gardens & Houseboats", lat: 34.0837, lon: 74.7973, popular: true },
    { name: "Gulmarg", cleanName: "Gulmarg", state: "Jammu & Kashmir", cat: "hill", icon: "🎿", tag: "Meadow of Flowers", tagline: "Highest Cable Car Gondola & Snow Skiing Slopes", lat: 34.0484, lon: 74.3805, popular: false },

    // West Bengal & North East
    { name: "Darjeeling", cleanName: "Darjeeling", state: "West Bengal", cat: "hill", icon: "🫖", tag: "Queen of Himalayas", tagline: "Tiger Hill Kanchenjunga Sunrise, Toy Train & Tea", lat: 27.0410, lon: 88.2663, popular: true },
    { name: "Gangtok", cleanName: "Gangtok", state: "Sikkim", cat: "hill", icon: "🏔️", tag: "Sikkimese Capital", tagline: "Tsomgo Lake, Nathula Pass & Rumtek Monastery", lat: 27.3389, lon: 88.6065, popular: true },
    { name: "Shillong", cleanName: "Shillong", state: "Meghalaya", cat: "nature", icon: "🌧️", tag: "Scotland of the East", tagline: "Elephant Falls, Umiam Lake & Vibrant Rock Cafes", lat: 25.5788, lon: 91.8933, popular: false },
    { name: "Kaziranga", cleanName: "Kaziranga", state: "Assam", cat: "nature", icon: "🦏", tag: "One-Horned Rhinos", tagline: "Brahmaputra Floodplains & Elephant Grass Safari", lat: 26.5775, lon: 93.1711, popular: false },

    // Maharashtra, UP, MP
    { name: "Mahabaleshwar", cleanName: "Mahabaleshwar", state: "Maharashtra", cat: "hill", icon: "🍓", tag: "Strawberry Hills", tagline: "Arthur's Seat, Venna Lake & Western Ghats Vista", lat: 17.9237, lon: 73.6586, popular: false },
    { name: "Lonavala & Khandala", cleanName: "Lonavala", state: "Maharashtra", cat: "hill", icon: "🌧️", tag: "Monsoon Getaway", tagline: "Tiger's Leap, Bhushi Dam & Karla Caves", lat: 18.7557, lon: 73.4091, popular: false },
    { name: "Varanasi (Kashi)", cleanName: "Varanasi", state: "Uttar Pradesh", cat: "spiritual", icon: "🛕", tag: "Eternal City", tagline: "Dashashwamedh Ghat Aarti, Kashi Vishwanath & Ganga", lat: 25.3176, lon: 82.9739, popular: true },
    { name: "Agra", cleanName: "Agra", state: "Uttar Pradesh", cat: "heritage", icon: "🕌", tag: "Wonders of the World", tagline: "Taj Mahal, Agra Fort & Mehtab Bagh", lat: 27.1767, lon: 78.0081, popular: true }
  ];

  // ── 2. Curated Indian Starting Transit Hubs (Origins) ──────────────
  const INDIAN_ORIGINS = [
    { name: "Bengaluru", state: "Karnataka", hub: "BLR Kempegowda Int'l / SBC Junction", icon: "🌆", popular: true },
    { name: "Mumbai", state: "Maharashtra", hub: "BOM Airport / CSMT Junction", icon: "🏙️", popular: true },
    { name: "Delhi (NCR)", state: "Delhi", hub: "DEL IGI Airport / New Delhi NDLS", icon: "🏛️", popular: true },
    { name: "Hyderabad", state: "Telangana", hub: "HYD Airport / Secunderabad SC", icon: "💎", popular: true },
    { name: "Chennai", state: "Tamil Nadu", hub: "MAA Airport / Chennai Central MAS", icon: "🌊", popular: true },
    { name: "Pune", state: "Maharashtra", hub: "PNQ Airport / Pune Junction PUNE", icon: "🎓", popular: true },
    { name: "Kolkata", state: "West Bengal", hub: "CCU Airport / Howrah Junction HWH", icon: "🌉", popular: true },
    { name: "Hubballi (Hubli)", state: "Karnataka", hub: "HBX Airport / SSS Hubballi UBL", icon: "🚂", popular: true },
    { name: "Kochi (Cochin)", state: "Kerala", hub: "COK Airport / Ernakulam Jn ERS", icon: "⛵", popular: true },
    { name: "Mangaluru", state: "Karnataka", hub: "IXE Airport / Mangalore Central MAQ", icon: "⚓", popular: true },
    { name: "Ahmedabad", state: "Gujarat", hub: "AMD Airport / Kalupur ADI Junction", icon: "🪁", popular: true },
    { name: "Jaipur", state: "Rajasthan", hub: "JAI Airport / Jaipur Junction JP", icon: "🏰", popular: true },
    { name: "Chandigarh", state: "Punjab/Haryana", hub: "IXC Airport / Chandigarh CDG", icon: "🌳", popular: false },
    { name: "Lucknow", state: "Uttar Pradesh", hub: "LKO Airport / Charbagh LKO", icon: "🍢", popular: false },
    { name: "Coimbatore", state: "Tamil Nadu", hub: "CJB Airport / Coimbatore CBE", icon: "🏭", popular: false },
    { name: "Mysuru", state: "Karnataka", hub: "MYQ Airport / Mysuru Junction MYS", icon: "🏰", popular: false },
    { name: "Goa (Madgaon)", state: "Goa", hub: "GOI / GOX Airport / Madgaon MAO", icon: "🏖️", popular: false },
    { name: "Belagavi", state: "Karnataka", hub: "IXG Airport / Belagavi BGM", icon: "🏰", popular: false },
    { name: "Varanasi", state: "Uttar Pradesh", hub: "VNS Airport / Varanasi Cantt BSB", icon: "🛕", popular: false },
    { name: "Indore", state: "Madhya Pradesh", hub: "IDR Devi Ahilya Airport / INDB", icon: "🍽️", popular: false },
    { name: "Guwahati", state: "Assam", hub: "GAU Airport / Guwahati GHY", icon: "🦏", popular: false }
  ];

  // ── 3. Helper: Highlight Matching Substrings ───────────────────────
  function highlightMatch(text, query) {
    if (!query || !query.trim()) return escapeHTML(text);
    const q = query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${q})`, 'gi');
    return escapeHTML(text).replace(regex, '<mark class="place-match-highlight">$1</mark>');
  }

  function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag));
  }

  // ── 4. Main Autocomplete Controller ────────────────────────────────
  class PlaceAutocomplete {
    constructor(container, options = {}) {
      this.container = container;
      this.type = options.type || container.dataset.type || 'destination'; // 'destination' or 'origin'
      this.input = container.querySelector('.place-text-input') || container.querySelector('input[type="text"]');
      this.clearBtn = container.querySelector('.place-clear-btn');
      this.badgeChip = container.querySelector('.place-indicator-chip');
      this.badgeText = container.querySelector('.place-chip-badge');
      this.dropdown = container.querySelector('.place-rec-dropdown');
      this.inputBox = container.querySelector('.place-input-box');

      this.onSelect = options.onSelect || null;
      this.selectedIndex = -1;
      this.currentFilter = 'all';
      this.renderedItems = [];
      this.debounceTimer = null;
      this.geoAbortController = null;

      this.init();
    }

    init() {
      if (!this.input || !this.dropdown) return;

      // Ensure necessary classes & structure
      if (this.type === 'origin' && this.inputBox) {
        this.inputBox.classList.add('origin-box');
      }

      // Initial clear button state
      this.toggleClearBtn();
      this.updateSelectedBadge(this.input.value);

      // Event Listeners
      this.input.addEventListener('focus', () => {
        this.openDropdown();
      });

      this.input.addEventListener('input', () => {
        this.toggleClearBtn();
        this.updateSelectedBadge(this.input.value);
        this.selectedIndex = -1;
        this.render();
      });

      this.input.addEventListener('keydown', (e) => this.handleKeyDown(e));

      if (this.clearBtn) {
        this.clearBtn.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.input.value = '';
          this.toggleClearBtn();
          this.updateSelectedBadge('');
          this.input.focus();
          this.currentFilter = 'all';
          this.render();
          this.triggerChangeEvent();
        });
      }

      // Close on outside click
      document.addEventListener('click', (e) => {
        if (!this.container.contains(e.target)) {
          this.closeDropdown();
        }
      });
    }

    toggleClearBtn() {
      if (!this.clearBtn) return;
      if (this.input.value && this.input.value.trim().length > 0) {
        this.clearBtn.classList.remove('d-none');
      } else {
        this.clearBtn.classList.add('d-none');
      }
    }

    updateSelectedBadge(val) {
      if (!this.badgeChip || !this.badgeText) return;
      if (!val || !val.trim()) {
        this.badgeChip.classList.add('d-none');
        return;
      }
      const q = val.trim().toLowerCase();
      if (this.type === 'destination') {
        const found = INDIAN_DESTINATIONS.find(d => 
          d.cleanName.toLowerCase() === q || d.name.toLowerCase().includes(q)
        );
        if (found) {
          const catLabel = found.cat === 'hill' ? 'Hill Station' :
                           found.cat === 'beach' ? 'Beach' :
                           found.cat === 'heritage' ? 'Heritage' :
                           found.cat === 'nature' ? 'Base Camp' : 'Spiritual';
          this.badgeText.innerHTML = `${found.icon} ${catLabel}`;
          this.badgeChip.classList.remove('d-none');
        } else {
          this.badgeChip.classList.add('d-none');
        }
      } else {
        const found = INDIAN_ORIGINS.find(o => o.name.toLowerCase().includes(q));
        if (found) {
          this.badgeText.innerHTML = `${found.icon} Transit Hub`;
          this.badgeChip.classList.remove('d-none');
        } else {
          this.badgeChip.classList.add('d-none');
        }
      }
    }

    openDropdown() {
      if (this.inputBox) this.inputBox.classList.add('is-focused');
      this.dropdown.classList.remove('d-none');
      this.selectedIndex = -1;
      this.render();
    }

    closeDropdown() {
      if (this.inputBox) this.inputBox.classList.remove('is-focused');
      this.dropdown.classList.add('d-none');
      this.selectedIndex = -1;
    }

    handleKeyDown(e) {
      if (this.dropdown.classList.contains('d-none')) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          this.openDropdown();
          e.preventDefault();
        }
        return;
      }

      const items = this.dropdown.querySelectorAll('.rec-item:not(.rec-loading-row)');
      if (!items.length) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.selectedIndex = (this.selectedIndex + 1) % items.length;
        this.highlightSelectedItem(items);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.selectedIndex = (this.selectedIndex - 1 + items.length) % items.length;
        this.highlightSelectedItem(items);
      } else if (e.key === 'Enter') {
        if (this.selectedIndex >= 0 && this.selectedIndex < items.length) {
          e.preventDefault();
          items[this.selectedIndex].click();
        }
      } else if (e.key === 'Escape') {
        this.closeDropdown();
      }
    }

    highlightSelectedItem(items) {
      items.forEach((it, idx) => {
        if (idx === this.selectedIndex) {
          it.classList.add('is-selected');
          it.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        } else {
          it.classList.remove('is-selected');
        }
      });
    }

    render() {
      const q = (this.input.value || '').trim();
      if (this.type === 'destination') {
        this.renderDestinations(q);
      } else {
        this.renderOrigins(q);
      }
    }

    // ── Destination Render ──────────────────────────────────────────
    renderDestinations(query) {
      const isSearch = query.length > 0;
      let matched = [];

      if (!isSearch) {
        // Filter by category tabs
        if (this.currentFilter === 'all') {
          matched = INDIAN_DESTINATIONS.filter(d => d.popular);
        } else {
          matched = INDIAN_DESTINATIONS.filter(d => d.cat === this.currentFilter);
        }
      } else {
        // Query match
        const ql = query.toLowerCase();
        matched = INDIAN_DESTINATIONS.filter(d => {
          return d.name.toLowerCase().includes(ql) ||
                 d.cleanName.toLowerCase().includes(ql) ||
                 d.state.toLowerCase().includes(ql) ||
                 d.tag.toLowerCase().includes(ql) ||
                 d.tagline.toLowerCase().includes(ql);
        });
      }

      this.renderedItems = matched;

      // Build HTML
      let html = `
        <div class="rec-dropdown-header">
          <div class="rec-header-top">
            <span class="rec-header-title">
              ${isSearch ? `<i class="bi bi-search text-turquoise"></i> Matching Destinations` : `🔥 Recommended Destinations`}
            </span>
            <span class="rec-header-count">${matched.length} ${matched.length === 1 ? 'place' : 'places'}</span>
          </div>
          ${!isSearch ? `
            <div class="rec-category-tabs">
              <button type="button" class="rec-cat-btn ${this.currentFilter==='all'?'active':''}" data-cat="all">🌟 All Popular</button>
              <button type="button" class="rec-cat-btn ${this.currentFilter==='hill'?'active':''}" data-cat="hill">🌿 Hills &amp; Tea</button>
              <button type="button" class="rec-cat-btn ${this.currentFilter==='beach'?'active':''}" data-cat="beach">🏖️ Beaches</button>
              <button type="button" class="rec-cat-btn ${this.currentFilter==='heritage'?'active':''}" data-cat="heritage">🛕 Heritage</button>
              <button type="button" class="rec-cat-btn ${this.currentFilter==='nature'?'active':''}" data-cat="nature">🍃 Base Camps</button>
              <button type="button" class="rec-cat-btn ${this.currentFilter==='spiritual'?'active':''}" data-cat="spiritual">🧘 Spiritual</button>
            </div>
          ` : ''}
        </div>
        <div class="rec-list-wrapper" id="recListWrapper">
      `;

      if (matched.length > 0) {
        matched.forEach((d, idx) => {
          const badgeClass = d.cat === 'hill' ? 'badge-hill' :
                             d.cat === 'beach' ? 'badge-beach' :
                             d.cat === 'heritage' ? 'badge-heritage' :
                             d.cat === 'nature' ? 'badge-nature' : 'badge-heritage';
          html += `
            <div class="rec-item ${idx===this.selectedIndex?'is-selected':''}" 
                 data-idx="${idx}" 
                 data-clean="${escapeHTML(d.cleanName)}"
                 data-name="${escapeHTML(d.name)}"
                 data-lat="${d.lat}" 
                 data-lon="${d.lon}">
              <div class="rec-icon-circle">${d.icon}</div>
              <div class="rec-info">
                <div class="rec-title-row">
                  <span class="rec-title">${highlightMatch(d.name, query)}</span>
                </div>
                <div class="rec-subtitle">${escapeHTML(d.state)} · ${highlightMatch(d.tagline, query)}</div>
              </div>
              <span class="rec-badge ${badgeClass}">${escapeHTML(d.tag)}</span>
            </div>
          `;
        });
      } else {
        html += `
          <div class="p-3 text-center text-muted small">
            <i class="bi bi-geo-alt fs-4 d-block mb-1 text-turquoise"></i>
            No pre-saved destination found for <strong>"${escapeHTML(query)}"</strong>.
            <div class="mt-1 extra-small text-secondary">Searching global OpenStreetMap network...</div>
          </div>
        `;
      }

      // External OpenStreetMap Section Container
      html += `
          <div id="geoFallbackContainer"></div>
        </div>
        <div class="rec-dropdown-footer">
          <div class="rec-keys-hint">
            <span class="rec-key-pill">↑</span><span class="rec-key-pill">↓</span> to navigate
            <span class="rec-key-pill ms-2">↵</span> to select
          </div>
          <span>Yatrika Smart Route</span>
        </div>
      `;

      this.dropdown.innerHTML = html;

      // Attach category tab listeners
      this.dropdown.querySelectorAll('.rec-cat-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.currentFilter = btn.dataset.cat;
          this.render();
        });
      });

      // Attach click events on items
      this.dropdown.querySelectorAll('.rec-item').forEach(item => {
        item.addEventListener('click', () => {
          const cleanName = item.dataset.clean || item.dataset.name;
          const lat = parseFloat(item.dataset.lat || 0);
          const lon = parseFloat(item.dataset.lon || 0);
          this.selectPlace(cleanName, {
            name: item.dataset.name,
            cleanName: cleanName,
            lat: lat,
            lon: lon
          });
        });
      });

      // Trigger debounced geocoding search for custom/worldwide places
      if (isSearch && query.length >= 2) {
        this.triggerGeocoding(query);
      }
    }

    // ── Origin Render ────────────────────────────────────────────────
    renderOrigins(query) {
      const isSearch = query.length > 0;
      let matched = [];

      if (!isSearch) {
        matched = INDIAN_ORIGINS.filter(o => o.popular);
      } else {
        const ql = query.toLowerCase();
        matched = INDIAN_ORIGINS.filter(o => {
          return o.name.toLowerCase().includes(ql) ||
                 o.state.toLowerCase().includes(ql) ||
                 o.hub.toLowerCase().includes(ql);
        });
      }

      let html = `
        <div class="rec-dropdown-header">
          <div class="rec-header-top">
            <span class="rec-header-title">
              ${isSearch ? `<i class="bi bi-search text-navy"></i> Matching Starting Hubs` : `⭐ Major Starting Cities &amp; Hubs`}
            </span>
            <span class="rec-header-count">${matched.length} hubs</span>
          </div>
        </div>
        <div class="rec-list-wrapper" id="recListWrapper">
      `;

      if (matched.length > 0) {
        matched.forEach((o, idx) => {
          html += `
            <div class="rec-item ${idx===this.selectedIndex?'is-selected':''}" 
                 data-idx="${idx}" 
                 data-name="${escapeHTML(o.name)}">
              <div class="rec-icon-circle">${o.icon}</div>
              <div class="rec-info">
                <div class="rec-title-row">
                  <span class="rec-title">${highlightMatch(o.name, query)}</span>
                </div>
                <div class="rec-subtitle">${escapeHTML(o.state)} · ${escapeHTML(o.hub)}</div>
              </div>
              <span class="rec-badge badge-hub">Transit Hub</span>
            </div>
          `;
        });
      } else {
        html += `
          <div class="p-3 text-center text-muted small">
            No major hub found for <strong>"${escapeHTML(query)}"</strong>.
            <div class="mt-1 extra-small text-secondary">Searching global OpenStreetMap network...</div>
          </div>
        `;
      }

      html += `
          <div id="geoFallbackContainer"></div>
        </div>
        <div class="rec-dropdown-footer">
          <div class="rec-keys-hint">
            <span class="rec-key-pill">↑</span><span class="rec-key-pill">↓</span> navigate
            <span class="rec-key-pill ms-2">↵</span> select
          </div>
          <span>Door-to-Door Transit Hub</span>
        </div>
      `;

      this.dropdown.innerHTML = html;

      this.dropdown.querySelectorAll('.rec-item').forEach(item => {
        item.addEventListener('click', () => {
          const name = item.dataset.name;
          this.selectPlace(name, { name: name, cleanName: name });
        });
      });

      if (isSearch && query.length >= 3) {
        this.triggerGeocoding(query);
      }
    }

    // ── Geocoding Fallback for Custom Cities ──────────────────────────
    triggerGeocoding(query) {
      clearTimeout(this.debounceTimer);
      if (this.geoAbortController) {
        this.geoAbortController.abort();
      }

      this.debounceTimer = setTimeout(async () => {
        const geoContainer = this.dropdown.querySelector('#geoFallbackContainer');
        if (!geoContainer) return;

        this.geoAbortController = new AbortController();
        try {
          const res = await fetch(`/planner/api/geocode?q=${encodeURIComponent(query)}&limit=4`, {
            signal: this.geoAbortController.signal
          });
          if (!res.ok) return;
          const geoResults = await res.json();
          if (!geoResults || !geoResults.length) return;

          let geoHtml = `
            <div class="rec-section-divider">
              <i class="bi bi-globe2 text-turquoise"></i> OpenStreetMap Live Locations
            </div>
          `;

          geoResults.forEach(r => {
            const shortName = r.display_name.split(',')[0].trim();
            const sub = r.display_name.split(',').slice(1, 4).join(', ').trim();
            geoHtml += `
              <div class="rec-item geo-item" data-clean="${escapeHTML(shortName)}" data-lat="${r.lat}" data-lon="${r.lon}">
                <div class="rec-icon-circle">📍</div>
                <div class="rec-info">
                  <div class="rec-title">${escapeHTML(shortName)}</div>
                  <div class="rec-subtitle">${escapeHTML(sub)}</div>
                </div>
                <span class="rec-badge badge-hub">Live Map</span>
              </div>
            `;
          });

          geoContainer.innerHTML = geoHtml;

          geoContainer.querySelectorAll('.geo-item').forEach(item => {
            item.addEventListener('click', () => {
              const name = item.dataset.clean;
              this.selectPlace(name, {
                name: name,
                cleanName: name,
                lat: parseFloat(item.dataset.lat || 0),
                lon: parseFloat(item.dataset.lon || 0)
              });
            });
          });
        } catch (e) {
          if (e.name !== 'AbortError') console.warn('Geocode fallback error', e);
        }
      }, 350);
    }

    selectPlace(cleanName, placeObj) {
      this.input.value = cleanName;
      this.toggleClearBtn();
      this.updateSelectedBadge(cleanName);
      this.closeDropdown();
      this.triggerChangeEvent();

      if (typeof this.onSelect === 'function') {
        this.onSelect(cleanName, placeObj);
      }

      // Dispatch custom DOM event
      this.input.dispatchEvent(new CustomEvent('placeSelected', {
        bubbles: true,
        detail: placeObj
      }));
    }

    triggerChangeEvent() {
      this.input.dispatchEvent(new Event('input', { bubbles: true }));
      this.input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  // ── 5. Global Initializer ──────────────────────────────────────────
  function initAllPlaceAutocompletes() {
    document.querySelectorAll('.place-autocomplete-container').forEach(container => {
      if (!container._placeAutocomplete) {
        container._placeAutocomplete = new PlaceAutocomplete(container);
      }
    });
  }

  // Expose globally
  window.PlaceAutocomplete = PlaceAutocomplete;
  window.initAllPlaceAutocompletes = initAllPlaceAutocompletes;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllPlaceAutocompletes);
  } else {
    initAllPlaceAutocompletes();
  }
})();
