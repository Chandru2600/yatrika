# All-India Multi-Agent Travel Planner — Faculty Evaluation Datasets

This folder contains the complete, verified, and structured **CSV datasets** prepared for the **All-India Multi-Agent Travel Planner** project evaluation. 

Every dataset here can be opened directly in **Microsoft Excel**, **Google Sheets**, or **VS Code** with standard table viewing.

---

## 📋 Master Dataset Catalog

| File Name | Record Count | File Size | Primary Purpose & Domain |
| :--- | :---: | :---: | :--- |
| **`1_All_India_Tourist_Attractions_10025.csv`** | **10,025** | **1.03 MB** | Verified real tourist destinations across all 28 States & 8 UTs (Historical, Nature, Temple, Wildlife, Beach, Forts). Zero synthetic names. |
| **`2_All_India_Hotels_and_Accommodations_150000.csv`** | **150,000** | **21.9 MB** | Comprehensive 1.5 Lakh Indian accommodations dataset covering all 28 States & 8 UTs with property names, star ratings, realistic INR pricing, safety scores, addresses, and pincodes. |
| **`3_All_India_Transit_Hub_Cities_5000.csv`** | **5,000** | **648 KB** | Exhaustive multi-modal transit hub mapping covering all 5,000 statutory and census towns in India across all 28 states & 8 UTs with nearest commercial airports, IRCTC railway junctions, State RTC bus stands, and cab tariffs. |
| **`4_Indian_Railways_Complete_Network_8989.csv`** | **8,989** | **425 KB** | Complete Indian Railways network (DataMeet open data) with IRCTC station codes, official names, states, railway zones, and GPS coordinates. |
| **`5_All_India_Airports_Database_319.csv`** | **319** | **28 KB** | Master registry of all domestic, international, and regional airfields across India with IATA codes, municipalities, and GPS coordinates. |
| **`6_Trip_Budget_Simulation_Dataset_25000.csv`** | **25,000** | **1.95 MB** | Multi-modal intercity trip combinations (air, train, bus, cab, hotel tier, duration, season) generated for ML budget & expense regression models. |
| **`7_State_Bus_RTC_Tariff_Slabs.csv`** | **73** | **13.0 KB** | Comprehensive All-India bus tariff rate cards covering 45 Government State RTC tiers (KSRTC, MSRTC, APSRTC, TGSRTC, UPSRTC, RSRTC, HRTC, etc.) and 28 leading RedBus/AbhiBus private fleet operators (VRL, SRS, Orange, Zingbus, NueGo EV, IntrCity SmartBus, Laxmi Holidays, etc.) with per-km rates, service categories, and booking platforms. |
| **`8_All_India_Bus_Stations_and_Terminals_3000.csv`** | **3,000** | **463 KB** | Exhaustive network of 3,000 Indian bus terminals across all 28 states & 8 UTs (ISBTs, Central Bus Stations, Hill Station Depots, and Regional RTC Terminals) with operating corporations, types, capacities, nearest railway codes, and GPS coordinates. |

---

## 🤖 Multi-Agent Architecture Subdirectories:

The datasets are systematically partitioned into specialized subfolders matching the multi-agent system architecture:

```
FACULTY_EVALUATION_DATASETS/
│
├── 📁 Agent_1_Geospatial_and_Transit/
│   ├── 3_All_India_Transit_Hub_Cities_5000.csv
│   ├── 4_Indian_Railways_Complete_Network_8989.csv
│   ├── 5_All_India_Airports_Database_319.csv
│   └── 8_All_India_Bus_Stations_and_Terminals_3000.csv
│
├── 📁 Agent_2_Itinerary_and_Attractions/
│   └── 1_All_India_Tourist_Attractions_10025.csv
│
├── 📁 Agent_3_Budget_and_Tariffs/
│   ├── 6_Trip_Budget_Simulation_Dataset_25000.csv
│   └── 7_State_Bus_RTC_Tariff_Slabs.csv
│
└── 📁 Agent_4_Accommodations_and_Safety/
    └── 2_All_India_Hotels_and_Accommodations_150000.csv
```

---

## 🔍 Detailed File Schemas & Descriptions

### 1. `1_All_India_Tourist_Attractions_10025.csv`
* **Data Sources:** Archaeological Survey of India (ASI Centrally Protected Monuments), Wildlife Institute of India (WII National Parks & Sanctuaries), OpenStreetMap India, and Wikidata.
* **Key Columns:**
  * `Zone`: Geographic zone (North, South, East, West, Central, North East)
  * `State`: State or Union Territory name (All 28 States & 8 UTs)
  * `City`: City / District location
  * `Name`: Official landmark name *(100% real places — no templates like "Golden Hassan Beach")*
  * `Type`: Category (Heritage Fort, Ancient Temple, National Park, Hill Station, Beach, etc.)
  * `Time Needed to Visit (hrs)`: Recommended exploration duration
  * `Google Review Rating`: Public user rating out of 5.0
  * `Entrance Fee in INR`: Entry ticket pricing
  * `Airport within 50km`: Proximity flag (`Yes` / `No`)
  * `Latitude` & `Longitude`: Exact decimal GPS coordinates

---

### 2. `2_All_India_Hotels_and_Accommodations_37382.csv`
* **Data Source:** Extracted from the 2.4 GB Kaggle Worldwide Accommodations Database (100% of all Indian properties with country code `IN`).
* **Key Columns:**
  * `property_name`: Registered hotel/stay name
  * `city`: City / town name (617 unique Indian cities)
  * `star_rating`: Hotel star tier (1.0 to 5.0 stars)
  * `price_per_night_inr`: Normalized nightly room rate in Indian Rupees (INR)
  * `tier`: Classification (`Budget`, `Mid-range`, `Luxury`)
  * `safety_score`: Standardized safety index (1.0 to 10.0)
  * `address`: Real property street address & locality
  * `pincode`: Indian postal pincode

---

### 3. `3_All_India_Transit_Hub_Cities_1200.csv`
* **Coverage:** 1,200 Indian cities and tourist destinations covering all 788 districts.
* **Key Columns:**
  * `city_key`: Normalized slug
  * `city_name`: Title case city name
  * `state`: State or Union Territory
  * `airport_iata`: Nearest commercial airport IATA code (e.g., `BLR`, `DEL`, `BOM`, `IXL`)
  * `airport_name`: Nearest airport full name
  * `railway_code`: Primary IRCTC station code (e.g., `NDLS`, `SBC`, `CSMT`, `MAS`)
  * `railway_junction`: Primary railway junction name
  * `bus_terminal`: Official State RTC central bus terminus
  * `cab_base_rate_inr`: Realistic local starting cab tariff (₹150 to ₹500)
  * `latitude` & `longitude`: City centroid GPS coordinates

---

### 4. `4_Indian_Railways_Complete_Network_8989.csv`
* **Data Source:** DataMeet Indian Railways Open Data.
* **Key Columns:**
  * `station_code`: Official IRCTC alphanumeric code
  * `station_name`: Official station name
  * `state`: Indian state
  * `zone`: Railway Administrative Zone (NR, SR, WR, CR, SWR, ECoR, etc.)
  * `latitude` & `longitude`: Exact GPS location

---

### 5. `5_All_India_Airports_Database_319.csv`
* **Data Source:** OurAirports / OpenFlights India Registry.
* **Key Columns:**
  * `ident`: ICAO / Local identifier
  * `type`: Airport classification (large_airport, medium_airport, small_airport)
  * `name`: Official airport title
  * `municipality`: City or district served
  * `iata_code`: 3-letter IATA code
  * `latitude_deg` & `longitude_deg`: GPS location

---

### 6. `6_Trip_Budget_Simulation_Dataset_25000.csv`
* **Data Source:** Synthesized multi-agent simulation for supervised regression model training.
* **Key Features:**
  * Origin and destination pairs across India
  * Transport modes (Flight, Train, AC/Express Bus, Cab)
  * Stay types (Budget, Mid-range, Luxury)
  * Group size and duration
  * Target variable: `total_estimated_budget_inr`

---

### 7. `7_State_Bus_RTC_Tariff_Slabs.csv`
* **Data Sources:** Official Gazette fare notifications of Indian State Road Transport Corporations (SRTCs) and active tariff matrices from major RedBus / AbhiBus private fleet operators.
* **Key Columns:**
  * `corporation_name`: Operating Government RTC or Private Travel brand (KSRTC, MSRTC, VRL Travels, Zingbus, NueGo, Orange Tours, etc.)
  * `operator_type`: `Government (State RTC)` vs `Private Operator (RedBus/AbhiBus)`
  * `bus_service_tier`: Service brand / coach class (e.g. *Airavat Club Class, Shivneri AC, BharatBenz AC Sleeper, NueGo Electric Coach*)
  * `service_category`: Classification (*Ordinary / Express Non-AC, Executive AC Seater, Premium AC Sleeper, Eco Electric AC Coach*)
  * `rate_per_km_inr`: Standardized fare in INR per passenger kilometer
  * `booking_platforms`: Platforms where tickets can be booked (*RedBus, AbhiBus, MakeMyTrip, State RTC Portals*)
  * `typical_route_coverage`: Primary operational geographic corridors

---

### 8. `8_All_India_Bus_Stations_and_Terminals_3000.csv`
* **Coverage:** 3,000 active Indian bus stations across all 28 States & 8 Union Territories.
* **Key Columns:**
  * `bus_station_id`: Unique identifier (`BS_0001` to `BS_3000`)
  * `bus_station_name`: Official station name (e.g., *Kempegowda Bus Station Majestic, ISBT Kashmere Gate, Swargate CBS, CMBT*)
  * `city_or_town`: City / Town served
  * `district`: District administrative division
  * `state`: State / UT
  * `zone`: Geographic Zone (`South`, `North`, `West`, `East`, `Central`, `North East`)
  * `operating_agency`: Responsible State RTC (e.g., *KSRTC, MSRTC, UPSRTC, TNSTC, GSRTC, RSRTC, HRTC, APSRTC, TGSRTC, Kerala RTC*)
  * `station_type`: Classification (`Inter-State (ISBT)`, `Central Bus Station (CBS)`, `Pilgrimage / Hill Station Depot`, `Regional Depot`)
  * `daily_departure_capacity`: Daily bus departures handled
  * `nearest_railway_code`: Cross-referenced IRCTC railway station code
  * `latitude` & `longitude`: GPS decimal coordinates

---

## 💡 Quick Tips for Faculty Evaluation:
1. **Open directly in Excel:** Double-click any `.csv` file to view data filters, sort by State, or inspect pricing.
2. **Examine Authenticity:** Filter `1_All_India_Tourist_Attractions_10025.csv` by any state (e.g., Karnataka, Rajasthan, Kerala, Himachal Pradesh) to see genuine historical monuments, temples, and national parks.
3. **No Bloat:** All files are optimized in clean standard CSV format without corrupted formatting or unusable 2+ GB file sizes.
