# AI Travel Planner — Full Project Status

<div align="center">

**A next-generation interactive travel planning system**  
Built on Flask · Bootstrap 5 · IBM Granite · MapLibre GL · OpenStreetMap APIs

[![IBM Granite](https://img.shields.io/badge/IBM-Granite-0062FF?logo=ibm&logoColor=white)](https://www.ibm.com/granite)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-000000?logo=flask)](https://flask.palletsprojects.com)
[![MapLibre GL](https://img.shields.io/badge/MapLibre-GL-396CB2)](https://maplibre.org)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap)](https://getbootstrap.com)
[![Status](https://img.shields.io/badge/Status-Production--Ready-198038)](/)

</div>

---

## 📌 What This Project Is

The **AI Travel Planner Agent** is a full-stack web application with two complementary planning workflows:

| Workflow | Technology | What It Does |
|---|---|---|
| **Smart Travel Wizard** | Vanilla JS + Real APIs | 10-step interactive planner using live OSM data, OSRM routing, real maps |
| **AI Trip Planner** | IBM Granite via watsonx.ai | Form-based planner that calls IBM Granite to generate a full structured itinerary saved to DB |

Both workflows live on the same Flask app, share the same user accounts, and link to each other.

---

## 🚀 How to Run

```bash
cd TravelPlannerAgent
python app.py
```

Open **http://localhost:5000** in your browser.

> **No API keys required** to use the Smart Wizard — it uses free public APIs (Nominatim, Overpass, OSRM, OpenFreeMap).  
> IBM keys and OpenWeatherMap key are **optional** — the app degrades gracefully without them.

---

## 🗂 Complete File Map

```
TravelPlannerAgent/
│
├── app.py                              ← Flask factory (entry point)
├── requirements.txt                    ← All Python dependencies
├── .env                                ← Local secrets (gitignored)
├── .gitignore
├── Procfile                            ← Gunicorn for Render/Cloud deploy
├── render.yaml                         ← Render.com deployment config
├── streamlit_app.py                    ← Separate Streamlit UI (standalone)
│
├── backend/
│   ├── config.py                       ← Dev/Prod/Test config + all env vars
│   ├── database/
│   │   ├── db.py                       ← SQLite init, query helpers
│   │   └── travel_planner.db           ← Auto-created SQLite database
│   ├── models/
│   │   ├── user.py                     ← User CRUD, SHA-256 password hashing
│   │   └── trip.py                     ← Trip CRUD, saved trips, expenses
│   ├── routes/
│   │   ├── auth_routes.py              ← /auth — register, login, logout, profile
│   │   ├── main_routes.py              ← / — home, dashboard
│   │   ├── planner_routes.py           ← /planner — all trip + wizard routes
│   │   ├── admin_routes.py             ← /admin — user management, analytics
│   │   └── api_routes.py               ← /api — JSON endpoints
│   └── services/
│       ├── granite/
│       │   └── granite_service.py      ← IBM Granite REST calls, JSON parsing
│       ├── weather/
│       │   └── weather_service.py      ← OpenWeatherMap current + forecast
│       └── pdf/
│           └── pdf_service.py          ← ReportLab PDF generator
│
└── frontend/
    ├── templates/
    │   ├── base.html                   ← Master layout (navbar, footer, flash)
    │   ├── home.html                   ← Landing page with wizard showcase
    │   ├── auth/
    │   │   ├── login.html
    │   │   ├── register.html
    │   │   └── profile.html
    │   ├── dashboard/
    │   │   └── dashboard.html          ← User dashboard + wizard launch card
    │   ├── planner/
    │   │   ├── wizard.html             ← 10-step Smart Travel Wizard
    │   │   ├── destinations.html       ← Public destinations explorer (10 places)
    │   │   ├── destination_detail.html ← 8-tab deep-dive (all 10 full datasets)
    │   │   ├── new_trip.html           ← IBM Granite AI planner form
    │   │   ├── view_trip.html          ← 7-tab trip view with map + charts
    │   │   └── saved_trips.html        ← Saved favourites list
    │   ├── admin/
    │   │   ├── dashboard.html
    │   │   ├── users.html
    │   │   └── trips.html
    │   └── errors/
    │       ├── 404.html
    │       └── 500.html
    └── static/
        ├── css/
        │   ├── main.css                ← App-wide styles, dark mode, components
        │   └── wizard.css              ← Wizard design system (~770 lines)
        ├── js/
        │   ├── main.js                 ← Dark mode, flash dismiss, shared utils
        │   ├── wizard.js               ← Full wizard logic + all API calls (~1070 lines)
        │   ├── planner.js              ← Multi-step IBM Granite form logic
        │   └── trip_view.js            ← MapLibre map + Chart.js for view_trip
        └── images/
            └── ibm-logo.svg
```

---

## ✨ Everything the App Can Do Right Now

### 🔐 Authentication System
- **Register** with name, email, password (SHA-256 + salt hashing)
- **Login / Logout** with session management (24-hour persistence)
- **Profile page** — view account details
- **Role system** — `user` and `admin` roles
- Protected routes redirect to login automatically
- Flash messages for all auth events

---

### 🏠 Landing Page (`/`)
- Hero section with animated floating cards (weather, hotel, itinerary)
- Context-aware CTA: **"Launch Smart Wizard"** for logged-in users, **"Start Planning Free"** for guests
- Feature grid — 8 capability cards
- **10-step Smart Wizard showcase** with full step descriptions
- IBM technology section with code preview snippet
- CTA banner linking to registration

---

### 📊 Dashboard (`/dashboard`) — Logged In Only
- **Time-aware greeting** — "Good Morning/Afternoon/Evening, [Name]"
- **4 stat cards** — Total Trips, Saved Trips, Completed Trips, Total Budget (₹)
- **Smart Wizard Launch Card** — full-width gradient banner listing all 10 wizard steps with direct launch button
- **Recent Trips list** — destination, dates, budget, status badge, view button
- **Live Weather widget** — shows current weather for user's last destination (OpenWeatherMap)
- **Saved Trips quick list** — last 4 saved trips
- **Quick Travel Tips** — 6 practical tips
- **8-destination quick-links grid** — direct links to all destination detail pages

---

### 🧙 Smart Travel Wizard (`/planner/wizard`) — 10 Full Steps

The wizard uses **100% real external APIs** — no dummy data, no AI credits needed.

#### Step 1 — Journey Details
- **Nominatim autocomplete** — type any city worldwide, get real geocoded suggestions with lat/lon
- Source + Destination city fields with live dropdown
- **Live OSRM route distance** calculated instantly when both cities are selected (e.g. "312.4 km · ~5h 20m")
- Travel Date + Return Date pickers with auto-calculated number of days
- Traveler counter with ±1 buttons
- Budget range slider (₹5,000 → ₹5,00,000) with live display
- **5 transport modes** — Car, Bike, Bus, Train, Flight (tile selector)
- **9 travel styles** — Adventure, Nature, Family, Solo, Luxury, Budget, Photography, Food, Spiritual
- **Live Trip Preview Card** — updates in real time as you type (destination, distance, days, travelers, budget, style)
- **Live weather chip** — fetches OpenWeatherMap data the moment you select a destination
- **localStorage persistence** — your session is saved and restored on next visit

#### Step 2 — Destination Explorer
- **Overpass API** fetches real tourist attractions from OpenStreetMap within 25 km of destination
- Attraction cards show: name, category icon, rating, distance, visit duration, difficulty, opening hours
- Badges: ⭐ Popular, 👨‍👩‍👧 Family-Friendly, 💎 Hidden Gem
- Favorite button (heart) per card
- **Filter bar** — All, Morning, Afternoon, Sunset, Night, Family, Adventure, Nature, Hidden Gems
- **Real-time search** — type to filter attractions by name or category
- **Floating itinerary sidebar** — live totals for selected places, sightseeing time, estimated distance, budget, time remaining
- Skeleton loading animation while fetching from Overpass
- Selected cards highlighted with green tick

#### Step 3 — Confirm & Reorder
- Drag-and-drop reordering of selected attractions
- Summary stats: places selected, total duration, total distance, entry fees, days needed

#### Step 4 — Interactive Route Planner
- **OSRM API** calculates real road distance and drive time between every stop
- Route timeline: Hotel → Attraction 1 → Attraction 2 → … → Hotel
- Each leg shows: distance (km), drive time, road type, transport mode icon
- **Journey Statistics** panel — total road distance, driving time, sightseeing time, stops count, trip duration
- **Cost Estimate breakdown** — Fuel (vehicle-type-aware), Tolls, Entry Fees, Food, Hotel
- Total estimated trip cost in ₹

#### Step 5 — Smart Timeline
- Auto-generated day-by-day hour-by-hour schedule
- Supports up to 3 days displayed simultaneously
- Events: Depart, Breakfast, Travel legs, Attraction visits, Lunch, Return to Hotel
- Each event has: time, category icon, title, subtitle, priority badge (HIGH/MEDIUM/LOW)
- Travel time between stops calculated from attraction distances

#### Step 6 — Attraction Deep Dive
- Grid of all selected attractions as detail cards
- Click any card → **Side Drawer** slides in from right with:
  - 3-photo gallery grid (Unsplash images)
  - Full description, category, type
  - Quick Info grid — visit duration, distance, rating, difficulty, opening hours, website
  - Travel Tips (3 tips per attraction)
  - Packing Suggestions (6 items)
  - User Reviews

#### Step 7 — Interactive Map (Real MapLibre GL)
- **Live OpenStreetMap tiles** via OpenFreeMap (no API key needed)
- **Red marker** — source/starting city
- **Blue marker** — destination city  
- **Green emoji pins** — every selected attraction, clickable with popup showing name, category, distance, visit time
- **OSRM route polyline** — dashed blue line connecting all stops in order
- Map auto-fits bounds to show all pins simultaneously
- **"Fly to Route"** button — animates camera to first attraction
- **"Satellite"** button — switches to lighter Positron style
- MapLibre built-in navigation controls (zoom, compass, pitch)
- **Map Legend** — hotels, restaurants, attractions, fuel, parking, hospital, police
- **Nearby Places list** — fuel, hospital, police, parking, store, ATM

#### Step 8 — Day Planner
- **Drag-and-drop activity cards** across 4 time columns: 🌅 Morning / ☀️ Afternoon / 🌆 Evening / 🌙 Night
- First attraction auto-placed in Morning column
- Unassigned pool of activities: all selected attractions + Breakfast, Lunch, Dinner, Rest, Shopping, Travel, Return
- Activity cards show: icon, name, duration, type badge (attraction/food/travel/leisure)
- Day selector tabs for multi-day trips

#### Step 9 — Travel Analytics
- **8 animated stat cards** with gradient backgrounds:
  - Total Distance (real OSRM km)
  - Driving Time
  - Sightseeing Time
  - Walking Estimate (steps)
  - Fuel Cost (mode-aware)
  - Total Estimated Spend
  - Remaining Budget
  - Attractions Count
- **Budget Doughnut Chart** (Chart.js) — Fuel / Entry Fees / Food / Hotel / Shopping breakdown
- **Time Distribution Bar Chart** (Chart.js) — time per attraction

#### Step 10 — Trip Overview
- **Hero banner** with gradient overlay, destination name, trip stats
- Trip Statistics grid — dates, road distance, attraction count, sightseeing time, estimated spend, transport
- **Selected Attractions** list — name, category, distance, visit time, website link if available
- **Live Weather card** — current conditions at destination (if OpenWeatherMap configured)
- **Expense Summary** — itemized breakdown with total
- **Packing Checklist** — 18 items, interactive checkboxes
- **Emergency Contacts** — Police (100), Ambulance (108), Fire (101), Tourist Helpline (1363)
- **Action buttons:**
  - 🖨 **Print** — `@media print` CSS hides all other steps, prints clean overview
  - ⬇️ **Download .txt** — structured itinerary file with all details
  - 🔗 **Share** — Web Share API (mobile) or clipboard fallback
  - 🔄 **Start Fresh** — clears localStorage and resets wizard
  - 💾 **Save with IBM Granite AI** — pre-fills `/planner/new` form with wizard data and submits to trigger full Granite AI generation + DB save

---

### 🤖 IBM Granite AI Trip Planner (`/planner/new`) — Requires IBM Keys

Multi-step form that calls IBM Granite to generate a complete trip plan:

- **Form inputs** — destination, dates, budget, travelers, travel style, transport mode, interests, special requirements
- **4 Granite prompts** — Itinerary, Budget, Hotels, Transport (all request structured JSON)
- **Live weather fetch** during form submission
- Results saved to SQLite with full JSON blobs
- Redirects to full trip view on completion
- Graceful fallback with demo data if Granite is unavailable

**Model:** `ibm/granite-4-h-small` (configured in `config.py`, overridable via `.env`)

---

### 📋 Trip View (`/planner/<trip_id>`) — 7 Tabs

After Granite generates a trip, the full view provides:

| Tab | Contents |
|---|---|
| **📅 Itinerary** | Day-wise schedule cards, morning/afternoon/evening, tips |
| **💰 Budget** | Pie chart + breakdown across all spending categories |
| **🏨 Hotels** | AI-recommended budget/mid-range/luxury options with amenities |
| **🚌 Transport** | Mode comparison with cost/time estimates |
| **🌤 Weather** | Current conditions + 7-day forecast cards + travel advice |
| **🗺 Map** | MapLibre GL map with attraction pins (uses saved coordinates) |
| **💳 Expenses** | Add manual expenses; running total vs. budget chart |

Additional actions:
- **Save to Favourites** — with optional notes
- **Download PDF** — full ReportLab-generated PDF report
- **Delete Trip**

---

### 🌍 Destinations Explorer (`/planner/destinations`) — Public

- **Hero section** with search bar
- **Category filter pills** — All, Hill Station, Beach, Heritage, Spiritual, Wildlife, Adventure, City
- **Real-time search** — filters by name, country, or tags as you type
- **10 destination cards** with: image, country, tagline, rating, best time, ideal days, distance from major city, weather, budget, tags
- Badge overlays: 🔥 Trending, ⭐ Popular, 💎 Hidden Gem, ✨ New
- **Featured destination banner** (Coorg) with full stats
- Result counter ("Showing X destinations")
- All cards link to full destination detail pages

---

### 📖 Destination Detail Pages (`/planner/destinations/<slug>`) — Public

**All 10 destinations fully populated** with rich realistic data:

| Destination | Tagline | Category |
|---|---|---|
| **Coorg** | Scotland of India | Hill Station |
| **Goa** | Pearl of the Orient | Beach |
| **Manali** | Gateway to the Himalayas | Hill Station |
| **Jaipur** | The Pink City | Heritage |
| **Kerala Backwaters** | God's Own Country | Nature |
| **Rishikesh** | Yoga Capital of the World | Spiritual |
| **Andaman Islands** | Emerald Islands | Beach |
| **Varanasi** | City of Light | Spiritual |
| **Ranthambore** | Land of Tigers | Wildlife |
| **Spiti Valley** | The Middle Land | Adventure |

**Each destination includes 8 tabs:**

| Tab | Contents |
|---|---|
| **📋 Overview** | Full description, 6 highlights, best visiting months grid (12 months with temp/icon/tag), quick facts panel |
| **📍 Attractions** | 5–8 attraction mini-cards with image, category, duration, fee, difficulty |
| **🌤 Weather** | Current conditions card, monthly guide grid, 3–4 weather tips |
| **🏨 Hotels** | 3 tiers (Luxury / Mid-Range / Budget) with star ratings, price per night, amenities |
| **🍽️ Local Food** | 3–6 food cards with image, type, description of local specialties |
| **📅 Itinerary** | 2–5 day suggested schedule with timed events and activity descriptions |
| **📷 Gallery** | 6-photo grid layout (1 large main + 5 thumbnails) |
| **🚗 Transport** | 3–4 transport options with route details and cost estimates |

**Quick Stats Bar** (sticky below hero): Best Season · Ideal Days · Budget Range · Language · Currency · Timezone

**Hero CTA buttons**: "Plan This Trip" (→ wizard or register) + "View Attractions"

---

### 🛡 Admin Panel (`/admin`) — Admin Role Only

- **Dashboard** — total users, trips, active trips, revenue
- **User Management** — list all users with registration date, trip count, role
- **Trip Management** — all trips across all users, filter by status
- Top destinations bar chart (Chart.js)

---

## 🌐 APIs Used

| API | Purpose | Key Required | Cost |
|---|---|---|---|
| **Nominatim (OSM)** | City geocoding + autocomplete | ❌ No | Free |
| **Overpass API** | Real tourist attractions near coordinates | ❌ No | Free |
| **OSRM** | Real road distance + drive time | ❌ No | Free |
| **OpenFreeMap** | MapLibre tile layers | ❌ No | Free |
| **OpenWeatherMap** | Current + 7-day forecast | ✅ Yes (free tier) | 1,000 calls/day free |
| **IBM watsonx.ai** | Granite AI itinerary generation | ✅ Yes (IBM Cloud) | Lite tier free |
| **Unsplash Source** | Attraction/destination photos | ❌ No | Free (no key) |

---

## 🗄 Database Schema

SQLite database at `backend/database/travel_planner.db` — auto-created on first run.

```sql
users (
  id, name, email, password_hash, salt,
  role,           -- 'user' | 'admin'
  created_at, last_login
)

trips (
  id, user_id, destination,
  start_date, end_date, num_days, budget,
  num_travelers, travel_style, transport,
  interests_json, special_requirements_json,
  itinerary_json,   -- IBM Granite output
  weather_json,     -- OpenWeatherMap output
  budget_json,      -- AI budget breakdown
  hotels_json,      -- AI hotel recommendations
  status,           -- 'active' | 'completed' | 'cancelled'
  created_at, updated_at
)

saved_trips (
  id, user_id, trip_id, notes, saved_at
)

expenses (
  id, trip_id, category, amount, description, created_at
)

travel_history (
  id, user_id, destination, visited_date, rating, notes
)
```

---

## ⚙️ Environment Variables

File: `.env` (gitignored — create from `.env.example`)

```env
# Flask
SECRET_KEY=your-secure-random-key-here
FLASK_ENV=development

# IBM Granite / watsonx.ai (optional — app works without these)
IBM_API_KEY=your_ibm_cloud_api_key
IBM_PROJECT_ID=your_watsonx_project_id
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
GRANITE_MODEL_ID=ibm/granite-4-h-small

# OpenWeatherMap (optional — weather features disabled without this)
WEATHER_API_KEY=your_openweathermap_api_key

# Currency Exchange (optional — not actively wired in UI yet)
EXCHANGE_API_KEY=your_exchangerate_api_key
```

### What works without API keys:
- ✅ Full Smart Wizard (all 10 steps) — real geocoding, real attractions, real map, real routing
- ✅ All destination pages
- ✅ Dashboard, authentication, saved trips
- ✅ PDF download of existing trips
- ⚠️ Weather chips show "unavailable" message (graceful fallback)
- ⚠️ IBM Granite trip generation uses demo/fallback itinerary data

---

## 🧱 Tech Stack Summary

**Frontend**
- HTML5 + CSS3 (custom glassmorphism design system)
- Bootstrap 5.3.3
- Bootstrap Icons 1.11.3
- Google Fonts — Inter (300–800)
- **MapLibre GL 4.5.0** — real interactive maps
- **Chart.js 4.4.4** — pie, doughnut, bar charts
- Vanilla JavaScript ES6+ (no framework)

**Backend**
- Python 3.10+
- **Flask 3.0.3** with Blueprint architecture (MVC)
- Werkzeug 3.0.4
- SQLite (Python stdlib `sqlite3`)
- **ReportLab 4.2.5** — PDF generation
- python-dotenv 1.0.1
- requests 2.32.3
- gunicorn 22.0.0 (production WSGI)
- ibm-watson 8.1.0 + ibm-cloud-sdk-core 3.22.0

**AI / IBM Cloud**
- IBM Granite (`ibm/granite-4-h-small`) via REST to IBM watsonx.ai
- IBM Cloud IAM token authentication (auto-refresh)

---

## 🔗 URL Map

| URL | Auth | Description |
|---|---|---|
| `/` | Public | Landing page |
| `/auth/register` | Public | Registration form |
| `/auth/login` | Public | Login form |
| `/auth/logout` | Login | Logout + redirect |
| `/auth/profile` | Login | User profile |
| `/dashboard` | Login | Dashboard with stats |
| `/planner/wizard` | Login | 10-step Smart Wizard |
| `/planner/destinations` | Public | Destinations explorer |
| `/planner/destinations/<slug>` | Public | Destination detail (10 destinations) |
| `/planner/new` | Login | IBM Granite AI planner form |
| `/planner/<id>` | Login | Trip view (7 tabs) |
| `/planner/<id>/pdf` | Login | Download PDF |
| `/planner/<id>/delete` | Login | Delete trip |
| `/planner/<id>/save` | Login | Save to favourites |
| `/planner/<id>/expense` | Login | Add expense entry |
| `/planner/saved` | Login | Saved trips list |
| `/planner/api/weather/<city>` | Public | JSON weather endpoint |
| `/admin` | Admin | Admin dashboard |
| `/admin/users` | Admin | User management |
| `/admin/trips` | Admin | Trip management |

---

## 🎨 UI / Design System

**Design Language**: Glassmorphism + Neumorphism accents  
**Color Palette**:

| Token | Value | Usage |
|---|---|---|
| `--wizard-accent` | `#0062FF` | IBM Blue — primary actions, active states |
| `--grad-ocean` | `#0062FF → #0098db` | Primary gradient buttons, timeline headers |
| `--grad-primary` | `#667eea → #764ba2` | Wizard step cards |
| `--grad-nature` | `#43e97b → #38f9d7` | Attraction pins, nature badges |
| `--grad-gold` | `#f6d365 → #fda085` | Budget/analytics cards |
| `--grad-sunset` | `#f093fb → #f5576c` | Expense/warning cards |
| `--step-done` | `#10b981` | Completed wizard steps |

**Components built:**
- Glassmorphism cards (backdrop-filter blur)
- Animated progress tracker with connectors
- Breadcrumb navigation
- Autocomplete dropdown
- Transport + Style tile selectors
- Attraction cards with image overlay + badges
- Floating itinerary sidebar
- Drag-and-drop day planner columns
- Side drawer (slides from right)
- MapLibre live map with custom pins
- Skeleton loading cards
- Analytics gradient cards with icon watermarks
- Toast notifications
- Animated range slider
- Month weather grid
- Hotel tier cards with amenity chips
- Scroll-reveal animations (IntersectionObserver)
- `@media print` clean Trip Overview

---

## 🔮 Known Gaps / Future Improvements

| Area | Gap | Effort |
|---|---|---|
| **Security** | Password hashing uses SHA-256+salt (should be bcrypt) | Low |
| **Security** | No CSRF tokens on forms (Flask-WTF not added) | Low |
| **Security** | No rate limiting on login/register endpoints | Low |
| **Wizard** | `travel_history` DB table exists but no routes use it | Low |
| **Wizard** | MapLibre tile server (openfreemap.org) is third-party — add fallback | Low |
| **AI** | IBM Granite model ID may need updating per account region | Low |
| **Currency** | `EXCHANGE_API_KEY` slot exists in config but not wired to any UI | Medium |
| **Wizard** | Overpass API has rate limits — add caching layer | Medium |
| **Auth** | No "Forgot Password" / email verification flow | Medium |
| **Maps** | OSRM public instance has rate limits — add retry + timeout | Medium |
| **Deployment** | Docker image / Dockerfile not present | Medium |

---

## 👤 Creating an Admin Account

```python
cd TravelPlannerAgent
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from backend.models.user import create_user
    create_user('Admin', 'admin@example.com', 'Admin@1234', role='admin')
    print('Admin user created')
"
```

Then login at **http://localhost:5000/auth/login** — the `/admin` link will appear in the navbar.

---

## 🧪 Quick Smoke Tests

```bash
# Verify all templates parse
python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('frontend/templates'))
for t in ['planner/wizard.html','planner/destinations.html','planner/destination_detail.html','dashboard/dashboard.html','home.html','base.html']:
    env.get_template(t); print('OK:', t)
"

# Verify all routes respond
python -c "
from app import create_app
app = create_app()
c = app.test_client()
for p in ['/', '/planner/destinations', '/planner/destinations/coorg', '/planner/destinations/spiti', '/planner/destinations/manali', '/planner/destinations/jaipur', '/planner/destinations/kerala', '/planner/destinations/rishikesh', '/planner/destinations/andaman', '/planner/destinations/varanasi', '/planner/destinations/ranthambore']:
    r = c.get(p); print(r.status_code, p)
"
```

Expected output — all `200 OK` for public routes, `302` for auth-protected routes.

---

## 📦 Install & Setup from Scratch

```bash
# 1. Clone / unzip the project
cd TravelPlannerAgent

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
# (Windows PowerShell)
@"
SECRET_KEY=dev-secret-key-change-in-production
FLASK_ENV=development
"@ | Out-File -FilePath .env -Encoding utf8

# Optional — add to .env for full AI + weather features:
# IBM_API_KEY=your_key
# IBM_PROJECT_ID=your_project_id
# WEATHER_API_KEY=your_owm_key

# 5. Run
python app.py
# → http://localhost:5000
```

---

*Last updated: July 2025 — AI Travel Planner Agent v2.0*  
* · Built with Flask + IBM Granite + MapLibre GL*
