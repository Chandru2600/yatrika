# System Architecture & Technical Specifications
## TravelPlannerAgent — Cooperative Multi-Agent Travel Planning System

---

## 1. System Overview & Core Philosophy

The **TravelPlannerAgent** is a production-grade full-stack travel planning platform tailored for Indian tourism. Unlike traditional generic travel tools that plan trips to abstract city borders, this system is built on the **"Stay-First Anchor" (Base Camp)** paradigm:

```
Traditional Flow:   Origin ───────> Generic City Center ───────> Where do I sleep? ───────> Random POIs
Stay-First Flow:    Origin ───────> Base Camp Stay (Hotel/Homestay) ───────> Circular Daily Loops ───> Return to Stay
```

### Core Tenets:
1. **Base Camp Selection First (Agent 4):** A verified hotel, resort, or homestay is anchored first using K-Means safety and budget clustering from a 150,000+ Indian hotel dataset.
2. **Door-to-Door Multimodal Transit (Agent 1):** Transit is computed from the traveler's doorstep directly to the gate of the Base Camp stay—incorporating trains, connecting ghat shuttles, state RTC buses, toll estimations, and mountain transfers.
3. **Circular Daily Sightseeing Loops (Agent 2):** Daily itineraries depart from and return to the Base Camp each morning and evening without back-and-forth backtracking.
4. **Machine Learning Budget Feasibility (Agent 3):** Trip expenses are benchmarked against a trained Random Forest Regressor ($R^2 = 90.92\%$) trained on 25,000 trips.
5. **Generative AI Synthesis:** IBM watsonx.ai (**IBM Granite** `ibm/granite-4-h-small`) provides culturally rich itineraries, local customs, and regional advice.

---

## 2. End-to-End Data Flow & Architecture Diagram

### 5-Stage Data Flow (Input ➔ Datasets ➔ 4 Agents ➔ IBM Granite LLM ➔ Output Dossier)

![Intelligent Travel Recommendation System 5-Stage Data Flow](ml_evaluation_charts/detailed_dataflow_architecture.jpg)

### Comprehensive Technical Blueprint & Subsystem Data Flow

![Deep Technical Blueprint Architecture](ml_evaluation_charts/deep_technical_architecture.jpg)

*This blueprint highlights the exact datasets, ML algorithms (K-Means, Random Forest Classifier, Random Forest Regressor R²=90.92%), Grounded IBM Granite prompt assembly, and database persistence schemas.*

---



## 3. High-Level Layered Architecture Diagram


```mermaid
graph TD
    %% Styling
    classDef client fill:#EBF3FF,stroke:#0F62FE,stroke-width:2px,color:#001D6C;
    classDef flask fill:#EDF5FF,stroke:#0043CE,stroke-width:2px,color:#001D6C;
    classDef agents fill:#F4F1FB,stroke:#8A3FFC,stroke-width:2px,color:#311166;
    classDef ml fill:#DEFBE6,stroke:#198038,stroke-width:2px,color:#044317;
    classDef external fill:#FFF0F1,stroke:#DA1E28,stroke-width:2px,color:#750E13;
    classDef data fill:#F2F4F8,stroke:#4D5358,stroke-width:2px,color:#21272A;

    subgraph Layer1["1. Presentation Layer (Frontend Client)"]
        UI_Home["Landing & Destination Explorer"]:::client
        UI_Wizard["10-Step Smart Travel Wizard<br/>(Interactive MapLibre GL & Overpass API)"]:::client
        UI_Planner["Fast Multi-Agent Form<br/>(1-Click Itinerary Generator)"]:::client
        UI_Dashboard["User Dashboard & Expense Tracker<br/>(Chart.js Analytics)"]:::client
        UI_PDF["PDF Export Engine (ReportLab)"]:::client
    end

    subgraph Layer2["2. Application Controller Layer (Flask Blueprints)"]
        App["Flask Core Application Factory (app.py)"]:::flask
        BP_Auth["auth_bp (/auth)<br/>Session & SHA-256 Auth"]:::flask
        BP_Main["main_bp (/)<br/>Dashboard & Overview"]:::flask
        BP_Planner["planner_bp (/planner)<br/>Trip Orchestration & API Endpoints"]:::flask
        BP_API["api_bp (/api)<br/>REST Endpoints for AJAX"]:::flask
        BP_Admin["admin_bp (/admin)<br/>Platform Analytics"]:::flask
    end

    subgraph Layer3["3. Cooperative 4-Agent Planning Engine"]
        Orchestrator["MultiAgentCooperativePipeline<br/>(cooperative_pipeline.py)"]:::agents
        
        Agent4["Agent 4: Accommodations & Safety<br/>• Selects Base Camp Anchor<br/>• 150k Indian Hotel Dataset"]:::agents
        Agent1["Agent 1: Geospatial & Transit<br/>• Door-to-Door Routing<br/>• Ixigo Multimodal Engine"]:::agents
        Agent2["Agent 2: Itinerary Scheduling<br/>• Daily Circular Sightseeing Loops<br/>• 10,025 Attraction Dataset"]:::agents
        Agent3["Agent 3: Budget & Expense<br/>• Financial Allocation Breakdown<br/>• Budget Feasibility Scoring"]:::agents
    end

    subgraph Layer4["4. Machine Learning & Generative AI Layer"]
        Model_KMeans["K-Means Hotel Clusterer<br/>(hotel_kmeans_model.pkl)<br/>Trained on 12k stays"]:::ml
        Model_Classifier["Random Forest POI Classifier<br/>(attraction_classifier_rf.pkl)<br/>Trained on 1,560 places"]:::ml
        Model_Regressor["Random Forest Budget Regressor<br/>(trip_budget_rf_model.pkl)<br/>R² = 90.92% on 25k Trips"]:::ml
        LLM_Granite["IBM watsonx.ai Granite LLM<br/>(ibm/granite-4-h-small)<br/>Culturally Tailored Insights"]:::ml
    end

    subgraph Layer5["5. Services & External Integration Layer"]
        Svc_Transit["Transit Service<br/>(Train, Bus, Cab, Flight Tariffs)"]:::external
        Svc_Weather["Weather Service<br/>(OpenWeatherMap Forecasts)"]:::external
        Svc_OSRM["OSRM Driving Router<br/>(Real Highway Polylines)"]:::external
        Svc_OSM["OpenStreetMap / Overpass API<br/>(Live Geocoding & POI Mining)"]:::external
        Svc_PDF["ReportLab PDF Generator<br/>(Offline Travel Dossier)"]:::external
    end

    subgraph Layer6["6. Persistence & Data Layer"]
        DB[(SQLite Database<br/>travel_planner.db)]:::data
        Datasets["Evaluated Datasets:<br/>1. 10k Attractions CSV<br/>2. 150k Hotels CSV<br/>3. RTC Bus Tariff Slabs<br/>4. 25k Budget Simulations"]:::data
    end

    %% Flow Connections
    UI_Wizard --> BP_Planner
    UI_Planner --> BP_Planner
    UI_Dashboard --> BP_Main
    UI_Home --> BP_Main

    BP_Planner --> Orchestrator
    BP_Planner --> Svc_Weather
    BP_Planner --> Svc_PDF
    BP_Planner --> DB

    Orchestrator --> Agent4
    Agent4 --> Model_KMeans
    Agent4 --> Datasets
    Agent4 -.->|Step 1: Yields Base Camp Stay| Agent1

    Agent1 --> Svc_Transit
    Agent1 --> Svc_OSRM
    Agent1 -.->|Step 2: Yields Transit Legs & POI Matrix| Agent2

    Agent2 --> Model_Classifier
    Agent2 --> Datasets
    Agent2 -.->|Step 3: Yields Circular Day Loops| Agent3

    Agent3 --> Model_Regressor
    Agent3 --> DB

    Orchestrator -.->|Fallback / Cultural Polish| LLM_Granite
    Svc_Weather --> External_OWM["OpenWeatherMap API"]:::external
    Svc_OSRM --> External_OSRM["Project OSRM Servers"]:::external
```

---

## 3. Cooperative Multi-Agent Execution Sequence

The cooperative multi-agent pipeline coordinates four specialized AI agents in a strictly orchestrated dependency graph:

```mermaid
sequenceDiagram
    autonumber
    actor User as Traveler
    participant Web as Web Frontend / Wizard
    participant Controller as Flask Planner Controller
    participant Pipeline as Multi-Agent Orchestrator
    participant Agent4 as Agent 4 (Accommodations & Safety)
    participant Agent1 as Agent 1 (Geospatial & Transit)
    participant Agent2 as Agent 2 (Itinerary Scheduling)
    participant Agent3 as Agent 3 (Budget & Expense ML)
    participant LLM as IBM Granite LLM (watsonx.ai)
    participant DB as SQLite Database

    User->>Web: Submit Trip Inputs (Origin, Destination, Dates, Budget, Travelers, Style)
    Web->>Controller: POST /planner/new or /planner/save_wizard
    Controller->>Pipeline: run_pipeline(trip_input)

    Note over Pipeline,Agent4: STEP 1: ANCHOR BASE CAMP FIRST
    Pipeline->>Agent4: select_base_camp(dest, travel_style, max_price)
    Agent4->>Agent4: Run K-Means safety & pricing clustering (150k hotel dataset)
    Agent4-->>Pipeline: Return Base Camp Stay (Name, GPS coords, Safety Score, Address)

    Note over Pipeline,Agent1: STEP 2: DOOR-TO-DOOR TRANSIT TO BASE CAMP
    Pipeline->>Agent1: calculate_door_to_door_transit(source, dest, base_camp_stay, mode)
    Agent1->>Agent1: Compute Ixigo Multimodal Chains (IRCTC Trains + Ghat Shuttles, RTC Buses, Self-drive tolls)
    Agent1->>Agent1: Calculate Stay-to-POIs distance matrix
    Agent1-->>Pipeline: Return Transit Legs, Arrival Time, Fuel/Tolls, POI Matrix

    Note over Pipeline,Agent2: STEP 3: CIRCULAR DAILY SIGHTSEEING LOOPS
    Pipeline->>Agent2: schedule_multiday_itinerary(dest, num_days, base_camp_stay, enriched_pois)
    Agent2->>Agent2: Run Random Forest Attraction Classifier & Cluster Spots by Proximity
    Agent2-->>Pipeline: Return Daily Schedules (Morning/Afternoon/Evening anchored to Stay)

    Note over Pipeline,Agent3: STEP 4: BUDGET REGRESSION & FINANCIAL FEASIBILITY
    Pipeline->>Agent3: calculate_stay_first_budget(budget, travelers, days, stay, transit_fare)
    Agent3->>Agent3: Run Random Forest Budget Regressor (90.9% R² on 25k trips)
    Agent3-->>Pipeline: Return Itemized Allocations, Benchmark Cost & Feasibility Score

    Pipeline->>LLM: Grounded Synthesis Prompt (Base Camp Stay + Transit Legs + POI Loops + Budget Limits)
    LLM-->>Pipeline: Return Enriched Storytelling Itinerary, Cultural Nuance, Local Phrases & Packing Guide

    Pipeline-->>Controller: Return Comprehensive Complete Itinerary Object
    Controller->>DB: Persist trip in 'trips' table (JSON payloads)
    Controller-->>Web: Redirect to /planner/trip/<trip_id> (Interactive View & Timeline)
    Web-->>User: Display Interactive Map, Timeline, Transit Tabs, and Budget Visualizer
```

---

## 4. Agent-Augmented LLM Flow (IBM Granite on watsonx.ai)

### The Neuro-Symbolic / Compound AI Pattern

A critical differentiator of this project is that **the 4 Specialized Agents feed their computed outputs directly as grounded context into the IBM Granite model**:

![Agent-Augmented LLM Flow for Travel Planning](ml_evaluation_charts/granite_agent_pipeline.jpg)

### Why This Architecture Eliminates Hallucination:
1. **Traditional Monolithic LLM (Prone to Failure):**
   * Prompting an LLM with only *"Plan a 3-day trip to Samse with ₹20,000"* causes it to invent non-existent hotels, guess inaccurate train tickets, and combine attractions that are hours apart.
2. **Our Agent-Augmented Pattern (Grounded & Deterministic):**
   * **Agent 4** supplies the verified hotel name, safety score (9.6/10), and nightly rate.
   * **Agent 1** supplies exact IRCTC train numbers, connecting KSRTC buses, and road toll distances.
   * **Agent 2** supplies real attraction names from the 10,025 ASI dataset arranged in circular loops.
   * **Agent 3** supplies the ML-predicted cost ($R^2 = 90.92\%$) and itemized category limits.
   * **IBM Granite (`ibm/granite-4-h-small`)** receives this rich structured payload and performs what LLMs do best: **Generative Cultural Synthesis**, crafting localized phrases, temple etiquette, weather-driven packing advice, and day-wise travel narratives without having to guess numbers or locations.

---

## 5. Multimodal Transit Engine Architecture (Ixigo-Style)


Transit does not stop at a generic bus station or rail terminal. It connects the origin all the way to the hotel doorway:

```mermaid
graph LR
    Origin["Origin City<br/>(e.g., Bengaluru / Hubballi)"]

    subgraph Mode1["🚆 Mode 1: Train + Mountain Connector"]
        T1["IRCTC Express Train<br/>(SBC to Kadur / Udupi)"] --> C1["Transfer Connector<br/>(Station Walk / Auto to Depot)"]
        C1 --> B1["KSRTC Ghat Bus<br/>(Kadur to Kalasa)"]
        B1 --> S1["Local Village Shuttle / Auto<br/>(Kalasa to Estate Gate)"]
    end

    subgraph Mode2["🚌 Mode 2: Direct State / Private Bus"]
        RTC["State RTC (Airavat / Rajahamsa)<br/>or Private (VRL / SRS Sleeper)"] --> S2["Town Connector / Auto"]
    end

    subgraph Mode3["🚗 Mode 3: Self-Drive & Dedicated Outstation Cab"]
        Cab["Doorstep Pickup Cab / Personal Car"] --> Tolls["NHAI Fastag Toll Plazas<br/>+ Petrol Consumption (₹102.86/L)"]
    end

    subgraph Mode4["✈️ Mode 4: Flight + Road Transfer"]
        Fly["IndiGo / Air India to Nearest Airport<br/>(e.g., IXE Mangalore)"] --> GhatCab["Mountain Ghat Cab Transfer<br/>(Charmadi / Shiradi Ghat)"]
    end

    BaseCamp["🏡 BASE CAMP STAY<br/>(Hotel / Homestay / Resort Entrance)"]

    Origin --> Mode1 --> BaseCamp
    Origin --> Mode2 --> BaseCamp
    Origin --> Mode3 --> BaseCamp
    Origin --> Mode4 --> BaseCamp
```

---

## 5. Database Entity-Relationship (ER) Diagram

The SQLite database (`travel_planner.db`) provides persistence for user profiles, trip records, expenses, and reviews:

```mermaid
erDiagram
    USERS ||--o{ TRIPS : "creates"
    USERS ||--o{ SAVED_TRIPS : "bookmarks"
    USERS ||--o{ TRAVEL_HISTORY : "reviews"
    TRIPS ||--o{ EXPENSES : "logs"
    TRIPS ||--o{ SAVED_TRIPS : "referenced_in"
    TRIPS ||--o{ TRAVEL_HISTORY : "referenced_in"

    USERS {
        int id PK
        string name
        string email UK
        string password
        string role
        string avatar
        datetime created_at
        datetime last_login
    }

    TRIPS {
        int id PK
        int user_id FK
        string destination
        date start_date
        date end_date
        int num_days
        float budget
        int num_travelers
        string travel_style
        string transport
        string transit_mode
        float transit_cost
        string arrival_time
        text transit_details_json
        string interests
        string special_requirements
        text itinerary_json
        text weather_json
        text budget_json
        text hotels_json
        string status
        datetime created_at
        datetime updated_at
    }

    EXPENSES {
        int id PK
        int trip_id FK
        string category
        float amount
        string description
        datetime date
    }

    SAVED_TRIPS {
        int id PK
        int user_id FK
        int trip_id FK
        datetime saved_at
        text notes
    }

    TRAVEL_HISTORY {
        int id PK
        int user_id FK
        int trip_id FK
        datetime visited_at
        int rating
        text review
    }
```

---

## 6. Machine Learning Models Specification

| Model Name | Type | Architecture / Estimator | Dataset Used | Benchmark Accuracy / Metric | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Trip Budget Regressor** | Supervised Regression | `RandomForestRegressor(n_estimators=100, max_depth=16)` + `MLPRegressor` | 25,000 Simulated Indian Trips | **$R^2 = 0.9092$ (90.92%)**, MAE = ₹1,120 | Accurately predicts total trip cost based on days, travelers, distance, mode, and hotel tier |
| **Attraction Recommendation Classifier** | Multi-class Classification | `RandomForestClassifier(n_estimators=100, max_depth=12)` | 1,560 Indian Tourist Attractions | **Accuracy = 84.6%** | Classifies and tags attraction types (Heritage, Nature, Spiritual, Beach, Adventure) |
| **Hotel Safety & Tier Clusterer** | Unsupervised Clustering | `KMeans(n_clusters=3)` with `StandardScaler` | 12,000 Stays (sampled from 150k dataset) | Inertia Convergence | Groups hotels into Budget, Balanced, and Luxury safety tiers |
| **Itinerary Synthesizer** | Generative AI LLM | **IBM Granite** (`ibm/granite-4-h-small`) | Prompt-Engineered Travel Ontology | Low latency via 2-call token caching | Synthesizes packing lists, cultural phrases, local etiquette, and emergency advisories |

---

## 7. How the Application Operates (Step-by-Step User Flow)

1. **User Authentication & Entry:**
   - The user visits `/` and logs in or creates an account via `/auth/login` (passwords hashed using SHA-256 with salts).
2. **Trip Selection & Initialization:**
   - The user enters origin, destination, dates, budget, travelers, and travel style.
   - The user can choose the **Fast 1-Click Multi-Agent Generator** or the **10-Step Interactive Wizard**.
3. **Base Camp Resolution (Agent 4):**
   - The system checks the destination against the 150,000 hotel dataset and selects the top safety-rated accommodation fitting the budget (e.g., *Bella Vista Tea Estate Homestay* in Samse/Kalasa).
4. **Door-to-Door Multimodal Transit (Agent 1):**
   - The transit engine resolves nearby train stations, bus terminals, airports, and road networks.
   - It computes full multi-leg journeys (e.g., Train to Kadur $\rightarrow$ Bus to Kalasa $\rightarrow$ Auto to Estate).
5. **Sightseeing Schedule Loops (Agent 2):**
   - Agent 2 fetches nearby attractions from the 10,025 tourist spots dataset, clusters them by proximity, and assigns them into morning, afternoon, and evening slots departing from and returning to the Base Camp.
6. **Budget Verification (Agent 3):**
   - The budget model verifies whether the user's allocated budget is sufficient, splits it into Stay (35%), Transit (25%), Meals (20%), Activities (12%), and Emergency Buffer (8%), and compares it with the trained ML regression benchmark.
7. **Weather Alerts & Packing Lists:**
   - Real-time weather is fetched via OpenWeatherMap to deliver weather warnings (e.g., monsoon rain gear).
   - Customized packing checklists and emergency contacts (Police: 100, Tourist Helpline: 1363) are prepared.
8. **Interactive Review & Modification:**
   - The user inspects the trip on an interactive MapLibre GL map, adjusts itineraries, and logs expenses.
9. **Export & Offline Use:**
   - The user can download a publication-ready PDF itinerary dossier generated dynamically via ReportLab.
