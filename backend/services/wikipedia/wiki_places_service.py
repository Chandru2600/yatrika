"""
Wikipedia / Wikimedia Commons Real Places Service
Fetches real, authentic visitor photos and historical summaries for tourist attractions
across India without requiring any API keys.
Includes persistent disk caching for ultra-fast <5ms lookups.
"""

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CACHE_FILE = CACHE_DIR / "wiki_places_cache.json"

_MEM_CACHE = None


def _load_cache():
    global _MEM_CACHE
    if _MEM_CACHE is not None:
        return _MEM_CACHE
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _MEM_CACHE = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read wiki places cache: {e}")
            _MEM_CACHE = {}
    else:
        _MEM_CACHE = {}
    return _MEM_CACHE


def _save_cache():
    if _MEM_CACHE is None:
        return
    try:
        data_to_save = dict(_MEM_CACHE)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to persist wiki places cache: {e}")


def _normalize_key(name: str, dest: str = "") -> str:
    combined = f"{name}_{dest}".lower().strip()
    return re.sub(r"[^a-z0-9_]+", "", combined.replace(" ", "_"))


def get_real_place_data(name: str, destination: str = "") -> dict:
    """
    Lookup authentic photo & summary for an attraction name using Wikipedia REST API.
    Returns: {"img": str or None, "desc": str or None, "title": str or None}
    """
    cache = _load_cache()
    key = _normalize_key(name, destination)
    
    if key in cache:
        return cache[key]

    clean_name = re.sub(r"\(.*?\)", "", name).strip()
    c_lower = clean_name.lower()

    # Intelligent alias mappings for prominent Indian landmarks
    ALIASES = {
        "namdroling": "Namdroling Monastery",
        "golden temple": "Namdroling Monastery" if "coorg" in destination.lower() or "karnataka" in destination.lower() else "Golden Temple",
        "bylakuppe": "Namdroling Monastery",
        "tadiyandmol": "Tadiandamol",
        "tadiandamol": "Tadiandamol",
        "talakaveri": "Talakaveri",
        "talacauvery": "Talakaveri",
        "omkareshwara": "Omkareshwara Temple, Madikeri",
        "dubare": "Dubare",
        "nagarhole": "Nagarhole National Park",
        "pushpagiri": "Pushpagiri Wildlife Sanctuary",
        "mullayanagiri": "Mullayanagiri",
        "baba budangiri": "Baba Budangiri",
        "kudremukh": "Kudremukh",
        "hebbe": "Hebbe Falls",
        "kalhatti": "Kalhatti Falls",
        "bhadra": "Bhadra Wildlife Sanctuary",
        "kemmangundi": "Kemmangundi",
    }

    alias_target = None
    for kw, target in ALIASES.items():
        if kw in c_lower:
            alias_target = target
            break

    search_queries = []
    if alias_target:
        search_queries.append(alias_target)
    search_queries.extend([
        clean_name,
        f"{clean_name}, {destination}" if destination else clean_name,
        clean_name.replace(" ", "_"),
    ])
    if destination:
        search_queries.append(f"{clean_name} ({destination})")


    result = {"img": None, "desc": None, "title": None}

    headers = {
        "User-Agent": "YatrikaTravelPlanner/2.0 (student-ai-travel-project@yatrika.app; +https://yatrika.app)"
    }

    # 1. Try direct page summary
    for q in search_queries:
        encoded = urllib.parse.quote(q.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    img = data.get("thumbnail", {}).get("source") or data.get("originalimage", {}).get("source")
                    desc = data.get("extract")
                    if img or desc:
                        result["img"] = img
                        result["desc"] = desc
                        result["title"] = data.get("title")
                        break
        except Exception:
            continue

    # 2. If direct title lookup missed, use Wikipedia Search API to find closest match
    if not result["img"]:
        try:
            search_url = (
                f"https://en.wikipedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(clean_name + ' ' + destination)}&gsrlimit=1"
                f"&prop=pageimages|extracts&piprop=thumbnail&pithumbsize=600&exintro=1&explaintext=1&format=json"
            )
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    pages = data.get("query", {}).get("pages", {})
                    for _, pdata in pages.items():
                        img = pdata.get("thumbnail", {}).get("source")
                        desc = pdata.get("extract")
                        if img or desc:
                            result["img"] = img or result["img"]
                            result["desc"] = desc or result["desc"]
                            result["title"] = pdata.get("title")
                            break
        except Exception:
            pass

    # Save to persistent cache so we never re-request
    cache[key] = result
    _save_cache()
    return result


def batch_get_real_places(places_and_dest_list: list) -> dict:
    """
    Fetch real place photos & descriptions for multiple (name, dest) pairs concurrently.
    Returns dict mapping (name, dest) -> place_data
    """
    import concurrent.futures
    cache = _load_cache()
    out = {}
    missing = []
    
    for item in places_and_dest_list:
        if isinstance(item, tuple):
            name, dest = item
        else:
            name, dest = item, ""
        key = _normalize_key(name, dest)
        if key in cache:
            out[(name, dest)] = cache[key]
        else:
            missing.append((name, dest))

    if missing:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_item = {
                executor.submit(get_real_place_data, nm, dst): (nm, dst)
                for (nm, dst) in missing
            }
            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    out[item] = future.result()
                except Exception:
                    out[item] = {"img": None, "desc": None, "title": None}

    return out

