# AI Travel Planner Agent — <div align="center">

**AI-powered travel planning using IBM Granite through IBM watsonx.ai**

[![IBM Granite](https://img.shields.io/badge/IBM-Granite-0062FF?logo=ibm&logoColor=white)](https://www.ibm.com/granite)
[![watsonx.ai](https://img.shields.io/badge/IBM-watsonx.ai-6929C4?logo=ibm&logoColor=white)](https://www.ibm.com/watsonx)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-000000?logo=flask)](https://flask.palletsprojects.com)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap)](https://getbootstrap.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📌 Project Overview

**Live Website:** [cmloni.pythonanywhere.com](https://cmloni.pythonanywhere.com)

The **AI Travel Planner Agent** is a full-stack web application that uses **IBM Granite** (via **IBM watsonx.ai**) to generate complete, personalized travel itineraries. Users enter their destination, dates, budget, and preferences — and the AI produces a comprehensive travel plan including day-wise schedules, hotel recommendations, budget breakdowns, weather forecasts, interactive maps, and a downloadable PDF report.

---

## ✨ Features

| Module | Description |
|---|---|
| 🤖 **AI Itinerary** | IBM Granite generates day-wise plans with morning/afternoon/evening slots |
| 🌤 **Weather Module** | Real-time & 7-day forecast via OpenWeatherMap |
| 🗺 **Interactive Map** | MapLibre + OpenStreetMap showing attractions, hotels, hospitals |
| 💰 **Budget Planner** | Auto-breakdown across accommodation, food, transport, tickets |
| 🏨 **Hotel Finder** | Budget, mid-range & luxury hotel AI recommendations |
| 🚌 **Transport Guide** | Flight, train, bus, metro recommendations with costs |
| 🎒 **Packing Assistant** | Destination-specific checklist |
| 🍜 **Local Food Guide** | Must-try dishes, restaurants, street food |
| 📄 **PDF Export** | Full itinerary export as professional PDF |
| 💳 **Expense Tracker** | Manual expense logging with chart visualization |
| ⭐ **Saved Trips** | Save, manage, and revisit trip plans |
| 🛡 **Admin Panel** | User management, analytics, top destinations chart |

---

## 🏗 Tech Stack

**Frontend**
- HTML5, CSS3, Bootstrap 5.3
- JavaScript (Vanilla ES6+)
- Chart.js 4.4 — pie and bar charts
- MapLibre GL — interactive maps
- OpenStreetMap / Nominatim — geocoding & tile layers

**Backend**
- Python 3.10+
- Flask 3.0 with Blueprints (MVC architecture)
- SQLite (via Python stdlib `sqlite3`)
- ReportLab — PDF generation

**AI / IBM Cloud**
- IBM Granite 13B Instruct (`ibm/granite-13b-instruct-v2`)
- IBM watsonx.ai REST API
- IBM Cloud IAM Token authentication

**External APIs**
- OpenWeatherMap API — weather data
- ExchangeRate API — currency conversion
- Nominatim (OpenStreetMap) — free geocoding

---

## 📁 Project Structure

```
TravelPlannerAgent/
│
├── app.py                          # Flask application factory (entry point)
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
│
├── backend/
│   ├── config.py                   # App configuration (dev/prod/test)
│   ├── database/
│   │   └── db.py                   # SQLite init, query helpers
│   ├── models/
│   │   ├── user.py                 # User CRUD + auth helpers
│   │   └── trip.py                 # Trip CRUD, saved trips, expenses
│   ├── routes/
│   │   ├── auth_routes.py          # /auth — register, login, logout
│   │   ├── main_routes.py          # / and /dashboard
│   │   ├── planner_routes.py       # /planner — new trip, view, PDF, map
│   │   └── admin_routes.py         # /admin — users, trips, analytics
│   └── services/
│       ├── granite/
│       │   └── granite_service.py  # IBM Granite API + prompt templates
│       ├── weather/
│       │   └── weather_service.py  # OpenWeatherMap integration
│       └── pdf/
│           └── pdf_service.py      # ReportLab PDF generator
│
├── frontend/
│   ├── templates/
│   │   ├── base.html               # Master template (navbar, footer, flash)
│   │   ├── home.html               # Landing page
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── dashboard/
│   │   │   └── dashboard.html
│   │   ├── planner/
│   │   │   ├── new_trip.html       # Multi-step planner form
│   │   │   ├── view_trip.html      # Full itinerary view (7 tabs)
│   │   │   └── saved_trips.html
│   │   └── admin/
│   │       └── dashboard.html
│   └── static/
│       ├── css/
│       │   └── main.css            # Complete custom CSS (~560 lines)
│       └── js/
│           ├── main.js             # Dark mode, flash, shared utilities
│           ├── planner.js          # Multi-step form logic
│           └── trip_view.js        # Charts, MapLibre map, expense chart
│
└── docs/
    └── README.md                   # This file
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10 or higher
- An [IBM Cloud account](https://cloud.ibm.com/registration) (Lite tier is free)
- An [OpenWeatherMap API key](https://openweathermap.org/api) (free tier)

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd TravelPlannerAgent
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
IBM_API_KEY=your_ibm_cloud_api_key
IBM_PROJECT_ID=your_watsonx_project_id
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
GRANITE_MODEL_ID=ibm/granite-13b-instruct-v2
WEATHER_API_KEY=your_openweathermap_key
SECRET_KEY=your-secure-random-secret-key
```

### 3. Run the Application

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 🔑 IBM Cloud Setup Guide

### Step 1: Create IBM Cloud Account
1. Go to [https://cloud.ibm.com/registration](https://cloud.ibm.com/registration)
2. Sign up for a **Lite (free)** account

### Step 2: Create an API Key
1. Go to **Manage → Access (IAM) → API keys**
2. Click **Create an IBM Cloud API key**
3. Copy the API key — you won't see it again
4. Paste it as `IBM_API_KEY` in your `.env` file

### Step 3: Create a watsonx.ai Project
1. Go to [https://dataplatform.cloud.ibm.com](https://dataplatform.cloud.ibm.com)
2. Click **New project → Create an empty project**
3. Copy the **Project ID** from Settings
4. Paste it as `IBM_PROJECT_ID` in your `.env` file

### Step 4: Verify Granite Access
- The model `ibm/granite-13b-instruct-v2` is available on Lite tier
- URL for US-South: `https://us-south.ml.cloud.ibm.com`

---

## 🌤 OpenWeatherMap Setup

1. Register at [https://openweathermap.org/api](https://openweathermap.org/api)
2. Go to **API Keys** in your account
3. Copy the default API key (or create a new one)
4. Paste it as `WEATHER_API_KEY` in your `.env`
5. The free tier supports **1,000 calls/day** — sufficient for development

---

## 🗄 Database

SQLite database is created automatically at first run:
`backend/database/travel_planner.db`

**Tables:**
- `users` — registration, auth, roles
- `trips` — trip data including AI-generated JSON blobs
- `saved_trips` — user favourites with notes
- `travel_history` — trip ratings and reviews
- `expenses` — manual expense tracking per trip

To create an admin user, run Python directly:

```python
python -c "
from backend.database.db import init_db
from backend.models.user import create_user
init_db()
create_user('Admin', 'admin@example.com', 'Admin@1234', role='admin')
print('Admin created')
"
```

---

## 🚀 Deployment

### IBM Cloud Foundry (Lite)

```bash
# Login to IBM Cloud
ibmcloud login

# Target Cloud Foundry
ibmcloud target --cf

# Create a Procfile
echo "web: gunicorn app:create_app()" > Procfile

# Create manifest.yml
cat > manifest.yml << EOF
applications:
- name: ai-travel-planner
  memory: 256M
  instances: 1
  buildpacks:
    - python_buildpack
  command: gunicorn "app:create_app()"
  env:
    IBM_API_KEY: YOUR_KEY
    IBM_PROJECT_ID: YOUR_PROJECT
    WEATHER_API_KEY: YOUR_WEATHER_KEY
    SECRET_KEY: YOUR_SECRET
EOF

# Push
ibmcloud cf push
```

### IBM Code Engine

```bash
# Build image (requires Docker)
docker build -t ai-travel-planner .

# Push to IBM Container Registry
ibmcloud cr push us.icr.io/<namespace>/ai-travel-planner

# Deploy
ibmcloud ce application create \
  --name ai-travel-planner \
  --image us.icr.io/<namespace>/ai-travel-planner \
  --port 5000 \
  --env IBM_API_KEY=xxx \
  --env IBM_PROJECT_ID=xxx
```

---

## 🧪 Testing

```bash
# Check all routes
python -c "
from app import create_app
app = create_app()
with app.test_client() as c:
    for rule in app.url_map.iter_rules():
        print(rule)
"

# Test Granite connection (requires valid IBM keys)
python -c "
from backend.services.granite.granite_service import call_granite
result = call_granite('Say hello in one sentence.')
print(result)
"

# Test weather service
python -c "
from backend.services.weather.weather_service import get_current_weather
print(get_current_weather('Paris'))
"
```

---

## 🔧 Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` from Granite | Invalid IBM API key | Re-generate key in IBM Cloud IAM |
| `404 Not Found` from watsonx | Wrong project ID or region URL | Verify project ID and URL matches your region |
| `Weather data unavailable` | Invalid/expired weather key | Check OpenWeatherMap dashboard |
| `ModuleNotFoundError: reportlab` | Missing dependency | Run `pip install reportlab` |
| Database error on first run | Permissions issue | Run `mkdir -p backend/database` first |
| `CSRF` or session errors | Missing `SECRET_KEY` | Set `SECRET_KEY` in `.env` |

---

## 🏛 Architecture

```
Browser → Flask (app.py)
           ├── Routes (Blueprints)
           │   ├── auth_routes  → User Model   → SQLite
           │   ├── main_routes  → Dashboard
           │   ├── planner_routes → Granite Service → IBM watsonx.ai
           │   │                → Weather Service → OpenWeatherMap
           │   │                → PDF Service    → ReportLab
           │   └── admin_routes → Analytics
           └── Templates (Jinja2 + Bootstrap 5)
```

---

## 📖 IBM Granite Prompts

The system uses **4 optimized prompts** per trip generation:

1. **Itinerary Prompt** — Day-wise schedule with morning/afternoon/evening slots, food, tips
2. **Budget Prompt** — Detailed cost breakdown with percentage allocations
3. **Hotel Prompt** — Tiered recommendations (budget/mid-range/luxury) with amenities
4. **Transport Prompt** — Mode comparisons with cost and time estimates

All prompts request **structured JSON output** for reliable parsing.

---

## 👨‍💻 Author
AI Travel Planner Agent using IBM Granite and IBM Cloud Lite

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
