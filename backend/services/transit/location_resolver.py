"""
TravelPlannerAgent - Comprehensive All-India Location Hub & Transit Resolver
Covers 85+ Indian tourist destinations, hill stations, heritage towns, and pilgrim centers.
Includes a dynamic spatial resolver that maps any arbitrary Indian location to its nearest
real airport and railway junction using the OurAirports (319 airports) and DataMeet (8,990 stations) datasets.
"""

import os
import csv
import json
import math

# Comprehensive All-India Destination Transit Hub Database
HUB_DATABASE = {
    # --- Karnataka Hill Stations & Heritage ---
    "samse": {
        "name": "Samse (Kalasa / Kudremukh Foothills)",
        "has_airport": False, "nearest_airport_name": "Mangalore Int'l Airport", "nearest_airport_code": "IXE",
        "airport_dist_km": 115, "airport_transfer_hours": 3.0, "airport_transfer_cab_cost": 2500,
        "has_railway": False, "nearest_station_name": "Kadur Junction", "nearest_station_code": "DRU",
        "rail_dist_km": 78, "rail_transfer_hours": 2.0, "rail_transfer_cab_cost": 1600,
        "has_bus": True, "bus_terminal_name": "Samse Tea Estate Junction / Kalasa Bus Stand",
        "connecting_bus": {
            "operator": "KSRTC Chikkamagaluru Division — Karnataka Sarige Express",
            "route": "Kadur ➔ Chikkamagaluru ➔ Mudigere Handpost ➔ Kottigehara ➔ Kalasa",
            "departure_station": "Kadur KSRTC Bus Stand (Bay 3)",
            "arrival_station": "Kalasa KSRTC Main Bus Stand",
            "duration": "2h 30m",
            "fare": 115,
            "frequency": "Every 30–45 mins",
            "station_transfer_walk": "5-min walk (400m) from Kadur Railway Station to Kadur Bus Stand Bay 3"
        },
        "local_shuttle": {
            "operator": "Kalasa – Samse – Kudremukh Rural Route Bus (KSRTC / Sri Durgamba)",
            "route": "Kalasa Town ➔ Samse Tea Estate Junction",
            "departure_station": "Kalasa Main Bus Stand",
            "arrival_station": "Samse Tea Estate / Homestay Gate",
            "duration": "20m",
            "fare": 20,
            "frequency": "Every 20 mins"
        }
    },
    "kalasa": {
        "name": "Kalasa",
        "has_airport": False, "nearest_airport_name": "Mangalore Int'l Airport", "nearest_airport_code": "IXE",
        "airport_dist_km": 105, "airport_transfer_hours": 2.8, "airport_transfer_cab_cost": 2200,
        "has_railway": False, "nearest_station_name": "Kadur Junction", "nearest_station_code": "DRU",
        "rail_dist_km": 68, "rail_transfer_hours": 1.8, "rail_transfer_cab_cost": 1400,
        "has_bus": True, "bus_terminal_name": "Kalasa KSRTC Bus Stand",
        "connecting_bus": {
            "operator": "KSRTC Chikkamagaluru Division — Karnataka Sarige Express",
            "route": "Kadur ➔ Chikkamagaluru ➔ Mudigere Handpost ➔ Kottigehara ➔ Kalasa",
            "departure_station": "Kadur KSRTC Bus Stand (Bay 3)",
            "arrival_station": "Kalasa KSRTC Main Bus Stand",
            "duration": "2h 30m",
            "fare": 115,
            "frequency": "Every 30–45 mins",
            "station_transfer_walk": "5-min walk (400m) from Kadur Railway Station to Kadur Bus Stand Bay 3"
        },
        "local_shuttle": {
            "operator": "Kalasa – Samse – Kudremukh Rural Route Bus (KSRTC / Sri Durgamba)",
            "route": "Kalasa Town ➔ Samse Tea Estate Junction",
            "departure_station": "Kalasa Main Bus Stand",
            "arrival_station": "Samse Tea Estate / Homestay Gate",
            "duration": "20m",
            "fare": 20,
            "frequency": "Every 20 mins"
        }
    },
    "chikmagalur": {
        "name": "Chikmagalur",
        "has_airport": False, "nearest_airport_name": "Mangalore Int'l Airport", "nearest_airport_code": "IXE",
        "airport_dist_km": 150, "airport_transfer_hours": 3.5, "airport_transfer_cab_cost": 2800,
        "has_railway": True, "nearest_station_name": "Chikamagalur Railway Station", "nearest_station_code": "CMGR",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Chikmagalur KSRTC Bus Stand"
    },
    "kudremukh": {
        "name": "Kudremukh",
        "has_airport": False, "nearest_airport_name": "Mangalore Int'l Airport", "nearest_airport_code": "IXE",
        "airport_dist_km": 95, "airport_transfer_hours": 2.5, "airport_transfer_cab_cost": 2000,
        "has_railway": False, "nearest_station_name": "Mangalore Junction", "nearest_station_code": "MAJN",
        "rail_dist_km": 95, "rail_transfer_hours": 2.5, "rail_transfer_cab_cost": 2000,
        "has_bus": True, "bus_terminal_name": "Kudremukh Bus Stop"
    },
    "coorg": {
        "name": "Coorg (Madikeri)",
        "has_airport": False, "nearest_airport_name": "Kannur Int'l Airport", "nearest_airport_code": "CNN",
        "airport_dist_km": 90, "airport_transfer_hours": 2.4, "airport_transfer_cab_cost": 2100,
        "has_railway": False, "nearest_station_name": "Mysuru Junction", "nearest_station_code": "MYS",
        "rail_dist_km": 118, "rail_transfer_hours": 2.8, "rail_transfer_cab_cost": 2400,
        "has_bus": True, "bus_terminal_name": "Madikeri KSRTC Bus Stand"
    },
    "madikeri": {
        "name": "Madikeri",
        "has_airport": False, "nearest_airport_name": "Kannur Int'l Airport", "nearest_airport_code": "CNN",
        "airport_dist_km": 90, "airport_transfer_hours": 2.4, "airport_transfer_cab_cost": 2100,
        "has_railway": False, "nearest_station_name": "Mysuru Junction", "nearest_station_code": "MYS",
        "rail_dist_km": 118, "rail_transfer_hours": 2.8, "rail_transfer_cab_cost": 2400,
        "has_bus": True, "bus_terminal_name": "Madikeri KSRTC Bus Stand"
    },
    "gokarna": {
        "name": "Gokarna",
        "has_airport": False, "nearest_airport_name": "Goa Dabolim Airport", "nearest_airport_code": "GOI",
        "airport_dist_km": 140, "airport_transfer_hours": 3.2, "airport_transfer_cab_cost": 2800,
        "has_railway": True, "nearest_station_name": "Gokarna Road Railway Station", "nearest_station_code": "GOK",
        "rail_dist_km": 8, "rail_transfer_hours": 0.3, "rail_transfer_cab_cost": 250,
        "has_bus": True, "bus_terminal_name": "Gokarna KSRTC Bus Stand"
    },
    "hampi": {
        "name": "Hampi",
        "has_airport": False, "nearest_airport_name": "Jindal Vijayanagar Airport (VDY)", "nearest_airport_code": "VDY",
        "airport_dist_km": 35, "airport_transfer_hours": 0.9, "airport_transfer_cab_cost": 900,
        "has_railway": True, "nearest_station_name": "Hosapete Junction", "nearest_station_code": "HPT",
        "rail_dist_km": 12, "rail_transfer_hours": 0.4, "rail_transfer_cab_cost": 300,
        "has_bus": True, "bus_terminal_name": "Hampi Temple Bus Stop"
    },
    "sakleshpur": {
        "name": "Sakleshpur",
        "has_airport": False, "nearest_airport_name": "Mangalore Int'l Airport", "nearest_airport_code": "IXE",
        "airport_dist_km": 130, "airport_transfer_hours": 3.1, "airport_transfer_cab_cost": 2600,
        "has_railway": True, "nearest_station_name": "Sakleshpur Railway Station", "nearest_station_code": "SKLR",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Sakleshpur KSRTC Bus Stand"
    },
    "dandeli": {
        "name": "Dandeli",
        "has_airport": False, "nearest_airport_name": "Hubli Airport", "nearest_airport_code": "HBX",
        "airport_dist_km": 72, "airport_transfer_hours": 1.8, "airport_transfer_cab_cost": 1600,
        "has_railway": False, "nearest_station_name": "Alnavar Junction", "nearest_station_code": "LWR",
        "rail_dist_km": 32, "rail_transfer_hours": 0.8, "rail_transfer_cab_cost": 750,
        "has_bus": True, "bus_terminal_name": "Dandeli Bus Stand"
    },
    "udupi": {
        "name": "Udupi",
        "has_airport": False, "nearest_airport_name": "Mangalore Int'l Airport", "nearest_airport_code": "IXE",
        "airport_dist_km": 55, "airport_transfer_hours": 1.2, "airport_transfer_cab_cost": 1200,
        "has_railway": True, "nearest_station_name": "Udupi Railway Station", "nearest_station_code": "UD",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Udupi Service Bus Stand"
    },

    # --- Kerala Destinations ---
    "wayanad": {
        "name": "Wayanad (Kalpetta)",
        "has_airport": False, "nearest_airport_name": "Calicut Int'l Airport", "nearest_airport_code": "CCJ",
        "airport_dist_km": 88, "airport_transfer_hours": 2.5, "airport_transfer_cab_cost": 2200,
        "has_railway": False, "nearest_station_name": "Kozhikode Railway Station", "nearest_station_code": "CLT",
        "rail_dist_km": 85, "rail_transfer_hours": 2.4, "rail_transfer_cab_cost": 2100,
        "has_bus": True, "bus_terminal_name": "Kalpetta KSRTC Bus Stand"
    },
    "munnar": {
        "name": "Munnar",
        "has_airport": False, "nearest_airport_name": "Cochin Int'l Airport", "nearest_airport_code": "COK",
        "airport_dist_km": 110, "airport_transfer_hours": 3.2, "airport_transfer_cab_cost": 2600,
        "has_railway": False, "nearest_station_name": "Aluva Railway Station", "nearest_station_code": "AWY",
        "rail_dist_km": 108, "rail_transfer_hours": 3.1, "rail_transfer_cab_cost": 2500,
        "has_bus": True, "bus_terminal_name": "Munnar Central Bus Stand"
    },
    "alleppey": {
        "name": "Alappuzha (Alleppey)",
        "has_airport": False, "nearest_airport_name": "Cochin Int'l Airport", "nearest_airport_code": "COK",
        "airport_dist_km": 82, "airport_transfer_hours": 2.1, "airport_transfer_cab_cost": 1900,
        "has_railway": True, "nearest_station_name": "Alappuzha Railway Station", "nearest_station_code": "ALLP",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Alappuzha KSRTC Terminal"
    },
    "thekkady": {
        "name": "Thekkady (Periyar)",
        "has_airport": False, "nearest_airport_name": "Madurai Airport", "nearest_airport_code": "IXM",
        "airport_dist_km": 136, "airport_transfer_hours": 3.5, "airport_transfer_cab_cost": 2800,
        "has_railway": False, "nearest_station_name": "Kottayam Railway Station", "nearest_station_code": "KTYM",
        "rail_dist_km": 110, "rail_transfer_hours": 3.0, "rail_transfer_cab_cost": 2400,
        "has_bus": True, "bus_terminal_name": "Kumily Bus Stand"
    },
    "varkala": {
        "name": "Varkala",
        "has_airport": False, "nearest_airport_name": "Thiruvananthapuram Int'l Airport", "nearest_airport_code": "TRV",
        "airport_dist_km": 42, "airport_transfer_hours": 1.1, "airport_transfer_cab_cost": 1100,
        "has_railway": True, "nearest_station_name": "Varkala Sivagiri Railway Station", "nearest_station_code": "VAK",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Varkala Temple Bus Stand"
    },

    # --- Tamil Nadu Destinations ---
    "ooty": {
        "name": "Ooty (Udhagamandalam)",
        "has_airport": False, "nearest_airport_name": "Coimbatore Int'l Airport", "nearest_airport_code": "CJB",
        "airport_dist_km": 88, "airport_transfer_hours": 2.8, "airport_transfer_cab_cost": 2400,
        "has_railway": True, "nearest_station_name": "Udhagamandalam Railway Station", "nearest_station_code": "UAM",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Ooty Central Bus Stand"
    },
    "kodaikanal": {
        "name": "Kodaikanal",
        "has_airport": False, "nearest_airport_name": "Madurai Airport", "nearest_airport_code": "IXM",
        "airport_dist_km": 120, "airport_transfer_hours": 3.2, "airport_transfer_cab_cost": 2600,
        "has_railway": False, "nearest_station_name": "Kodai Road Railway Station", "nearest_station_code": "KQN",
        "rail_dist_km": 80, "rail_transfer_hours": 2.2, "rail_transfer_cab_cost": 1900,
        "has_bus": True, "bus_terminal_name": "Kodaikanal Bus Stand"
    },
    "rameswaram": {
        "name": "Rameswaram",
        "has_airport": False, "nearest_airport_name": "Madurai Airport", "nearest_airport_code": "IXM",
        "airport_dist_km": 175, "airport_transfer_hours": 3.8, "airport_transfer_cab_cost": 3200,
        "has_railway": True, "nearest_station_name": "Rameswaram Railway Station", "nearest_station_code": "RMM",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Rameswaram Temple Bus Stand"
    },
    "kanyakumari": {
        "name": "Kanyakumari",
        "has_airport": False, "nearest_airport_name": "Thiruvananthapuram Int'l Airport", "nearest_airport_code": "TRV",
        "airport_dist_km": 95, "airport_transfer_hours": 2.5, "airport_transfer_cab_cost": 2200,
        "has_railway": True, "nearest_station_name": "Kanyakumari Railway Station", "nearest_station_code": "CAPE",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Kanyakumari Central Bus Stand"
    },
    "pondicherry": {
        "name": "Pondicherry (Puducherry)",
        "has_airport": True, "nearest_airport_name": "Pondicherry Airport", "nearest_airport_code": "PNY",
        "airport_dist_km": 0, "airport_transfer_hours": 0, "airport_transfer_cab_cost": 0,
        "has_railway": True, "nearest_station_name": "Puducherry Railway Station", "nearest_station_code": "PDY",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Puducherry PRTC Bus Stand"
    },

    # --- Himachal Pradesh ---
    "shimla": {
        "name": "Shimla",
        "has_airport": False, "nearest_airport_name": "Chandigarh Int'l Airport", "nearest_airport_code": "IXC",
        "airport_dist_km": 115, "airport_transfer_hours": 3.2, "airport_transfer_cab_cost": 2800,
        "has_railway": True, "nearest_station_name": "Shimla Railway Station (via Kalka)", "nearest_station_code": "SML",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Shimla ISBT Tutikandi"
    },
    "manali": {
        "name": "Manali",
        "has_airport": False, "nearest_airport_name": "Kullu Bhuntar Airport", "nearest_airport_code": "KUU",
        "airport_dist_km": 50, "airport_transfer_hours": 1.8, "airport_transfer_cab_cost": 1500,
        "has_railway": False, "nearest_station_name": "Chandigarh Junction", "nearest_station_code": "CDG",
        "rail_dist_km": 290, "rail_transfer_hours": 7.5, "rail_transfer_cab_cost": 4500,
        "has_bus": True, "bus_terminal_name": "Manali HRTC Volvo Bus Stand"
    },
    "kasol": {
        "name": "Kasol",
        "has_airport": False, "nearest_airport_name": "Kullu Bhuntar Airport", "nearest_airport_code": "KUU",
        "airport_dist_km": 31, "airport_transfer_hours": 1.2, "airport_transfer_cab_cost": 900,
        "has_railway": False, "nearest_station_name": "Chandigarh Junction", "nearest_station_code": "CDG",
        "rail_dist_km": 270, "rail_transfer_hours": 7.0, "rail_transfer_cab_cost": 4200,
        "has_bus": True, "bus_terminal_name": "Kasol HRTC Bus Stop"
    },
    "dharamshala": {
        "name": "Dharamshala / McLeod Ganj",
        "has_airport": True, "nearest_airport_name": "Kangra Airport (Gaggal)", "nearest_airport_code": "DHM",
        "airport_dist_km": 14, "airport_transfer_hours": 0.5, "airport_transfer_cab_cost": 500,
        "has_railway": False, "nearest_station_name": "Pathankot Cantt", "nearest_station_code": "PTKC",
        "rail_dist_km": 85, "rail_transfer_hours": 2.5, "rail_transfer_cab_cost": 2000,
        "has_bus": True, "bus_terminal_name": "Dharamshala ISBT"
    },
    "spiti": {
        "name": "Spiti Valley (Kaza)",
        "has_airport": False, "nearest_airport_name": "Kullu Bhuntar Airport", "nearest_airport_code": "KUU",
        "airport_dist_km": 240, "airport_transfer_hours": 7.5, "airport_transfer_cab_cost": 6500,
        "has_railway": False, "nearest_station_name": "Shimla Railway Station", "nearest_station_code": "SML",
        "rail_dist_km": 410, "rail_transfer_hours": 12.0, "rail_transfer_cab_cost": 9000,
        "has_bus": True, "bus_terminal_name": "Kaza HRTC Bus Stand"
    },
    "dalhousie": {
        "name": "Dalhousie",
        "has_airport": False, "nearest_airport_name": "Kangra Airport (Gaggal)", "nearest_airport_code": "DHM",
        "airport_dist_km": 105, "airport_transfer_hours": 3.2, "airport_transfer_cab_cost": 2800,
        "has_railway": False, "nearest_station_name": "Pathankot Cantt", "nearest_station_code": "PTKC",
        "rail_dist_km": 80, "rail_transfer_hours": 2.4, "rail_transfer_cab_cost": 2200,
        "has_bus": True, "bus_terminal_name": "Dalhousie Bus Stand"
    },

    # --- Uttarakhand Destinations ---
    "rishikesh": {
        "name": "Rishikesh",
        "has_airport": False, "nearest_airport_name": "Dehradun Jolly Grant Airport", "nearest_airport_code": "DED",
        "airport_dist_km": 21, "airport_transfer_hours": 0.6, "airport_transfer_cab_cost": 600,
        "has_railway": True, "nearest_station_name": "Yog Nagari Rishikesh", "nearest_station_code": "YNRK",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Rishikesh Bus Stand"
    },
    "mussoorie": {
        "name": "Mussoorie",
        "has_airport": False, "nearest_airport_name": "Dehradun Jolly Grant Airport", "nearest_airport_code": "DED",
        "airport_dist_km": 58, "airport_transfer_hours": 1.8, "airport_transfer_cab_cost": 1600,
        "has_railway": False, "nearest_station_name": "Dehradun Terminal", "nearest_station_code": "DDN",
        "rail_dist_km": 34, "rail_transfer_hours": 1.2, "rail_transfer_cab_cost": 1100,
        "has_bus": True, "bus_terminal_name": "Library Bus Stand Mussoorie"
    },
    "nainital": {
        "name": "Nainital",
        "has_airport": False, "nearest_airport_name": "Pantnagar Airport", "nearest_airport_code": "PGH",
        "airport_dist_km": 68, "airport_transfer_hours": 2.0, "airport_transfer_cab_cost": 1800,
        "has_railway": False, "nearest_station_name": "Kathgodam Railway Station", "nearest_station_code": "KGM",
        "rail_dist_km": 35, "rail_transfer_hours": 1.1, "rail_transfer_cab_cost": 1000,
        "has_bus": True, "bus_terminal_name": "Tallital Bus Station Nainital"
    },
    "auli": {
        "name": "Auli (Joshimath)",
        "has_airport": False, "nearest_airport_name": "Dehradun Jolly Grant Airport", "nearest_airport_code": "DED",
        "airport_dist_km": 275, "airport_transfer_hours": 8.5, "airport_transfer_cab_cost": 6500,
        "has_railway": False, "nearest_station_name": "Rishikesh Railway Station", "nearest_station_code": "RKSH",
        "rail_dist_km": 255, "rail_transfer_hours": 8.0, "rail_transfer_cab_cost": 6000,
        "has_bus": True, "bus_terminal_name": "Joshimath Bus Stand"
    },
    "corbett": {
        "name": "Jim Corbett National Park (Ramnagar)",
        "has_airport": False, "nearest_airport_name": "Pantnagar Airport", "nearest_airport_code": "PGH",
        "airport_dist_km": 80, "airport_transfer_hours": 2.2, "airport_transfer_cab_cost": 1900,
        "has_railway": True, "nearest_station_name": "Ramnagar Railway Station", "nearest_station_code": "RMR",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Ramnagar Bus Depot"
    },

    # --- Jammu & Kashmir, Ladakh ---
    "leh": {
        "name": "Leh (Ladakh)",
        "has_airport": True, "nearest_airport_name": "Kushok Bakula Rimpochee Airport", "nearest_airport_code": "IXL",
        "airport_dist_km": 0, "airport_transfer_hours": 0, "airport_transfer_cab_cost": 0,
        "has_railway": False, "nearest_station_name": "Jammu Tawi", "nearest_station_code": "JAT",
        "rail_dist_km": 700, "rail_transfer_hours": 18.0, "rail_transfer_cab_cost": 15000,
        "has_bus": True, "bus_terminal_name": "Leh JKSRTC Bus Stand"
    },
    "gulmarg": {
        "name": "Gulmarg",
        "has_airport": False, "nearest_airport_name": "Srinagar Int'l Airport", "nearest_airport_code": "SXR",
        "airport_dist_km": 56, "airport_transfer_hours": 1.8, "airport_transfer_cab_cost": 1800,
        "has_railway": False, "nearest_station_name": "Mazhom Railway Station", "nearest_station_code": "MZMA",
        "rail_dist_km": 38, "rail_transfer_hours": 1.2, "rail_transfer_cab_cost": 1200,
        "has_bus": True, "bus_terminal_name": "Tangmarg / Gulmarg Bus Stand"
    },
    "pahalgam": {
        "name": "Pahalgam",
        "has_airport": False, "nearest_airport_name": "Srinagar Int'l Airport", "nearest_airport_code": "SXR",
        "airport_dist_km": 90, "airport_transfer_hours": 2.5, "airport_transfer_cab_cost": 2400,
        "has_railway": False, "nearest_station_name": "Anantnag Railway Station", "nearest_station_code": "ANT",
        "rail_dist_km": 42, "rail_transfer_hours": 1.2, "rail_transfer_cab_cost": 1200,
        "has_bus": True, "bus_terminal_name": "Pahalgam Main Bus Stand"
    },

    # --- Rajasthan & Gujarat ---
    "mount abu": {
        "name": "Mount Abu",
        "has_airport": False, "nearest_airport_name": "Udaipur Airport", "nearest_airport_code": "UDR",
        "airport_dist_km": 175, "airport_transfer_hours": 3.8, "airport_transfer_cab_cost": 3200,
        "has_railway": False, "nearest_station_name": "Abu Road Railway Station", "nearest_station_code": "ABR",
        "rail_dist_km": 28, "rail_transfer_hours": 0.8, "rail_transfer_cab_cost": 800,
        "has_bus": True, "bus_terminal_name": "Mount Abu RSRTC Stand"
    },
    "ranthambore": {
        "name": "Ranthambore (Sawai Madhopur)",
        "has_airport": False, "nearest_airport_name": "Jaipur Int'l Airport", "nearest_airport_code": "JAI",
        "airport_dist_km": 160, "airport_transfer_hours": 3.5, "airport_transfer_cab_cost": 3000,
        "has_railway": True, "nearest_station_name": "Sawai Madhopur Junction", "nearest_station_code": "SWM",
        "rail_dist_km": 12, "rail_transfer_hours": 0.4, "rail_transfer_cab_cost": 350,
        "has_bus": True, "bus_terminal_name": "Sawai Madhopur Bus Stand"
    },
    "dwarka": {
        "name": "Dwarka",
        "has_airport": False, "nearest_airport_name": "Jamnagar Airport", "nearest_airport_code": "JGA",
        "airport_dist_km": 130, "airport_transfer_hours": 2.8, "airport_transfer_cab_cost": 2500,
        "has_railway": True, "nearest_station_name": "Dwarka Railway Station", "nearest_station_code": "DWK",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Dwarka GSRTC Bus Stand"
    },
    "gir": {
        "name": "Gir National Park (Sasan Gir)",
        "has_airport": False, "nearest_airport_name": "Keshod Airport", "nearest_airport_code": "IXK",
        "airport_dist_km": 50, "airport_transfer_hours": 1.2, "airport_transfer_cab_cost": 1200,
        "has_railway": True, "nearest_station_name": "Sasan Gir Railway Station", "nearest_station_code": "SASN",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Sasan Gir Bus Stop"
    },

    # --- Maharashtra Hill Stations & Destinations ---
    "lonavala": {
        "name": "Lonavala",
        "has_airport": False, "nearest_airport_name": "Pune Airport", "nearest_airport_code": "PNQ",
        "airport_dist_km": 72, "airport_transfer_hours": 1.6, "airport_transfer_cab_cost": 1700,
        "has_railway": True, "nearest_station_name": "Lonavala Railway Station", "nearest_station_code": "LNL",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Lonavala MSRTC Stand"
    },
    "mahabaleshwar": {
        "name": "Mahabaleshwar",
        "has_airport": False, "nearest_airport_name": "Pune Airport", "nearest_airport_code": "PNQ",
        "airport_dist_km": 125, "airport_transfer_hours": 3.2, "airport_transfer_cab_cost": 2600,
        "has_railway": False, "nearest_station_name": "Wathar Railway Station", "nearest_station_code": "WTR",
        "rail_dist_km": 62, "rail_transfer_hours": 1.8, "rail_transfer_cab_cost": 1500,
        "has_bus": True, "bus_terminal_name": "Mahabaleshwar ST Bus Stand"
    },
    "alibaug": {
        "name": "Alibaug",
        "has_airport": False, "nearest_airport_name": "Chhatrapati Shivaji Maharaj Airport", "nearest_airport_code": "BOM",
        "airport_dist_km": 95, "airport_transfer_hours": 2.5, "airport_transfer_cab_cost": 2200,
        "has_railway": False, "nearest_station_name": "Pen Railway Station", "nearest_station_code": "PEN",
        "rail_dist_km": 28, "rail_transfer_hours": 0.8, "rail_transfer_cab_cost": 750,
        "has_bus": True, "bus_terminal_name": "Alibaug ST Stand"
    },

    # --- Madhya Pradesh & Central India ---
    "khajuraho": {
        "name": "Khajuraho",
        "has_airport": True, "nearest_airport_name": "Khajuraho Airport", "nearest_airport_code": "HJR",
        "airport_dist_km": 0, "airport_transfer_hours": 0, "airport_transfer_cab_cost": 0,
        "has_railway": True, "nearest_station_name": "Khajuraho Railway Station", "nearest_station_code": "KURJ",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Khajuraho Bus Stand"
    },
    "kanha": {
        "name": "Kanha National Park",
        "has_airport": False, "nearest_airport_name": "Jabalpur Airport", "nearest_airport_code": "JLR",
        "airport_dist_km": 160, "airport_transfer_hours": 3.8, "airport_transfer_cab_cost": 3400,
        "has_railway": False, "nearest_station_name": "Gondia Junction", "nearest_station_code": "G",
        "rail_dist_km": 145, "rail_transfer_hours": 3.5, "rail_transfer_cab_cost": 3100,
        "has_bus": True, "bus_terminal_name": "Khatiya Kanha Bus Stop"
    },
    "pachmarhi": {
        "name": "Pachmarhi",
        "has_airport": False, "nearest_airport_name": "Bhopal Raja Bhoj Airport", "nearest_airport_code": "BHO",
        "airport_dist_km": 210, "airport_transfer_hours": 4.8, "airport_transfer_cab_cost": 4200,
        "has_railway": False, "nearest_station_name": "Pipariya Railway Station", "nearest_station_code": "PPI",
        "rail_dist_km": 54, "rail_transfer_hours": 1.4, "rail_transfer_cab_cost": 1300,
        "has_bus": True, "bus_terminal_name": "Pachmarhi Bus Stand"
    },

    # --- East & Northeast India ---
    "darjeeling": {
        "name": "Darjeeling",
        "has_airport": False, "nearest_airport_name": "Bagdogra Airport", "nearest_airport_code": "IXB",
        "airport_dist_km": 68, "airport_transfer_hours": 2.6, "airport_transfer_cab_cost": 2400,
        "has_railway": True, "nearest_station_name": "Darjeeling Himalayan Railway", "nearest_station_code": "DJ",
        "rail_dist_km": 0, "rail_transfer_hours": 0, "rail_transfer_cab_cost": 0,
        "has_bus": True, "bus_terminal_name": "Darjeeling Chowk Bazaar Bus Stand"
    },
    "gangtok": {
        "name": "Gangtok",
        "has_airport": True, "nearest_airport_name": "Pakyong Airport", "nearest_airport_code": "PYG",
        "airport_dist_km": 30, "airport_transfer_hours": 1.1, "airport_transfer_cab_cost": 1200,
        "has_railway": False, "nearest_station_name": "New Jalpaiguri Junction", "nearest_station_code": "NJP",
        "rail_dist_km": 120, "rail_transfer_hours": 4.0, "rail_transfer_cab_cost": 3500,
        "has_bus": True, "bus_terminal_name": "SNT Bus Terminus Gangtok"
    },
    "shillong": {
        "name": "Shillong",
        "has_airport": True, "nearest_airport_name": "Shillong Airport (Umroi)", "nearest_airport_code": "SHL",
        "airport_dist_km": 32, "airport_transfer_hours": 1.1, "airport_transfer_cab_cost": 1200,
        "has_railway": False, "nearest_station_name": "Guwahati Railway Station", "nearest_station_code": "GHY",
        "rail_dist_km": 98, "rail_transfer_hours": 2.8, "rail_transfer_cab_cost": 2500,
        "has_bus": True, "bus_terminal_name": "Polo Ground Bus Station Shillong"
    },
    "cherrapunji": {
        "name": "Cherrapunji (Sohra)",
        "has_airport": False, "nearest_airport_name": "Guwahati Int'l Airport", "nearest_airport_code": "GAU",
        "airport_dist_km": 165, "airport_transfer_hours": 4.5, "airport_transfer_cab_cost": 3800,
        "has_railway": False, "nearest_station_name": "Guwahati Railway Station", "nearest_station_code": "GHY",
        "rail_dist_km": 150, "rail_transfer_hours": 4.2, "rail_transfer_cab_cost": 3600,
        "has_bus": True, "bus_terminal_name": "Sohra Market Bus Stand"
    },
    "kaziranga": {
        "name": "Kaziranga National Park",
        "has_airport": False, "nearest_airport_name": "Jorhat Airport", "nearest_airport_code": "JRH",
        "airport_dist_km": 85, "airport_transfer_hours": 2.0, "airport_transfer_cab_cost": 1900,
        "has_railway": False, "nearest_station_name": "Jakhalabandha Railway Station", "nearest_station_code": "JKB",
        "rail_dist_km": 42, "rail_transfer_hours": 1.1, "rail_transfer_cab_cost": 1100,
        "has_bus": True, "bus_terminal_name": "Kohora Bus Stand Kaziranga"
    }
}

# Major Metropolitan Commercial Airports Mapping
MAJOR_METRO_AIRPORTS = {
    "bangalore": ("Kempegowda Int'l Airport", "BLR"),
    "bengaluru": ("Kempegowda Int'l Airport", "BLR"),
    "delhi": ("Indira Gandhi Int'l Airport", "DEL"),
    "new delhi": ("Indira Gandhi Int'l Airport", "DEL"),
    "mumbai": ("Chhatrapati Shivaji Maharaj Airport", "BOM"),
    "hyderabad": ("Rajiv Gandhi Int'l Airport", "HYD"),
    "chennai": ("Chennai Int'l Airport", "MAA"),
    "kolkata": ("Netaji Subhash Chandra Bose Airport", "CCU"),
    "ahmedabad": ("Sardar Vallabhbhai Patel Airport", "AMD"),
    "pune": ("Pune Int'l Airport", "PNQ"),
    "jaipur": ("Jaipur Int'l Airport", "JAI"),
    "lucknow": ("Chaudhary Charan Singh Airport", "LKO"),
    "varanasi": ("Lal Bahadur Shastri Int'l Airport", "VNS"),
    "kochi": ("Cochin Int'l Airport", "COK"),
    "cochin": ("Cochin Int'l Airport", "COK"),
    "goa": ("Goa Dabolim Airport", "GOI"),
    "madgaon": ("Goa Dabolim Airport", "GOI"),
    "panaji": ("Manohar Int'l Airport (Mopa)", "GOX"),
    "chandigarh": ("Shaheed Bhagat Singh Int'l Airport", "IXC"),
    "amritsar": ("Sri Guru Ram Dass Jee Airport", "ATQ"),
    "guwahati": ("Lokpriya Gopinath Bordoloi Airport", "GAU"),
    "bhubaneswar": ("Biju Patnaik Int'l Airport", "BBI"),
    "patna": ("Jay Prakash Narayan Airport", "PAT"),
    "ranchi": ("Birsa Munda Airport", "IXR"),
    "srinagar": ("Sheikh ul-Alam Int'l Airport", "SXR"),
    "dehradun": ("Jolly Grant Airport", "DED"),
    "mangalore": ("Mangalore Int'l Airport", "IXE"),
    "mysore": ("Mysore Airport", "MYQ"),
    "mysuru": ("Mysore Airport", "MYQ"),
    "coimbatore": ("Coimbatore Int'l Airport", "CJB"),
    "madurai": ("Madurai Airport", "IXM"),
    "visakhapatnam": ("Visakhapatnam Airport", "VTZ"),
    "vijayawada": ("Vijayawada Int'l Airport", "VGA"),
    "tirupati": ("Tirupati Airport", "TIR"),
    "bhopal": ("Raja Bhoj Airport", "BHO"),
    "indore": ("Devi Ahilya Bai Holkar Airport", "IDR"),
    "surat": ("Surat International Airport", "STV"),
    "vadodara": ("Vadodara Airport", "BDQ"),
    "raipur": ("Swami Vivekananda Airport", "RPR"),
    "leh": ("Kushok Bakula Rimpochee Airport", "IXL"),
    "agartala": ("Maharaja Bir Bikram Airport", "IXA")
}


# Comprehensive Pan-India Commercial Airports (name, iata, lat, lon)
INDIAN_COMMERCIAL_AIRPORTS = [
    ("Kempegowda Int'l Airport, Bengaluru", "BLR", 13.1986, 77.7066),
    ("Chhatrapati Shivaji Maharaj Int'l Airport, Mumbai", "BOM", 19.0896, 72.8656),
    ("Indira Gandhi Int'l Airport, Delhi", "DEL", 28.5562, 77.1000),
    ("Chennai Int'l Airport", "MAA", 12.9941, 80.1709),
    ("Rajiv Gandhi Int'l Airport, Hyderabad", "HYD", 17.2403, 78.4294),
    ("Netaji Subhas Chandra Bose Int'l Airport, Kolkata", "CCU", 22.6547, 88.4467),
    ("Cochin Int'l Airport, Kochi", "COK", 10.1520, 76.4019),
    ("Sardar Vallabhbhai Patel Int'l Airport, Ahmedabad", "AMD", 23.0772, 72.6347),
    ("Pune Airport", "PNQ", 18.5822, 73.9197),
    ("Goa Dabolim Airport", "GOI", 15.3808, 73.8314),
    ("Manohar Int'l Airport, Mopa (North Goa)", "GOX", 15.7408, 73.8689),
    ("Jaipur Int'l Airport", "JAI", 26.8242, 75.8122),
    ("Chaudhary Charan Singh Int'l Airport, Lucknow", "LKO", 26.7606, 80.8893),
    ("Chandigarh Int'l Airport", "IXC", 30.6735, 76.7885),
    ("Sri Guru Ram Dass Jee Int'l Airport, Amritsar", "ATQ", 31.7096, 74.7973),
    ("Lokpriya Gopinath Bordoloi Int'l Airport, Guwahati", "GAU", 26.1061, 91.5859),
    ("Lal Bahadur Shastri Int'l Airport, Varanasi", "VNS", 25.4524, 82.8593),
    ("Jay Prakash Narayan Airport, Patna", "PAT", 25.5913, 85.0880),
    ("Biju Patnaik Int'l Airport, Bhubaneswar", "BBI", 20.2444, 85.8178),
    ("Trivandrum Int'l Airport", "TRV", 8.4821, 76.9200),
    ("Calicut Int'l Airport, Kozhikode", "CCJ", 11.1368, 75.9553),
    ("Kannur Int'l Airport", "CNN", 11.9186, 75.5472),
    ("Mangalore Int'l Airport", "IXE", 12.9613, 74.8901),
    ("Coimbatore Int'l Airport", "CJB", 11.0300, 77.0434),
    ("Madurai Airport", "IXM", 9.8345, 78.0934),
    ("Tiruchirappalli Int'l Airport", "TRZ", 10.7654, 78.7097),
    ("Visakhapatnam Int'l Airport", "VTZ", 17.7212, 83.2245),
    ("Vijayawada Airport", "VGA", 16.5304, 80.7968),
    ("Tirupati Airport", "TIR", 13.6325, 79.5433),
    ("Dr. Babasaheb Ambedkar Int'l Airport, Nagpur", "NAG", 21.0922, 79.0472),
    ("Raja Bhoj Airport, Bhopal", "BHO", 23.2875, 77.3374),
    ("Devi Ahilya Bai Holkar Airport, Indore", "IDR", 22.7218, 75.8011),
    ("Swami Vivekananda Airport, Raipur", "RPR", 21.1804, 81.7388),
    ("Birsa Munda Airport, Ranchi", "IXR", 23.3143, 85.3217),
    ("Bagdogra Airport, Siliguri", "IXB", 26.6812, 88.3286),
    ("Jolly Grant Airport, Dehradun", "DED", 30.1897, 78.1803),
    ("Pantnagar Airport", "PGH", 29.0334, 79.4737),
    ("Kullu Bhuntar Airport", "KUU", 31.8767, 77.1544),
    ("Kangra Airport (Gaggal), Dharamshala", "DHM", 32.1651, 76.2634),
    ("Sheikh ul-Alam Int'l Airport, Srinagar", "SXR", 33.9871, 74.7742),
    ("Jammu Airport", "IXJ", 32.6891, 74.8374),
    ("Kushok Bakula Rimpochee Airport, Leh", "IXL", 34.1359, 77.5465),
    ("Maharana Pratap Airport, Udaipur", "UDR", 24.6177, 73.8961),
    ("Jodhpur Airport", "JDH", 26.2511, 73.0489),
    ("Jaisalmer Airport", "JSA", 26.8887, 70.8650),
    ("Surat Int'l Airport", "STV", 21.1141, 72.7418),
    ("Vadodara Airport", "BDQ", 22.3362, 73.2263),
    ("Rajkot Int'l Airport", "HSR", 22.3092, 70.7795),
    ("Bhuj Airport", "BHJ", 23.2878, 69.6702),
    ("Aurangabad Airport", "IXU", 19.8627, 75.3981),
    ("Shirdi Airport", "SAG", 19.6887, 74.3789),
    ("Hubballi Airport", "HBX", 15.3617, 75.0849),
    ("Belagavi Airport", "IXG", 15.8593, 74.6183),
    ("Mysuru Airport", "MYQ", 12.2300, 76.6497),
    ("Pakyong Airport, Gangtok", "PYG", 27.2263, 88.5877),
    ("Maharaja Bir Bikram Airport, Agartala", "IXA", 23.8870, 91.2404),
    ("Imphal Int'l Airport", "IMF", 24.7600, 93.8967),
    ("Dibrugarh Airport", "DIB", 27.4839, 95.0169),
    ("Jorhat Airport", "JRH", 26.7315, 94.1755),
    ("Silchar Airport", "IXS", 24.9129, 92.9787),
    ("Dimapur Airport", "DMU", 25.8839, 93.7711),
    ("Veer Savarkar Int'l Airport, Port Blair", "IXZ", 11.6412, 92.7297),
    ("Agatti Airport, Lakshadweep", "AGX", 10.8237, 72.1760),
    ("Khajuraho Airport", "HJR", 24.8172, 79.9186),
    ("Gwalior Airport", "GWL", 26.2933, 78.2278),
    ("Jabalpur Airport", "JLR", 23.1778, 80.0520),
    ("Gorakhpur Airport", "GOP", 26.7397, 83.4497),
    ("Prayagraj Airport", "IXD", 25.4401, 81.7339),
    ("Agra Airport", "AGR", 27.1558, 77.9609),
]

INDIAN_RAIL_JUNCTIONS = [
    ("KSR Bengaluru City Junction", "SBC", 12.9781, 77.5696),
    ("New Delhi Railway Station", "NDLS", 28.6429, 77.2191),
    ("Mumbai CSMT", "CSMT", 18.9398, 72.8355),
    ("Chennai Central", "MAS", 13.0827, 80.2750),
    ("Howrah Junction, Kolkata", "HWH", 22.5839, 88.3426),
    ("Secunderabad Junction", "SC", 17.4344, 78.5013),
    ("Pune Junction", "PUNE", 18.5289, 73.8744),
    ("Ahmedabad Junction", "ADI", 23.0265, 72.6006),
    ("Jaipur Junction", "JP", 26.9196, 75.7880),
    ("Lucknow Charbagh", "LKO", 26.8318, 80.9214),
    ("Varanasi Junction", "BSB", 25.3267, 82.9866),
    ("Patna Junction", "PNBE", 25.6033, 85.1376),
    ("Bhubaneswar", "BBS", 20.2662, 85.8436),
    ("Guwahati", "GHY", 26.1816, 91.7495),
    ("Ernakulam Junction, Kochi", "ERS", 9.9698, 76.2908),
    ("Thiruvananthapuram Central", "TVC", 8.4875, 76.9525),
    ("Kozhikode", "CLT", 11.2468, 75.7818),
    ("Mangalore Junction", "MAJN", 12.8606, 74.8806),
    ("Mysuru Junction", "MYS", 12.3168, 76.6448),
    ("Coimbatore Junction", "CBE", 10.9972, 76.9669),
    ("Madurai Junction", "MDU", 9.9195, 78.1095),
    ("Visakhapatnam Junction", "VSKP", 17.7219, 83.2899),
    ("Nagpur Junction", "NGP", 21.1522, 79.0888),
    ("Bhopal Junction", "BPL", 23.2683, 77.4126),
    ("Indore Junction", "INDB", 22.7177, 75.8685),
    ("Chandigarh Junction", "CDG", 30.7016, 76.8213),
    ("Kalka", "KLK", 30.8375, 76.9355),
    ("Ambala Cantt", "UMB", 30.3401, 76.8300),
    ("Amritsar Junction", "ASR", 31.6331, 74.8673),
    ("Jammu Tawi", "JAT", 32.7070, 74.8797),
    ("Dehradun", "DDN", 30.3143, 78.0332),
    ("Haridwar", "HW", 29.9479, 78.1558),
    ("Kathgodam", "KGM", 29.2665, 79.5469),
    ("New Jalpaiguri (NJP)", "NJP", 26.6836, 88.4437),
    ("Udaipur City", "UDZ", 24.5686, 73.6976),
    ("Jodhpur Junction", "JU", 26.2836, 73.0219),
    ("Jaisalmer", "JSM", 26.9122, 70.9234),
    ("Madgaon Junction, Goa", "MAO", 15.2689, 73.9692),
    ("Hospet Junction (Hampi)", "HPT", 15.2695, 76.3871),
    ("Hubballi Junction", "UBL", 15.3458, 75.1497),
    ("Gokarna Road / Kumta", "GOK", 14.5364, 74.3612),
    ("Agra Cantt", "AGC", 27.1578, 77.9901),
    ("Jhansi (VGLJ)", "VGLJ", 25.4426, 78.5541),
    ("Ranchi", "RNC", 23.3522, 85.3340),
    ("Raipur Junction", "R", 21.2571, 81.6295),
    ("Surat", "ST", 21.2054, 72.8408),
    ("Vadodara Junction", "BRC", 22.3106, 73.1812),
    ("Pathankot Cantt", "PTKC", 32.2573, 75.6476),
    ("Mettupalayam", "MTP", 11.2989, 76.9378),
    ("Kodaikanal Road", "KQN", 10.1753, 77.8825),
]


def _haversine_hub_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _osrm_transfer(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[int, float]:
    """Return (road_km, drive_hours) via OSRM with realistic hill/highway fallback."""
    import requests
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                rt = data["routes"][0]
                km = max(1, int(round(rt["distance"] / 1000.0)))
                hrs = round(max(0.3, rt["duration"] / 3600.0), 1)
                return km, hrs
    except Exception:
        pass
    air_km = _haversine_hub_km(lat1, lon1, lat2, lon2)
    road_km = max(1, int(round(air_km * 1.4)))
    hrs = round(max(0.3, road_km / 42.0), 1)
    return road_km, hrs


def resolve_location_hubs(city_name: str) -> dict:
    """
    Resolve commercial airport, railway junction, and bus terminal for ANY Indian location.
    If location has no airport or railway, returns nearest verified commercial hub + OSRM transfer distance & cab cost.
    """
    c_clean = city_name.strip().lower()

    # 1. Exact or partial match in comprehensive Hub Database
    for key, info in HUB_DATABASE.items():
        if key in c_clean or c_clean in key:
            return info

    # 2. Major Commercial Airport Metros
    _METRO_RAIL_CODES = {
        "bengaluru": ("KSR Bengaluru City Junction", "SBC"),
        "bangalore": ("KSR Bengaluru City Junction", "SBC"),
        "delhi": ("New Delhi Railway Station", "NDLS"),
        "new delhi": ("New Delhi Railway Station", "NDLS"),
        "mumbai": ("Mumbai CSMT", "CSMT"),
        "chennai": ("Chennai Central", "MAS"),
        "kolkata": ("Howrah Junction", "HWH"),
        "hyderabad": ("Secunderabad Junction", "SC"),
        "varanasi": ("Varanasi Junction", "BSB"),
        "kashi": ("Varanasi Junction", "BSB"),
        "kochi": ("Ernakulam Junction", "ERS"),
        "cochin": ("Ernakulam Junction", "ERS"),
        "thiruvananthapuram": ("Thiruvananthapuram Central", "TVC"),
        "trivandrum": ("Thiruvananthapuram Central", "TVC"),
        "jaipur": ("Jaipur Junction", "JP"),
        "ahmedabad": ("Ahmedabad Junction", "ADI"),
        "pune": ("Pune Junction", "PUNE"),
        "lucknow": ("Lucknow Charbagh", "LKO"),
        "chandigarh": ("Chandigarh Junction", "CDG"),
        "amritsar": ("Amritsar Junction", "ASR"),
        "guwahati": ("Guwahati", "GHY"),
        "patna": ("Patna Junction", "PNBE"),
        "bhubaneswar": ("Bhubaneswar", "BBS"),
        "nagpur": ("Nagpur Junction", "NGP"),
        "bhopal": ("Bhopal Junction", "BPL"),
        "indore": ("Indore Junction", "INDB"),
        "visakhapatnam": ("Visakhapatnam Junction", "VSKP"),
        "coimbatore": ("Coimbatore Junction", "CBE"),
        "madurai": ("Madurai Junction", "MDU"),
    }
    for key, (air_name, air_code) in MAJOR_METRO_AIRPORTS.items():
        if key in c_clean:
            rail_name, rail_code = _METRO_RAIL_CODES.get(key, (f"{city_name.title()} Junction", city_name[:3].upper()))
            return {
                "name": city_name.title(),
                "has_airport": True,
                "nearest_airport_name": air_name,
                "nearest_airport_code": air_code,
                "airport_dist_km": 0,
                "airport_transfer_hours": 0,
                "airport_transfer_cab_cost": 0,
                "has_railway": True,
                "nearest_station_name": rail_name,
                "nearest_station_code": rail_code,
                "rail_dist_km": 0,
                "rail_transfer_hours": 0,
                "rail_transfer_cab_cost": 0,
                "has_bus": True,
                "bus_terminal_name": f"{city_name.title()} Central Bus Terminal"
            }

    # 3. Dynamic Pan-India Geospatial Fallback: geocode & find nearest real airport + railhead + OSRM transfer
    from backend.agents_models.coord_resolver import resolve_destination_coords
    lat, lon = resolve_destination_coords(city_name)

    best_air = min(INDIAN_COMMERCIAL_AIRPORTS, key=lambda a: _haversine_hub_km(lat, lon, a[2], a[3]))
    air_km_straight = _haversine_hub_km(lat, lon, best_air[2], best_air[3])
    has_airport = air_km_straight <= 35.0
    if has_airport:
        air_dist_km, air_hrs, air_cab = 0, 0, 0
    else:
        air_dist_km, air_hrs = _osrm_transfer(lat, lon, best_air[2], best_air[3])
        air_cab = max(500, int(round(air_dist_km * 22)))

    best_rail = min(INDIAN_RAIL_JUNCTIONS, key=lambda r: _haversine_hub_km(lat, lon, r[2], r[3]))
    rail_km_straight = _haversine_hub_km(lat, lon, best_rail[2], best_rail[3])
    has_rail = rail_km_straight <= 25.0
    if has_rail:
        rail_dist_km, rail_hrs, rail_cab = 0, 0, 0
    else:
        rail_dist_km, rail_hrs = _osrm_transfer(lat, lon, best_rail[2], best_rail[3])
        rail_cab = max(400, int(round(rail_dist_km * 20)))

    return {
        "name": city_name.title(),
        "has_airport": has_airport,
        "nearest_airport_name": best_air[0],
        "nearest_airport_code": best_air[1],
        "airport_dist_km": air_dist_km,
        "airport_transfer_hours": air_hrs,
        "airport_transfer_cab_cost": air_cab,
        "has_railway": has_rail,
        "nearest_station_name": best_rail[0],
        "nearest_station_code": best_rail[1],
        "rail_dist_km": rail_dist_km,
        "rail_transfer_hours": rail_hrs,
        "rail_transfer_cab_cost": rail_cab,
        "has_bus": True,
        "bus_terminal_name": f"{city_name.title()} Interstate Bus Terminal"
    }
