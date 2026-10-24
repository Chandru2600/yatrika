# Academic Project Report & 15-Week Work Breakdown Structure (WBS)
## Project Title: AI-Powered Travel Planner Agent (A Stay-First Compound Multi-Agent System for Indian Tourism Logistics)
**Domain:** Artificial Intelligence / Intelligent Agent Systems / Geospatial Optimization  
**Tech Stack:** Python (Flask), Scikit-Learn, IBM watsonx.ai (Granite), SQLite, MapLibre GL, ReportLab, OSRM  
**Affiliation/Context:** University Engineering Capstone / IBM University Engagement Project  

---

# PART 1: COMPREHENSIVE 15-WEEK PROJECT SCHEDULE & MILESTONES

```
+-----------------------------------------------------------------------------------------------------+
|                                   15-WEEK PROJECT PHASING TIMELINE                                  |
+-----------------------------------------------------------------------------------------------------+
| W1  | W2  | W3  | W4  | W5  | W6  | W7  | W8  | W9  | W10 | W11 | W12 | W13 | W14 | W15 |
| [Phase 1: Inception] | [Phase 2: Data & EDA] | [Phase 3: Multi-Agent ML] | [Phase 4: Dev & AI] | [Phase 5: Deploy & Viva] |
+-----------------------------------------------------------------------------------------------------+
```

| Phase | Weeks | Strategic Focus | Primary Objective |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Week 1 – 3 | **Requirement Analysis & Architecture** | Problem definition, literature review of OTA & LLM flaws, Stay-First architecture design |
| **Phase 2** | Week 4 – 6 | **Dataset Curation & Preprocessing** | Ingesting & cleaning 150k stays, 10k ASI spots, 8.9k rail stations, and 25k budget trips |
| **Phase 3** | Week 7 – 9 | **Mathematical & Multi-Agent ML Modeling** | K-Means stay clustering, OSRM transit chaining, RF Classifier & Regressor training |
| **Phase 4** | Week 10 – 12 | **IBM watsonx.ai Grounding & Full-Stack UI** | IBM Granite prompt engineering, Flask MVC backend, MapLibre GL, 10-step wizard |
| **Phase 5** | Week 13 – 15 | **Integration, Evaluation & Final Defense** | Model validation ($R^2$, MAE), PDF dossier exporter, cloud deployment, final viva |

---

### Phase 1: Problem Formulation, Literature Survey & Architecture (Weeks 1 – 3)

#### • Week 1: Problem Definition, Project Charter & Feasibility Study
- **Weekly Objective:** Formalize the project scope, analyze existing Indian tourism logistics limitations, and define project charter.
- **Key Tasks Completed:**
  - Researched fragmentation in Indian travel planning (siloed flights, IRCTC, state RTC buses, lack of last-mile mountain connectivity).
  - Drafted Problem Statement and System Feasibility Report.
  - Setup version control repository (`git`), virtual environment, and dependency baseline.
- **Deliverables:** Project Charter, Problem Statement Document, Baseline Environment Setup.

#### • Week 2: Literature Review & Architecture Conceptualization
- **Weekly Objective:** Evaluate limitations of monolithic LLMs (hallucinations, lack of spatial awareness) and design the "Stay-First Anchor" (Base Camp) concept.
- **Key Tasks Completed:**
  - Compared legacy OTA platforms vs. raw LLMs vs. Compound Multi-Agent systems.
  - Formulated the Stay-First Anchor paradigm: routing around verified lodging to eliminate backtracking itineraries.
  - Designed High-Level Multi-Agent Architecture (Agents 1 through 4 + IBM Granite).
- **Deliverables:** Literature Survey Matrix, High-Level Architecture Block Diagram.

#### • Week 3: Software Requirements Specification (SRS) & Database Modeling
- **Weekly Objective:** Finalize technical specifications, module interactions, and relational database schema.
- **Key Tasks Completed:**
  - Authored Software Requirements Specification (SRS) document (IEEE standard).
  - Designed Entity-Relationship (ER) model and SQLite relational schema (Users, Itineraries, Expenses, Stays, Bookmarks).
  - Defined REST API endpoints and data contracts between agent subsystems.
- **Deliverables:** Approved SRS Document, ER Diagram, SQLite Database Schema DDL.

---

### Phase 2: Data Engineering, Cleaning & Exploratory Data Analysis (Weeks 4 – 6)

#### • Week 4: Master Dataset Ingestion & Spatial Geocoding
- **Weekly Objective:** Collect and curate comprehensive Indian tourism, hospitality, and transit datasets.
- **Key Tasks Completed:**
  - Ingested 150,000 Indian hotels and homestays with GPS latitude/longitude.
  - Extracted 10,025 Archaeological Survey of India (ASI) tourist destinations.
  - Integrated 8,989 Indian Railway network stations and 3,000 state bus terminals.
- **Deliverables:** Raw datasets cataloged into `FACULTY_EVALUATION_DATASETS/` with schema validations.

#### • Week 5: Data Cleaning, Outlier Filtering & Normalization Pipelines
- **Weekly Objective:** Clean spatial anomalies, fill missing pricing metrics, and filter duplicate attractions.
- **Key Tasks Completed:**
  - Developed pandas data cleaning pipelines to sanitize coordinates, pricing tiers, and rating metrics.
  - Filtered duplicate and invalid coordinate pairs outside Indian territorial bounds.
  - Implemented one-hot encoding and feature scalers (`StandardScaler`, `MinMaxScaler`) for ML pipelines.
- **Deliverables:** Cleaned CSV datasets, Feature Engineering Python scripts, Preprocessing summary report.

#### • Week 6: Exploratory Data Analysis (EDA) & Transit Tariff Slabs
- **Weekly Objective:** Conduct statistical exploratory analysis and model state-wise bus and railway fare matrices.
- **Key Tasks Completed:**
  - Analyzed accommodation price distributions across budget, standard, and luxury tiers across Indian states.
  - Formulated fare rule matrices for state RTC bus networks (KSRTC, MSRTC, HRTC) and Fastag highway toll slabs.
  - Generated correlation heatmaps, feature distribution plots, and statistical benchmarks.
- **Deliverables:** EDA Notebooks, Statistical Summary Plots, Transit Tariff Matrix Tables.

---

### Phase 3: Machine Learning & Multi-Agent Algorithmic Modeling (Weeks 7 – 9)

#### • Week 7: Agent 4 (Accommodations & Safety) & Agent 1 (Geospatial Transit)
- **Weekly Objective:** Build K-Means clustering for safe lodging and OSRM transit network routing.
- **Key Tasks Completed:**
  - Developed **Agent 4 (Accommodations & Safety)** using unsupervised K-Means clustering across 150,000 stays to segment lodging by pricing and safety indices.
  - Implemented **Agent 1 (Geospatial & Multimodal Transit)** integrating Open Source Routing Machine (OSRM) to calculate door-to-door transit chains (air, rail, road).
  - Built last-mile connector logic linking terminal stations to mountain/remote lodging.
- **Deliverables:** Trained K-Means clustering model (`agent4_kmeans.pkl`), OSRM transit calculation service.

#### • Week 8: Agent 2 (Itinerary Scheduling Random Forest Classifier)
- **Weekly Objective:** Train machine learning model to recommend and order attractions in circular daily loops.
- **Key Tasks Completed:**
  - Formulated feature vector combining attraction category, dwell time, popularity score, and proximity to Base Camp.
  - Trained Random Forest Classifier on 10,025 ASI attractions achieving **84.6% classification accuracy**.
  - Implemented traveling salesperson (TSP) heuristic to guarantee non-overlapping circular daily routes.
- **Deliverables:** Trained Itinerary Random Forest Classifier model, Confusion matrix and ROC-AUC curves.

#### • Week 9: Agent 3 (Budget & Expense Random Forest Regressor)
- **Weekly Objective:** Train high-precision regression model for end-to-end trip financial feasibility.
- **Key Tasks Completed:**
  - Trained Random Forest Regressor on 25,000 simulated Indian travel expense profiles.
  - Optimized hyperparameters using Grid Search Cross-Validation, achieving **$R^2 = 90.92\%$** with low MAE.
  - Created budget breakdown engine allocating funds across accommodation, intercity travel, food, entry tickets, and safety reserves.
- **Deliverables:** Trained Budget Regressor model (`agent3_budget_rf.pkl`), Regression performance charts ($R^2$, RMSE, Residuals).

---

### Phase 4: watsonx.ai Integration, Dual Engine & Full-Stack Development (Weeks 10 – 12)

#### • Week 10: IBM watsonx.ai Foundation Model (Granite) Grounding
- **Weekly Objective:** Integrate IBM Granite LLM to synthesize cultural guidance without hallucinations.
- **Key Tasks Completed:**
  - Configured IBM watsonx.ai REST client with IAM Token authentication using **`ibm/granite-4-h-small`**.
  - Engineered zero-hallucination grounded prompts: feeding deterministic outputs of Agents 1–4 into Granite.
  - Generated cultural etiquette, local dialect phrases, dress code advisory, and weather-driven packing advice.
- **Deliverables:** watsonx.ai integration wrapper (`ibm_granite_service.py`), JSON schema validator, prompt templates.

#### • Week 11: Backend Architecture & Dual Operational Modes
- **Weekly Objective:** Build Flask modular MVC backend supporting AI Mode and Step-Wise Wizard Mode.
- **Key Tasks Completed:**
  - Implemented Flask Blueprint architecture (`auth_routes.py`, `planner_routes.py`, `main_routes.py`, `api_routes.py`).
  - Developed **Mode 1 (Autonomous AI Mode)**: single-click multi-agent pipeline generating full itineraries.
  - Developed **Mode 2 (Step-Wise Mode)**: interactive 10-step wizard with drag-and-drop itinerary reordering.
  - Implemented SHA-256 authenticated user sessions and SQLite transactional integrity.
- **Deliverables:** Functional Flask REST backend, API endpoint test collection, session authentication system.

#### • Week 12: Modern Glassmorphic Frontend & MapLibre GL Integration
- **Weekly Objective:** Develop rich interactive UI with vector mapping and dynamic telemetry.
- **Key Tasks Completed:**
  - Designed responsive glassmorphic UI using CSS custom tokens, Bootstrap 5.3, and dark/light accents.
  - Integrated **MapLibre GL** for vector map rendering, interactive attraction markers, and route polyline overlays.
  - Integrated **Chart.js** to render real-time expense telemetry, category distributions, and budget burn-down graphs.
  - Added sticky reveal footer and mobile-responsive navigation.
- **Deliverables:** Complete responsive web interface, interactive map modules, dynamic financial analytics dashboard.

---

### Phase 5: System Integration, PDF Dossier, Evaluation & Defense (Weeks 13 – 15)

#### • Week 13: ReportLab Dynamic PDF Exporter & Comprehensive System Testing
- **Weekly Objective:** Build offline travel dossier generation and conduct end-to-end unit and integration testing.
- **Key Tasks Completed:**
  - Implemented **ReportLab** PDF engine compiling day-by-day schedules, maps, emergency contacts, and expense tables into downloadable PDF travel dossiers.
  - Conducted end-to-end integration testing connecting frontend wizard, SQLite database, ML agents, and watsonx.ai.
  - Performed cross-browser testing and responsive viewport stress testing across mobile and desktop.
- **Deliverables:** PDF Generation engine (`pdf_generator.py`), Integration test suite with test execution reports.

#### • Week 14: Empirical Faculty Evaluation, Benchmarking & Deployment
- **Weekly Objective:** Run evaluation benchmarks against faculty test datasets and deploy system live.
- **Key Tasks Completed:**
  - Executed benchmark latency evaluations across all four agents and watsonx.ai runtime.
  - Documented verification evidence against all 8 faculty evaluation datasets (`FACULTY_EVALUATION_DATASETS`).
  - Deployed application to cloud hosting with environment variable security and live web links.
- **Deliverables:** System Benchmark Report, Comprehensive Architecture Document (`ARCHITECTURE.md`).

#### • Week 15: Final Documentation, Presentation & Project Defense
- **Weekly Objective:** Finalize project thesis, presentation slides, code repository cleanup, and final viva presentation.
- **Key Tasks Completed:**
  - Authored comprehensive 8-chapter Academic Project Report (`PROJECT_REPORT.md`).
  - Prepared final presentation slide deck (`TravelPlanner_Project_IBMUniversityEngagement.pptx`).
  - Performed final code audit, repository documentation (`README.md`, `TECHNICAL_EXPLANATION.md`), and mock viva demo.
- **Deliverables:** Complete Bound Project Report, Defense Slide Deck, Production Codebase, Final Project Sign-Off.

---

# PART 2: FORMAL WEEKLY PROGRESS REPORT FORM (WITH SIGNATURES)

*This standardized form can be printed or exported directly for weekly faculty review submissions.*

```
====================================================================================================
                        DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING
                           ACADEMIC PROJECT PROGRESS REPORT - WEEKLY
====================================================================================================
```

### 1. Project & Student Information
| Field | Details |
| :--- | :--- |
| **Project Title** | **AI-Powered Travel Planner Agent: A Stay-First Compound Multi-Agent System for Indian Tourism Logistics** |
| **Project ID / Code** | IBM-AI-TRV-2026-04 |
| **Student Name(s)** | ________________________________________________________________ |
| **Register / Roll No.** | ________________________________________________________________ |
| **Branch / Degree** | B.Tech / B.E. / M.C.A. — Computer Science & Engineering |
| **Academic Year / Sem** | 2025–2026 / Semester VIII |
| **Internal Guide / Supervisor** | ________________________________________________________________ |
| **Report Submission Date** | ______ / ______ / 2026 |
| **Reporting Week** | **Week [ ___ ] of 15** (Dates: ____/____/2026 to ____/____/2026) |

---

### 2. Summary of Work Done During the Current Week
> **Instructions:** Summarize key milestones achieved, modules developed, algorithms coded, and research conducted during this reporting period.

```
Summary of the Week:
----------------------------------------------------------------------------------------------------
[                                                                                                  ]
[                                                                                                  ]
[                                                                                                  ]
[                                                                                                  ]
[                                                                                                  ]
[                                                                                                  ]
[                                                                                                  ]
----------------------------------------------------------------------------------------------------
```
*Key Deliverables Completed This Week:*
- [ ] ___________________________________________________________________________________________
- [ ] ___________________________________________________________________________________________
- [ ] ___________________________________________________________________________________________

---

### 3. Planned Tasks for Next Week
> **Instructions:** Clearly state Task 1 and Task 2 with specific technical deliverables for the upcoming week.

#### **Task 1 for Next Week:**
- **Title / Module:** ___________________________________________________________________________
- **Objective & Technical Scope:**  
  _________________________________________________________________________________________________  
  _________________________________________________________________________________________________  
- **Expected Deliverables / Artifacts:** _________________________________________________________

#### **Task 2 for Next Week:**
- **Title / Module:** ___________________________________________________________________________
- **Objective & Technical Scope:**  
  _________________________________________________________________________________________________  
  _________________________________________________________________________________________________  
- **Expected Deliverables / Artifacts:** _________________________________________________________

---

### 4. Technical Challenges Encountered & Mitigations
| Challenge / Blocker Encountered | Mitigation Strategy / Resolution |
| :--- | :--- |
| 1. | |
| 2. | |

---

### 5. Cumulative Progress Assessment
- **Estimated Project Completion:** `[  ]` %
- **Work Status:** `[ ] On Schedule` &nbsp;&nbsp;&nbsp;&nbsp; `[ ] Behind Schedule` &nbsp;&nbsp;&nbsp;&nbsp; `[ ] Ahead of Schedule`
- **Git Commit Hash / Revision (if applicable):** `________________________`

---

### 6. Faculty Review & Verification Signatures

**Guide's Remarks & Feedback:**  
____________________________________________________________________________________________________  
____________________________________________________________________________________________________  

**Evaluation Criteria Checklist:**
- [ ] Weekly tasks completed satisfactorily
- [ ] Code committed to repository & documented
- [ ] Evidence/Screenshots/Logs verified
- [ ] Progress aligned with 15-Week Project Plan

```
+------------------------------------+------------------------------------+
|                                    |                                    |
|                                    |                                    |
| __________________________________ | __________________________________ |
| Signature of the Student(s)        | Signature of Internal Guide        |
| Date:                              | Date:                              |
+------------------------------------+------------------------------------+
|                                    |                                    |
|                                    |                                    |
| __________________________________ | __________________________________ |
| Project Coordinator / HoD          | External / Industry Evaluator      |
| Date:                              | Date:                              |
+------------------------------------+------------------------------------+
```

---

# PART 3: PRE-FILLED WEEKLY REPORTS FOR ACTIVE MILESTONES

*Below are pre-filled, submission-ready examples aligned with the core project modules that you can immediately adapt.*

---

## 📋 Ready-to-Submit Report: Milestone A (Machine Learning & Multi-Agent Pipeline)
*(Representative of **Week 8 / 9**)*

- **Reporting Week:** Week 9 of 15
- **Project Title:** AI-Powered Travel Planner Agent (A Stay-First Compound Multi-Agent System)

### • Summary of the Week:
> During this reporting week, we focused on training, hyperparameter tuning, and validating the core machine learning models powering the Multi-Agent framework:
> 1. Completed training of the **Budget & Expense Feasibility Agent (Agent 3)** using a Random Forest Regressor trained on 25,000 simulated Indian travel expense profiles across accommodation, transport, meals, and tickets. Optimized via Grid Search CV, reaching an **$R^2$ score of 90.92%** and low Root Mean Squared Error (RMSE).
> 2. Implemented the **Itinerary Scheduling Agent (Agent 2)** utilizing a Random Forest Classifier evaluated across 10,025 Archaeological Survey of India (ASI) attractions, attaining **84.6% classification accuracy** for attraction recommendation.
> 3. Embedded Traveling Salesperson (TSP) circular loop heuristics to prevent backtracking journeys and ensure all daily tours start and end at the verified Base Camp stay.
> 4. Exported serialized pickle models (`agent3_budget_rf.pkl`, `agent2_itinerary_rf.pkl`) and logged metrics into `ml_evaluation_charts/`.

### • Task 1 for Next Week:
- **Title:** IBM watsonx.ai (Granite) Foundation Model Integration & Grounded Prompt Pipeline
- **Technical Scope:** Configure the IBM watsonx.ai REST client with secure IAM token generation. Implement prompt-engineering templates that feed the deterministic numerical outputs of Agent 1–4 into **`ibm/granite-4-h-small`** to generate cultural etiquette, local dialect phrases, and packing tips without hallucination.
- **Expected Deliverables:** `backend/services/ibm_granite_service.py` module, JSON output validation tests, and zero-hallucination verification benchmarks.

### • Task 2 for Next Week:
- **Title:** Flask Modular Backend Blueprints & Dual Operational Engine Architecture
- **Technical Scope:** Refactor the backend architecture into Flask Blueprints (`auth_routes`, `planner_routes`, `api_routes`). Construct both operational modes: (1) **Autonomous AI Mode** for one-click multi-agent generation, and (2) **10-Step Interactive Smart Travel Wizard** allowing manual override and drag-and-drop schedule editing.
- **Expected Deliverables:** Complete Flask routing structure, SQLite session manager, and API endpoints for travel wizard progression.

---

## 📋 Ready-to-Submit Report: Milestone B (Full-Stack UI, Vector Maps & PDF Dossier)
*(Representative of **Week 12 / 13**)*

- **Reporting Week:** Week 13 of 15
- **Project Title:** AI-Powered Travel Planner Agent (A Stay-First Compound Multi-Agent System)

### • Summary of the Week:
> During this reporting week, we finalized the full-stack user interface and automated reporting system:
> 1. Integrated **MapLibre GL** vector mapping engine on the frontend, rendering high-resolution interactive map tiles, custom pin markers for Base Camp stays and ASI attractions, and OSRM-generated route polylines.
> 2. Implemented interactive financial telemetry using **Chart.js**, displaying dynamic category-wise expense donuts, day-wise spending burn-down charts, and budget compliance warnings.
> 3. Implemented the **ReportLab PDF Exporter engine**, enabling users to generate and download comprehensive, beautifully formatted offline travel dossiers containing complete daily schedules, emergency contacts, weather alerts, and expense breakdowns.
> 4. Enhanced responsive frontend layout with glassmorphic CSS styling, sticky footer controls, and mobile navigation support.

### • Task 1 for Next Week:
- **Title:** Faculty Evaluation Benchmark Verification & Multi-Dataset Stress Testing
- **Technical Scope:** Execute validation tests against all 8 official datasets in `FACULTY_EVALUATION_DATASETS/` (150,000 Stays, 10,025 ASI Spots, 8,989 Rail Stations, 25,000 Budget Trips). Measure and record end-to-end latency benchmarks across API calls, ML inference, and watsonx.ai response times.
- **Expected Deliverables:** Completed Benchmark Report (`FACULTY_EVALUATION_DATASETS/README.md`), latency comparison graphs, and verification test logs.

### • Task 2 for Next Week:
- **Title:** Cloud Deployment Setup & Final Academic Defense Slide Deck
- **Technical Scope:** Prepare the production Flask application for cloud infrastructure with secure environment configuration (`.env`). Prepare the comprehensive academic defense presentation deck (`TravelPlanner_Project_IBMUniversityEngagement.pptx`) covering architecture, ML metrics, demo flow, and business viability.
- **Expected Deliverables:** Cloud deployment configuration, completed 25+ slide defense PPT deck, and rehearsed project demonstration.
