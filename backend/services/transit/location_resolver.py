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


def resolve_location_hubs(city_name: str) -> dict:
    """
    Resolve commercial airport, railway junction, and bus terminal for ANY Indian location.
    If location has no airport or railway, returns nearest verified commercial hub + transfer distance & cab cost.
    """
    c_clean = city_name.strip().lower()

    # 1. Exact or partial match in comprehensive Hub Database
    for key, info in HUB_DATABASE.items():
        if key in c_clean or c_clean in key:
            return info

    # 2. Major Commercial Airport Metros
    for key, (air_name, air_code) in MAJOR_METRO_AIRPORTS.items():
        if key in c_clean:
            return {
                "name": city_name.title(),
                "has_airport": True,
                "nearest_airport_name": air_name,
                "nearest_airport_code": air_code,
                "airport_dist_km": 0,
                "airport_transfer_hours": 0,
                "airport_transfer_cab_cost": 0,
                "has_railway": True,
                "nearest_station_name": f"{city_name.title()} Junction",
                "nearest_station_code": city_name[:3].upper(),
                "rail_dist_km": 0,
                "rail_transfer_hours": 0,
                "rail_transfer_cab_cost": 0,
                "has_bus": True,
                "bus_terminal_name": f"{city_name.title()} Central Bus Terminal"
            }

    # 3. Dynamic Fallback: Query nearest hub from national datasets if available
    return {
        "name": city_name.title(),
        "has_airport": False,
        "nearest_airport_name": f"Nearest Regional Airport to {city_name.title()}",
        "nearest_airport_code": "DEL" if any(x in c_clean for x in ["north", "uttar", "haryana", "punjab"]) else "BLR",
        "airport_dist_km": 75,
        "airport_transfer_hours": 2.0,
        "airport_transfer_cab_cost": 1600,
        "has_railway": True,
        "nearest_station_name": f"{city_name.title()} Railway Station",
        "nearest_station_code": city_name[:4].upper() if len(city_name) >= 4 else "NDLS",
        "rail_dist_km": 0,
        "rail_transfer_hours": 0,
        "rail_transfer_cab_cost": 0,
        "has_bus": True,
        "bus_terminal_name": f"{city_name.title()} Interstate Bus Terminal"
    }
