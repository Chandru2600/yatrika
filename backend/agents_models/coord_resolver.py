"""
Shared Geospatial Coordinate Resolver for Indian Destinations & Transit Hubs.
Integrates:
1. Curated 55+ Indian Tourism & Hill Station Centroids
2. 5,000 Transit Hub Cities (3_All_India_Transit_Hub_Cities_5000.csv)
3. 10,025 Verified Indian Tourist Attractions (1_All_India_Tourist_Attractions_10025.csv)
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEST_COORDS = {
    # Karnataka
    "coorg": (12.4244, 75.7382),
    "madikeri": (12.4244, 75.7382),
    "kodagu": (12.4244, 75.7382),
    "chikmagalur": (13.3161, 75.7720),
    "chikkamagaluru": (13.3161, 75.7720),
    "samse": (13.2389, 75.3856),
    "kalasa": (13.2389, 75.3856),
    "kudremukh": (13.2167, 75.2500),
    "kudremukha": (13.2167, 75.2500),
    "hampi": (15.3350, 76.4600),
    "gokarna": (14.5479, 74.3188),
    "mysore": (12.2958, 76.6394),
    "mysuru": (12.2958, 76.6394),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "sakleshpur": (12.9440, 75.7865),
    "dandeli": (15.2415, 74.6223),
    "badami": (15.9189, 75.6766),
    "pattadakal": (15.9483, 75.8160),
    "bandipur": (11.6664, 76.6291),
    "kabini": (11.9324, 76.2730),
    "udupi": (13.3409, 74.7421),
    "mangalore": (12.9141, 74.8560),

    # Kerala
    "munnar": (10.0889, 77.0595),
    "alleppey": (9.4981, 76.3388),
    "alappuzha": (9.4981, 76.3388),
    "wayanad": (11.6854, 76.1320),
    "varkala": (8.7379, 76.7163),
    "kochi": (9.9312, 76.2673),
    "cochin": (9.9312, 76.2673),
    "thekkady": (9.6031, 77.1615),
    "periyar": (9.6031, 77.1615),
    "kovalam": (8.4004, 76.9787),
    "kumarakom": (9.6175, 76.4301),

    # Goa
    "goa": (15.2993, 74.1240),
    "panaji": (15.4909, 73.8278),
    "north goa": (15.5494, 73.7535),
    "south goa": (15.2048, 73.9856),

    # Tamil Nadu
    "ooty": (11.4102, 76.6950),
    "udhagamandalam": (11.4102, 76.6950),
    "kodaikanal": (10.2381, 77.4892),
    "pondicherry": (11.9416, 79.8083),
    "puducherry": (11.9416, 79.8083),
    "madurai": (9.9252, 78.1198),
    "rameshwaram": (9.2876, 79.3129),
    "mahabalipuram": (12.6269, 80.1927),
    "chennai": (13.0827, 80.2707),
    "kanyakumari": (8.0883, 77.5385),

    # Himachal Pradesh
    "manali": (32.2396, 77.1887),
    "shimla": (31.1048, 77.1734),
    "dharamshala": (32.2190, 76.3234),
    "mcleod ganj": (32.2426, 76.3213),
    "kasol": (32.0100, 77.3150),
    "spiti valley": (32.2461, 78.0349),
    "spiti": (32.2461, 78.0349),
    "dalhousie": (32.5387, 75.9710),
    "khajjiar": (32.5510, 76.0610),
    "kullu": (31.9579, 77.1095),

    # Uttarakhand
    "rishikesh": (30.0869, 78.2676),
    "mussoorie": (30.4598, 78.0644),
    "nainital": (29.3919, 79.4542),
    "haridwar": (29.9457, 78.1642),
    "jim corbett": (29.5300, 78.7747),
    "corbett": (29.5300, 78.7747),
    "auli": (30.5310, 79.5694),
    "dehradun": (30.3165, 78.0322),

    # Rajasthan
    "jaipur": (26.9124, 75.7873),
    "udaipur": (24.5854, 73.7125),
    "jodhpur": (26.2389, 73.0243),
    "jaisalmer": (26.9157, 70.9083),
    "pushkar": (26.4899, 74.5511),
    "ranthambore": (26.0173, 76.5026),
    "mount abu": (24.5925, 72.7156),

    # Maharashtra
    "mumbai": (19.0760, 72.8777),
    "pune": (18.5204, 73.8567),
    "lonavala": (18.7557, 73.4091),
    "mahabaleshwar": (17.9237, 73.6586),
    "panchgani": (17.9237, 73.8016),
    "alibaug": (18.6414, 72.8722),

    # North & East & Central
    "delhi": (28.7041, 77.1025),
    "new delhi": (28.6139, 77.2090),
    "agra": (27.1767, 78.0081),
    "varanasi": (25.3176, 82.9739),
    "amritsar": (31.6340, 74.8723),
    "leh": (34.1526, 77.5771),
    "ladakh": (34.1526, 77.5771),
    "srinagar": (34.0837, 74.7973),
    "gulmarg": (34.0484, 74.3805),
    "darjeeling": (27.0410, 88.2663),
    "gangtok": (27.3389, 88.6065),
    "shillong": (25.5788, 91.8933),
    "pachmarhi": (22.4674, 78.4346),
    "khajuraho": (24.8318, 79.9199),
    "puri": (19.8135, 85.8312),
    "kolkata": (22.5726, 88.3639),
    "kaza": (32.2244, 78.0723),
    "tawang": (27.5861, 91.8594),
    "bhuj": (23.2420, 69.6669),
    "aurangabad": (19.8762, 75.3433)
}

_CACHE = {}
_HUBS_DF = None
_ATTRACTIONS_DF = None


def _get_hubs_df():
    global _HUBS_DF
    if _HUBS_DF is not None:
        return _HUBS_DF
    p = BASE_DIR / "FACULTY_EVALUATION_DATASETS" / "3_All_India_Transit_Hub_Cities_5000.csv"
    if p.exists():
        try:
            df = pd.read_csv(p)
            df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
            df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
            _HUBS_DF = df.dropna(subset=["latitude", "longitude"])
        except Exception:
            _HUBS_DF = None
    return _HUBS_DF


def _get_attractions_df():
    global _ATTRACTIONS_DF
    if _ATTRACTIONS_DF is not None:
        return _ATTRACTIONS_DF
    p = BASE_DIR / "FACULTY_EVALUATION_DATASETS" / "1_All_India_Tourist_Attractions_10025.csv"
    if p.exists():
        try:
            df = pd.read_csv(p)
            df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
            df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
            df = df.dropna(subset=["Latitude", "Longitude"])
            # Do not resolve coordinates against generic numbered placeholders or ASI protected tags
            clean_mask = ~df["Name"].astype(str).str.contains(r'(?i)ASI Monument|Monument\s*#|#\d+|Protected Heritage', regex=True)
            _ATTRACTIONS_DF = df[clean_mask]
        except Exception:
            _ATTRACTIONS_DF = None
    return _ATTRACTIONS_DF


def resolve_destination_coords(destination: str) -> tuple:
    """
    Resolves the exact (latitude, longitude) for any Indian destination.
    Returns: (latitude: float, longitude: float)
    """
    if not destination:
        return (12.4244, 75.7382)

    dest_clean = destination.strip()
    d_lower = dest_clean.lower()

    if d_lower in _CACHE:
        return _CACHE[d_lower]

    # 1. Exact match in curated DEST_COORDS
    if d_lower in DEST_COORDS:
        _CACHE[d_lower] = DEST_COORDS[d_lower]
        return DEST_COORDS[d_lower]

    # 2. Key contained in destination (e.g. "North Goa Beach Trip" contains "north goa")
    # Sort keys by length descending so longer/more specific entries match first
    for k in sorted(DEST_COORDS.keys(), key=len, reverse=True):
        if k in d_lower:
            _CACHE[d_lower] = DEST_COORDS[k]
            return DEST_COORDS[k]

    # 3. Destination contained in key (e.g. "chikmagal" in "chikmagalur") - only if len >= 4
    if len(d_lower) >= 4:
        for k in sorted(DEST_COORDS.keys(), key=len, reverse=True):
            if d_lower in k:
                _CACHE[d_lower] = DEST_COORDS[k]
                return DEST_COORDS[k]

    # 4. Match in 5,000 Transit Hubs dataset
    hubs = _get_hubs_df()
    if hubs is not None and not hubs.empty:
        # Match exact city_name first
        m_exact = hubs[hubs["city_name"].astype(str).str.lower() == d_lower]
        if not m_exact.empty:
            coords = (float(m_exact.iloc[0]["latitude"]), float(m_exact.iloc[0]["longitude"]))
            _CACHE[d_lower] = coords
            return coords
        match = hubs[hubs["city_name"].astype(str).str.lower().str.contains(d_lower, regex=False)]
        if not match.empty:
            coords = (float(match.iloc[0]["latitude"]), float(match.iloc[0]["longitude"]))
            _CACHE[d_lower] = coords
            return coords

    # 5. Match in 10,025 Attractions dataset
    attractions = _get_attractions_df()
    if attractions is not None and not attractions.empty:
        # Match exact City first
        m_city_exact = attractions[attractions["City"].astype(str).str.lower() == d_lower]
        if not m_city_exact.empty:
            coords = (float(m_city_exact.iloc[0]["Latitude"]), float(m_city_exact.iloc[0]["Longitude"]))
            _CACHE[d_lower] = coords
            return coords

        # Match City contains
        m_city = attractions[attractions["City"].astype(str).str.lower().str.contains(d_lower, regex=False)]
        if not m_city.empty:
            coords = (float(m_city.iloc[0]["Latitude"]), float(m_city.iloc[0]["Longitude"]))
            _CACHE[d_lower] = coords
            return coords

        # Match Name with word boundary to avoid false substring matches (e.g. Kaza vs Kazakhstan)
        import re
        pattern = r'\b' + re.escape(d_lower) + r'\b'
        m_name = attractions[attractions["Name"].astype(str).str.lower().str.contains(pattern, regex=True)]
        if not m_name.empty:
            coords = (float(m_name.iloc[0]["Latitude"]), float(m_name.iloc[0]["Longitude"]))
            _CACHE[d_lower] = coords
            return coords

    # 6. Try OpenStreetMap Nominatim geocode fallback
    try:
        import requests
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{dest_clean}, India", "format": "json", "limit": 1},
            headers={"User-Agent": "YatrikaTravelAgent/2.0"},
            timeout=2.5
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                coords = (float(data[0]["lat"]), float(data[0]["lon"]))
                _CACHE[d_lower] = coords
                return coords
    except Exception:
        pass

    # Default fallback to Coorg if completely unrecognized
    fallback = (12.4244, 75.7382)
    _CACHE[d_lower] = fallback
    return fallback
