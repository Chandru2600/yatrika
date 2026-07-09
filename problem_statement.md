# Problem Statement: AI-Powered Travel Planner Agent

## 📌 Project Title
**AI-Powered Travel Planner Agent**

## 🌐 Project Domain
**Travel, Tourism & Hospitality / Intelligent Agent Systems**

---

## 🔍 Context & Background
Planning a vacation or a business trip is historically a highly fragmented, time-consuming, and exhausting process. Travelers must toggle between dozens of platforms—comparing flights and hotels, mapping locations, checking local weather forecasts, calculating multi-currency budgets, and researching regional attractions. 

Without a cohesive, integrated planner, itineraries are manually compiled in notebooks or static spreadsheets. These manual methods fail to account for:
- Live weather constraints (e.g., planning outdoor visits during heavy rain).
- Optimal route connections between consecutive sightseeing spots (leading to back-and-forth travel).
- Real-time pricing breakdowns across accommodation, meals, transit, and entry fees.
- Granular personalization matching the traveler’s distinct preference style (nature, spiritual, adventure, budget, luxury).

---

## ⚠️ The Problem Statement
How can we build an intelligent, integrated digital travel assistant that autonomously structures complete daily travel schedules, computes accurate driving routes, estimates category-wise expenses, recommends local highlights, and delivers real-time weather alerts—all tailored to a single set of user budget and style inputs, eliminating fragmented search workflows?

---

## 💡 The Objective
The core goal of this project is to develop the **AI-Powered Travel Planner Agent**—a full-stack web application designed to orchestrate two complementary workflows:
1. **API-Driven Smart Travel Wizard:** A 10-step interactive planner utilizing public geographic APIs (Nominatim, Overpass, OSRM, MapLibre GL) to build maps, locate attractions, compute actual driving routes, and structure drag-and-drop daily schedules without requiring AI generation credits.
2. **IBM watsonx.ai Agentic Planner:** A generative AI pipeline using **IBM Granite** (`ibm/granite-4-h-small`) to process user requirements and produce structured, JSON-parsed day-wise itineraries, tiered lodging options, transport recommendations, and itemized budget estimates.

---

## 🏗️ Core Solution Modules
To resolve the problem, the agent incorporates the following specialized components:
* **City Selection & Autocomplete:** Resolves source and destination inputs with coordinates using geocoders.
* **POI (Point of Interest) Miner:** Queries OpenStreetMap (via Overpass API) to locate authentic attractions near the destination.
* **Route Optimizer:** Computes OSRM road distance, transit duration, and fuel costs between each scheduled attraction.
* **Interactive Map Viewer:** Uses MapLibre GL to plot attraction pins, starter hotels, and route polylines.
* **Manual Expense Tracker:** Enables users to log actual travel spending and visualizes budget compliance via Chart.js.
* **Offline PDF Exporter:** Uses ReportLab to compile the complete itinerary into a clean, downloadable PDF report.

---

## 🛠️ Technology Stack
- **Web Framework:** Flask (Python) with a Blueprint MVC architecture.
- **Frontend Layer:** HTML5, CSS3 (custom glassmorphic theme), Bootstrap 5.3, Vanilla JavaScript (ES6+).
- **AI Core:** IBM watsonx.ai REST API, IBM Granite model (`ibm/granite-4-h-small`), IAM Token authentication.
- **Database Layer:** SQLite (via Python stdlib `sqlite3`) tracking user credentials (hashed via SHA-256), travel plans, expenses, and reviews.
- **Mapping & Charts:** MapLibre GL, Chart.js.
