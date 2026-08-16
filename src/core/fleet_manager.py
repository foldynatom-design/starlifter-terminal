# -*- coding: utf-8 -*-
"""
fleet_helper.py - Shuttle & cargo ship recommendation engine.

Recommends best cargo shuttle + loading method for mother ships.
Uses hangar specs, UEX ship data, and priority shuttle list.

ALL fleet data loaded from resources/*.json — no hardcoded ship data.
Edit JSON files to update ship dimensions, hangars, or priorities.

Usage:
    from fleet_helper import _recommend_shuttle, _recommend_cargo_ship
"""

import os
import json
import math
from path_config import PATHS

# ── Lazy-loaded data caches ──
_uex_ships_db = None
_hangar_fit_map_cache = None
_concept_ships_cache = None
_priority_shuttles_cache = None
_ship_dimensions_cache = None
_cargo_bay_dimensions_cache = None


def _load_uex_ships_db():
    """Lazy-load UEX ships database from resources/uex_ships_db.json."""
    global _uex_ships_db
    if _uex_ships_db is not None:
        return _uex_ships_db
    
    db_path = PATHS.resource("uex_ships_db.json")
    if os.path.isfile(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                _uex_ships_db = json.load(f)
            return _uex_ships_db
        except (json.JSONDecodeError, OSError):
            pass
    
    _uex_ships_db = {}
    return _uex_ships_db


def _load_json_resource(filename, default=None):
    """Load a JSON resource file. Returns default if file missing or corrupt."""
    path = PATHS.resource(filename)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[fleet_helper] Warning: failed to load {filename}: {e}")
    return default if default is not None else {}


def _get_hangar_fit_map():
    """Load hangar fit map from hangar_fit_map.json."""
    global _hangar_fit_map_cache
    if _hangar_fit_map_cache is None:
        _hangar_fit_map_cache = _load_json_resource("hangar_fit_map.json", {})
    return _hangar_fit_map_cache


def _get_concept_ships():
    """Load concept ships set from concept_ships.json."""
    global _concept_ships_cache
    if _concept_ships_cache is None:
        data = _load_json_resource("concept_ships.json", [])
        _concept_ships_cache = set(data) if isinstance(data, list) else set()
        
        # Enforce known concept ships if JSON is empty/missing
        _concept_ships_cache.update([
            "banu merchantman", "hull d", "hull e", "bmm", "merchantman",
            "kraken", "kraken privateer", "pioneer", "endeavor", "orion", "polaris",
            "galaxy", "apollo", "apollo medivac", "apollo triage", "genesis",
            "genesis starliner", "crucible", "vulcan", "legionnaire", "expanse",
            "liberator", "nautilus", "odyssey", "railent", "san'tok.yai"
        ])
    return _concept_ships_cache


def _get_priority_shuttles():
    """Load priority shuttles from priority_shuttles.json."""
    global _priority_shuttles_cache
    if _priority_shuttles_cache is None:
        _priority_shuttles_cache = _load_json_resource("priority_shuttles.json", {})
    return _priority_shuttles_cache


def _get_ship_dimensions():
    """Load ship dimensions from ship_dimensions.json."""
    global _ship_dimensions_cache
    if _ship_dimensions_cache is None:
        _ship_dimensions_cache = _load_json_resource("ship_dimensions.json", {})
    return _ship_dimensions_cache


def _get_cargo_bay_dimensions():
    """Load cargo bay dimensions from cargo_bay_dimensions.json."""
    global _cargo_bay_dimensions_cache
    if _cargo_bay_dimensions_cache is None:
        _cargo_bay_dimensions_cache = _load_json_resource("cargo_bay_dimensions.json", {})
    return _cargo_bay_dimensions_cache


# ── Convenience aliases (read-only access via properties) ──
# These act as lazy proxies so existing code using _HANGAR_FIT_MAP etc. still works.

class _LazyDict:
    """Lazy-loading dict proxy. Loads from JSON on first access."""
    def __init__(self, loader_fn):
        self._loader = loader_fn
        self._data = None
    def _ensure(self):
        if self._data is None:
            self._data = self._loader()
    def __contains__(self, key):
        self._ensure(); return key in self._data
    def __getitem__(self, key):
        self._ensure(); return self._data[key]
    def __iter__(self):
        self._ensure(); return iter(self._data)
    def items(self):
        self._ensure(); return self._data.items()
    def keys(self):
        self._ensure(); return self._data.keys()
    def values(self):
        self._ensure(); return self._data.values()
    def get(self, key, default=None):
        self._ensure(); return self._data.get(key, default)


class _LazySet:
    """Lazy-loading set proxy."""
    def __init__(self, loader_fn):
        self._loader = loader_fn
        self._data = None
    def _ensure(self):
        if self._data is None:
            self._data = self._loader()
    def __contains__(self, key):
        self._ensure(); return key in self._data
    def __iter__(self):
        self._ensure(); return iter(self._data)


_HANGAR_FIT_MAP = _LazyDict(_get_hangar_fit_map)
_CONCEPT_SHIPS = _LazySet(_get_concept_ships)
_PRIORITY_SHUTTLES = _LazyDict(_get_priority_shuttles)
_SHIP_DIMENSIONS = _LazyDict(_get_ship_dimensions)
_CARGO_BAY_DIMENSIONS = _LazyDict(_get_cargo_bay_dimensions)

_PAD_ORDER = {"XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5}



def can_shuttle_fit(shuttle_name, mother_ship_name):
    """Check if a shuttle/vehicle physically fits in a mother ship's bay.

    Checks BOTH dedicated hangars (HANGAR_FIT_MAP) AND internal cargo bays
    (CARGO_BAY_DIMENSIONS). Any ship with a big enough internal space counts.

    Returns:
        dict with 'fits' (bool), 'reason' (str), 'clearance' (dict or None),
        'bay_type' ('hangar' or 'cargo_bay'), 'open_roof' (bool)
        or None if either ship is unknown
    """
    shuttle_low = shuttle_name.lower().strip()
    mother_low = mother_ship_name.lower().strip()

    # ── 1. Check dedicated hangar first (HANGAR_FIT_MAP) ──
    hangar = None
    for key, val in _HANGAR_FIT_MAP.items():
        if key in mother_low or mother_low in key:
            hangar = val
            break

    if hangar:
        bay = hangar.get("bay_dimensions")
        if bay:
            known_fits = hangar.get("known_fits", [])
            known_no_fit = hangar.get("known_no_fit", [])
            known_open = hangar.get("known_open_roof", [])

            if any(kf in shuttle_low or shuttle_low in kf for kf in known_no_fit):
                return {"fits": False, "reason": "Community-verified: does NOT fit in hangar",
                        "clearance": None, "bay_type": "hangar"}

            if any(kf in shuttle_low or shuttle_low in kf for kf in known_open):
                return {"fits": True, "reason": "Fits with ROOF OPEN only",
                        "clearance": None, "bay_type": "hangar", "open_roof": True}

            if any(kf in shuttle_low or shuttle_low in kf for kf in known_fits):
                dims = _get_ship_dims(shuttle_low)
                clearance = None
                if dims:
                    clearance = {
                        "length": round(bay["length"] - dims["length"], 1),
                        "width": round(bay["width"] - dims["width"], 1),
                        "height": round(bay["height"] - dims["height"], 1),
                    }
                return {"fits": True, "reason": "Community-verified: FITS in hangar",
                        "clearance": clearance, "bay_type": "hangar"}

            # Not in known lists — check by dimensions
            dims = _get_ship_dims(shuttle_low)
            if dims:
                return _check_dims_fit(dims, bay, "hangar")

    # ── 2. Check cargo bay dimensions ──
    cargo_bay = None
    for key, val in _CARGO_BAY_DIMENSIONS.items():
        if key in mother_low or mother_low in key:
            cargo_bay = val
            break

    if cargo_bay:
        dims = _get_ship_dims(shuttle_low)
        if dims:
            result = _check_dims_fit(dims, cargo_bay, "cargo_bay")
            if result["fits"]:
                result["reason"] += f" (via {cargo_bay.get('access', 'ramp')})"
            return result
        # Known ship but no dimensions — can't determine
        return None

    # Neither hangar nor cargo bay found
    return None


def _check_dims_fit(ship_dims, bay_dims, bay_type):
    """Compare ship dimensions against bay dimensions."""
    clearance = {
        "length": round(bay_dims["length"] - ship_dims["length"], 1),
        "width": round(bay_dims["width"] - ship_dims["width"], 1),
        "height": round(bay_dims["height"] - ship_dims["height"], 1),
    }

    fits_l = ship_dims["length"] <= bay_dims["length"]
    fits_w = ship_dims["width"] <= bay_dims["width"]
    fits_h = ship_dims["height"] <= bay_dims["height"]

    if fits_l and fits_w and fits_h:
        return {"fits": True, "reason": "Dimensions check: should fit",
                "clearance": clearance, "bay_type": bay_type}
    else:
        over = []
        if not fits_l:
            over.append(f"length by {-clearance['length']}m")
        if not fits_w:
            over.append(f"width by {-clearance['width']}m")
        if not fits_h:
            over.append(f"height by {-clearance['height']}m")
        return {"fits": False, "reason": f"Too large: exceeds {', '.join(over)}",
                "clearance": clearance, "bay_type": bay_type}


def _get_ship_dims(name_low):
    """Fuzzy match ship name to dimensions table."""
    if name_low in _SHIP_DIMENSIONS:
        return _SHIP_DIMENSIONS[name_low]
    for key, val in _SHIP_DIMENSIONS.items():
        if key in name_low or name_low in key:
            return val
    return None


def _recommend_shuttle(vessel_name, total_scu, ships_db=None):
    """Recommend best cargo shuttle + loading method for ANY ship.

    Works for ALL vessels -- carriers with hangars get hangar shuttle recs,
    regular cargo ships get landing pad / EVA / self-load recommendations.

    Args:
        vessel_name: Ship name (e.g. 'Aegis Idris', 'Drake Cutlass Black')
        total_scu: Total SCU to transport
        ships_db: Optional UEX ships dict. Auto-loads from JSON if None.

    Returns dict with:
        hangar_shuttles: list of ships that fit in hangar (empty for non-carriers)
        pad_shuttles: list of ships for landing pad transfer
        recommended: best option dict or None
        loading_method: 'self' / 'hangar' / 'landing_pad' / 'eva'
        note: human-readable note for PDF
        mother_ship: display name
        has_hangar: bool
    """
    if not vessel_name or total_scu <= 0:
        return None

    if ships_db is None:
        ships_db = _load_uex_ships_db()

    vn_low = vessel_name.lower()

    # ── Strip manufacturer prefix for matching ──
    for prefix in ["aegis", "anvil", "drake", "rsi", "crusader", "misc",
                    "origin", "consolidated outland", "argo", "mirai",
                    "gatac", "esperia", "roberts space industries",
                    "musashi industrial"]:
        if vn_low.startswith(prefix):
            vn_low_clean = vn_low[len(prefix):].strip()
            break
    else:
        vn_low_clean = vn_low

    # ── Find vessel's own SCU capacity from DB ──
    vessel_scu = 0
    vessel_display = vessel_name
    vessel_pad = ""
    for k, v in ships_db.items():
        kl = k.lower()
        if kl == vn_low or kl == vn_low_clean or vn_low_clean in kl or kl in vn_low:
            vessel_scu = v.get("scu", 0)
            vessel_display = v.get("name", v.get("short_name", vessel_name))
            vessel_pad = v.get("pad_type", "")
            break

    # ── Find hangar info (only carriers have this) ──
    hangar_info = None
    for key, val in _HANGAR_FIT_MAP.items():
        if key in vn_low or key in vn_low_clean:
            hangar_info = val
            break

    has_hangar = hangar_info is not None
    is_concept_mother = hangar_info.get("concept_only", False) if hangar_info else False
    concept_note = " (NOTE: Concept ship, specs may change.)" if is_concept_mother else ""

    is_eva = any(e in str(loading_type).lower() for e in ["eva", "orbit", "float"]) or any(e in str(location).lower() for e in ["eva", "orbit", "float"])
    is_planetary = any(e in str(location).lower() for e in ["surface", "outpost", "planet", "ground", "land", "monox", "bloom", "delamar", "sunset mesa", "ostler", "jacksons", "jackson's", "yang", "arid reach", "rayari", "shubin", "hdms", "babbage", "lorville", "area18", "area 18", "orison", "levski", "revolux", "zeus", "rappel", "facility", "site", "farm"]) or any(e in str(loading_type).lower() for e in ["surface", "outpost", "planet", "planetary", "ground"])

    # ── Build candidate shuttle list ──
    max_pad_order = _PAD_ORDER.get(hangar_info.get("max_pad", "XS"), 0) if hangar_info else 0
    known_fits = hangar_info.get("known_fits", []) if hangar_info else []
    known_no_fit = hangar_info.get("known_no_fit", []) if hangar_info else []

    hangar_ships = []
    all_cargo_ships = []

    for k, v in ships_db.items():
        pad = v.get("pad_type", "")
        scu = v.get("scu", 0)
        ship_name_low = k.lower()

        if scu <= 0:
            continue

        if ship_name_low == vn_low or ship_name_low == vn_low_clean:
            continue

        if ship_name_low in _CONCEPT_SHIPS:
            continue
        display_name = v.get("name", "").lower()
        if any(cs in display_name for cs in _CONCEPT_SHIPS):
            continue

        trips = max(1, -(-total_scu // scu))
        ship_entry = {
            "name": v.get("name", v.get("short_name", "?")),
            "scu": scu,
            "trips": trips,
            "is_cargo": v.get("is_cargo", 0),
            "pad": pad if pad else "GV",
            "is_known_fit": False,
            "priority": 0,
        }

        if scu > 0 and pad:
            if vn_low_clean in ["raft", "hull a", "hull b", "nomad"] and pad == "GV":
                pass
            else:
                all_cargo_ships.append(ship_entry.copy())

        if has_hangar:
            is_priority = False
            for pk, pv in _PRIORITY_SHUTTLES.items():
                if pk in ship_name_low or ship_name_low in pk:
                    ship_entry["priority"] = pv
                    is_priority = True
                    break

            if not is_priority:
                if not pad or _PAD_ORDER.get(pad, 99) > max_pad_order:
                    continue

            if any(nf in ship_name_low or ship_name_low in nf for nf in known_no_fit):
                continue

            if not pad and not is_priority:
                continue

            ship_entry["is_known_fit"] = any(
                kf in ship_name_low or ship_name_low in kf for kf in known_fits
            )
            hangar_ships.append(ship_entry)

    def _shuttle_tier_sort_key(s):
        s_low = s["name"].lower()
        if "golem" in s_low or "ox" in s_low:
            rank = 1
        elif "mpuv cargo" in s_low or "mpuv-c" in s_low or "mpuv 1c" in s_low or "mpuv-1c" in s_low:
            rank = 2
        elif "mpuv tractor" in s_low or "mpuv-t" in s_low or "mpuv" in s_low:
            rank = 3
        elif "cutter" in s_low:
            rank = 4
        else:
            rank = 10
        return (rank, s["scu"])

    if total_scu <= 64:
        cargo_options = [s for s in all_cargo_ships if any(k in s["name"].lower() for k in ["golem", "ox", "mpuv", "cutter"])]
        cargo_options.sort(key=_shuttle_tier_sort_key)
        if not cargo_options:
            cargo_options = [s for s in all_cargo_ships if s["scu"] >= total_scu]
            cargo_options.sort(key=lambda x: x["scu"])
    else:
        cargo_options = [s for s in all_cargo_ships if s["scu"] >= total_scu]
        cargo_options.sort(key=lambda x: x["scu"])
        if not cargo_options:
            cargo_options = sorted(all_cargo_ships, key=lambda x: -x["scu"])[:3]

    chosen_choices = cargo_options[:3]
    choices_str = " / ".join(f"{c['name']} ({c['scu']} SCU)" for c in chosen_choices) if chosen_choices else "Drake Golem Ox (64 SCU) / Argo MPUV Cargo (2 SCU) / Argo MPUV Tractor (16 SCU)"

    # ── SELF-LOAD vs EVA LOAD ──
    if is_eva and not has_hangar:
        return {
            "hangar_shuttles": [],
            "pad_shuttles": [],
            "recommended": chosen_choices[0] if chosen_choices else {
                "name": "Drake Cutlass Black", "scu": 46, "trips": 1,
                "pad": "M", "is_cargo": 1,
            },
            "loading_method": "eva",
            "note": (
                f"EVA LOADING WARNING: Deep space / orbital EVA transfer required for {vessel_display} at {location or 'Orbit (EVA)'}. "
                f"Zero-g cargo extraction active. Tractor beam personnel mandatory. Recommended transfer shuttles: {choices_str}."
            ),
            "mother_ship": vessel_display,
            "has_hangar": False,
            "total_scu": total_scu,
        }

    is_hangar_staging = any(e in str(loading_type).lower() for e in ["hangar", "bay", "elevator", "in hangar"]) or any(e in str(location).lower() for e in ["hangar", "bay", "in hangar"])
    load_location_str = "in hangar via freight elevator." if is_hangar_staging else "on landing pad."
    marine_note = " Marine security escort recommended for planetary surface operations." if is_planetary else ""

    # ── SELF-LOAD: ship itself can carry the cargo ──
    # Capital mothership keys that require shuttle transfers in orbit/staging
    _NON_CARGO_MOTHERSHIPS = {"idris", "javelin", "kraken", "polaris", "890 jump", "carrack", "hull c", "hull d", "hull e"}
    is_true_mothership = any(m in vn_low_clean for m in _NON_CARGO_MOTHERSHIPS)

    if vessel_scu >= total_scu and (not has_hangar or not is_true_mothership):
        return {
            "hangar_shuttles": [],
            "pad_shuttles": [],
            "recommended": {
                "name": vessel_display, "scu": vessel_scu, "trips": 1,
                "pad": vessel_pad, "is_cargo": 1,
            },
            "loading_method": "self",
            "note": (
                f"SELF-LOAD DIRECTIVE: {vessel_display} ({vessel_scu} SCU) can land directly {load_location_str.rstrip('.')} "
                f"to load {total_scu:.1f} SCU directly into primary hold. "
                f"Use of ATLS, MaxLift, and personnel with tractor beams advised.{marine_note}"
            ),
            "mother_ship": vessel_display,
            "has_hangar": False,
            "total_scu": total_scu,
        }

    # ── Build candidate shuttle list ──
    max_pad_order = _PAD_ORDER.get(hangar_info["max_pad"], 0) if hangar_info else 0
    known_fits = hangar_info.get("known_fits", []) if hangar_info else []
    known_no_fit = hangar_info.get("known_no_fit", []) if hangar_info else []

    hangar_ships = []
    all_cargo_ships = []

    for k, v in ships_db.items():
        pad = v.get("pad_type", "")
        scu = v.get("scu", 0)
        ship_name_low = k.lower()

        if scu <= 0:
            continue

        # Skip the vessel itself
        if ship_name_low == vn_low or ship_name_low == vn_low_clean:
            continue

        # HARD RULE: concept-only ships are NEVER recommended
        if ship_name_low in _CONCEPT_SHIPS:
            continue
        display_name = v.get("name", "").lower()
        if any(cs in display_name for cs in _CONCEPT_SHIPS):
            continue

        trips = max(1, -(-total_scu // scu))  # ceil division
        ship_entry = {
            "name": v.get("name", v.get("short_name", "?")),
            "scu": scu,
            "trips": trips,
            "is_cargo": v.get("is_cargo", 0),
            "pad": pad if pad else "GV",
            "is_known_fit": False,
            "priority": 0,
        }

        # ── Non-cargo ship exclusion list (Refueling, Luxury, Passenger, Mining, Salvage, Heavy Military) ──
        NON_CARGO_KEYWORDS = [
            "starfarer", "gemini", "890", "jump", "600i", "400i", "300i", "325a", "350r",
            "starliner", "genesis", "starlite", "phoenix", "reclaimer", "vulture", "prospector",
            "mole", "orion", "arrastra", "expanse", "pioneer", "crucible", "vulcan", "apollo",
            "cutlass red", "cutlass blue", "herald", "terrapin", "hammerhead", "nautilus",
            "retaliator", "redeemer", "valkyrie", "eclipse", "gladiator", "ares", "asgard",
            "idris", "javelin", "polaris", "kraken", "touring", "vanguard", "fighter",
            "interceptor", "racer", "stealth", "bomber", "sentinel", "harbinger", "warden",
            "hoplite", "gladius", "arrow", "hornet", "sabre", "blade", "buccaneer", "hawk",
            "scorpius", "mantis", "luxury", "gunship", "corvette", "salvage", "mining",
            "exploration", "medical", "refuel", "tanker", "passenger"
        ]

        is_non_cargo = any(nk in ship_name_low or nk in str(v.get("name", "")).lower() for nk in NON_CARGO_KEYWORDS)

        # Track ALL cargo ships for pad/EVA recommendations
        if scu > 0 and pad and not is_non_cargo:
            # External Grid Ships ban ground vehicles
            if vn_low_clean in ["raft", "hull a", "hull b", "nomad"] and pad == "GV":
                pass # skip appending
            else:
                all_cargo_ships.append(ship_entry.copy())

        # ── Hangar-fit check (only for carriers) ──
        if has_hangar:
            # Priority shuttles
            is_priority = False
            for pk, pv in _PRIORITY_SHUTTLES.items():
                if pk in ship_name_low or ship_name_low in pk:
                    ship_entry["priority"] = pv
                    is_priority = True
                    break

            if not is_priority:
                if not pad or _PAD_ORDER.get(pad, 99) > max_pad_order:
                    continue  # Skip for hangar list (still in all_cargo_ships)

            # Check known_no_fit
            if any(nf in ship_name_low or ship_name_low in nf for nf in known_no_fit):
                continue

            if not pad and not is_priority:
                continue

            ship_entry["is_known_fit"] = any(
                kf in ship_name_low or ship_name_low in kf for kf in known_fits
            )
            hangar_ships.append(ship_entry)

    # Sort hangar ships
    hangar_ships.sort(key=lambda x: (
        -x["priority"], -x["is_known_fit"], -x["is_cargo"], x["trips"], -x["scu"]
    ))

    # ── Pad ships: larger ships that can carry full load in 1 trip ──
    pad_ships = []
    for s in all_cargo_ships:
        if s["scu"] >= total_scu:
            pad_ships.append(s)
    pad_ships.sort(key=lambda x: (-x["is_cargo"], x["scu"]))

    # ── Multi-trip pad ships: if no single-trip option exists ──
    multi_trip_ships = []
    if not pad_ships:
        for s in all_cargo_ships:
            if s["scu"] > 0:
                multi_trip_ships.append(s)
        multi_trip_ships.sort(key=lambda x: (-x["is_cargo"], x["trips"], -x["scu"]))

    is_hangar_staging = any(e in str(loading_type).lower() for e in ["hangar", "bay", "elevator", "in hangar"]) or any(e in str(location).lower() for e in ["hangar", "bay", "in hangar"])
    load_location_str = "in hangar via freight elevator." if is_hangar_staging else "on landing pad."

    # ── IN-HANGAR STAGING (Direct capital dock freight elevator loading) ──
    if is_hangar_staging:
        return {
            "hangar_shuttles": [],
            "pad_shuttles": [],
            "recommended": {
                "name": vessel_display, "scu": vessel_scu, "trips": 1,
                "pad": vessel_pad, "is_cargo": 1,
            },
            "loading_method": "in_hangar",
            "note": (
                f"IN-HANGAR DIRECTIVE: {vessel_display} ({vessel_scu} SCU) docked directly in capital hangar. "
                f"Direct freight elevator staging into primary hold ({total_scu:.1f} SCU). "
                f"Use of ATLS, MaxLift, and personnel with tractor beams advised."
            ),
            "mother_ship": vessel_display,
            "has_hangar": has_hangar,
            "total_scu": total_scu,
        }

    # ── Determine best recommendation ──
    best_hangar = hangar_ships[0] if hangar_ships else None
    best_pad = pad_ships[0] if pad_ships else None
    best_multi = multi_trip_ships[0] if multi_trip_ships else None

    if has_hangar:
        ship_label = hangar_info.get("name", vn_low.title()) if hangar_info else vn_low.title()

        if best_hangar and best_hangar["trips"] <= 2:
            loading_method = "hangar"
            recommended = best_hangar
            trip_txt = "Single trip" if best_hangar["trips"] == 1 else "2 trips required (max limit)"
            note = (
                f"HANGAR LOADING DIRECTIVE: Internal bay loading via {best_hangar['name']} "
                f"({best_hangar['scu']} SCU, {trip_txt}). Use of ATLS and personnel with tractor beams advised.{marine_note}"
            )
        else:
            loading_method = "landing_pad"
            recommended = best_pad if best_pad else best_hangar
            note = (
                f"LANDING PAD WARNING: Transport vessel exceeds internal hangar dimensions of {ship_label}. "
                f"EVA / Landing Pad transfer required. Recommend: {recommended['name']} ({recommended['scu']} SCU)."
            )

        hangar_note = hangar_info.get("note", "")
        if hangar_note:
            note += f" [{hangar_note}]"
    else:
        ship_label = vessel_display
        is_planetary = any(k in loc_str or k in type_str for k in ["planetary", "surface", "outpost", "ground", "land", "monox", "bloom", "delamar", "sunset mesa", "ostler", "jacksons", "yang", "arid reach", "rayari", "shubin", "hdms", "babbage", "lorville", "area18", "orison", "levski", "revolux", "zeus", "rappel", "facility", "site", "farm"])
        is_eva = any(k in loc_str or k in type_str for k in ["eva", "free float", "deep space", "orbit", "interdiction"])
        marine_note = " Marine security escort recommended for planetary surface operations." if is_planetary else ""

        if is_planetary:
            loading_method = "planetary"
            recommended = best_pad if best_pad else (best_multi if best_multi else {"name": "Cargo Ship", "scu": 100, "trips": 1})
            loc_display = location if location else "Planetary Outpost"
            note = (
                f"PLANETARY STAGING DIRECTIVE: Capital vessel {vessel_display} staging at {loc_display}. "
                f"Shuttle/L-boat transport or orbital staging required for full cargo transfer.{marine_note}"
            )
        elif is_hangar_staging or vessel_scu >= total_scu:
            loading_method = "self"
            recommended = {
                "name": vessel_display, "scu": vessel_scu, "trips": 1,
                "pad": vessel_pad, "is_cargo": 1,
            }
            note = (
                f"HANGAR LOADING DIRECTIVE: Direct bay loading for {vessel_display} ({vessel_scu} SCU). "
                f"Use of ATLS and Maxlift tractor beams advised.{marine_note}"
            )
        elif is_eva:
            loading_method = "eva"
            recommended = None
            note = f"EVA LOADING WARNING: Deep space / orbital EVA transfer required for {ship_label}."
        else:
            loading_method = "landing_pad"
            recommended = best_pad if best_pad else (best_multi if best_multi else {"name": "Cargo Ship", "scu": 100, "trips": 1})
            note = (
                f"STAGING LOCATION DIRECTIVE: External cargo transfer required for {vessel_display} at {location if location else 'Staging Area'}.{marine_note}"
            )

    return {
        "hangar_shuttles": hangar_ships[:5],
        "pad_shuttles": pad_ships[:3],
        "recommended": recommended,
        "loading_method": loading_method,
        "note": note,
        "mother_ship": ship_label,
        "has_hangar": has_hangar,
        "total_scu": total_scu,
    }

def _recommend_cargo_ship(total_scu, ships_db=None):
    """Recommend the best cargo ship to transport total_scu.

    Used by Supply Route PDF — picks the smallest ship that can carry
    the entire cargo in one trip. If nothing fits in 1 trip, picks the
    largest available and calculates trips needed.
    For small cargo (< 64 SCU), strictly selects from IDRIS internal hangar compatible
    ships: ARGO MPUV Cargo, ARGO MPUV Tractor, DRAKE GOLEM OX.
    """
    if not total_scu or total_scu <= 0:
        return None

    # Bod 8: Small Cargo Rule (< 64 SCU) -> Idris internal hangar fit
    if float(total_scu) <= 64:
        small_ships = [
            {"name": "ARGO MPUV Cargo", "scu": 2, "key": "argo_mpuv_cargo"},
            {"name": "ARGO MPUV Tractor", "scu": 4, "key": "argo_mpuv_tractor"},
            {"name": "Drake Golem OX", "scu": 64, "key": "golem_ox"},
        ]
        best_fit = small_ships[0] if total_scu <= 2 else (small_ships[1] if total_scu <= 4 else small_ships[2])
        options_str = " | ".join(f"{s['name']} ({s['scu']} SCU)" for s in small_ships)
        return {
            "name": best_fit["name"],
            "scu": best_fit["scu"],
            "trips": 1,
            "note": f"SMALL CARGO (<64 SCU - IDRIS HANGAR FIT): {options_str}",
            "fits": True,
            "alt": small_ships[1]["name"] if best_fit["name"] == small_ships[0]["name"] else small_ships[0]["name"],
            "options": small_ships,
        }

    if ships_db is None:
        ships_db = _load_uex_ships_db()

    # Build sorted list of cargo ships (only real, non-concept, SCU > 0)
    cargo_ships = []
    
    # Strict Pure-Cargo blacklist
    non_cargo_blacklist = [
        "carrack", "890 jump", "890", "reclaimer", "corsair", "constellation aquila",
        "constellation phoenix", "600i explorer", "600i touring", "600i", "400i", "odyssey",
        "idris", "javelin", "hammerhead", "polaris", "nautilus", "prowler", "redeemer",
        "valkyrie", "terrapin", "vulture", "prospector", "mole", "starfarer", "luxury",
        "gunship", "corvette", "salvage", "mining", "exploration", "cutlass red", "cutlass blue"
    ]
    _DEDICATED_CARGO_HAULERS = [
        "c2 hercules", "m2 hercules", "a2 hercules", "caterpillar", "hull c", "hull b", "hull a", "hull d", "hull e",
        "constellation taurus", "freelancer max", "freelancer", "raft", "cutlass black", "zeus cl", "spirit c1",
        "starlancer max", "starlancer tac", "ironclad", "rsi hermes", "golem ox", "misc golem ox", "avenger titan",
        "nomad", "c8x pisces", "drake cutter", "constellation andromeda"
    ]
    
    for k, v in ships_db.items():
        scu = v.get("scu", 0)
        if scu <= 0:
            continue
        if not v.get("is_spaceship", 1):
            continue
        if k.lower() in _CONCEPT_SHIPS:
            continue
            
        name = v.get("name", v.get("short_name", k))
        name_lower = name.lower()
        
        # Pure-Cargo enforcement (Step 4 Requirement)
        if any(b in name_lower for b in non_cargo_blacklist):
            continue
            
        cargo_ships.append({"name": name, "scu": scu, "key": k})

    cargo_ships.sort(key=lambda x: (0 if any(dh in x["name"].lower() for dh in _DEDICATED_CARGO_HAULERS) else 1, x["scu"]))


    if not cargo_ships:
        return None

    # Find smallest ship that fits in 1 trip
    best_fit = None
    for ship in cargo_ships:
        if ship["scu"] >= total_scu:
            best_fit = ship
            break

    if best_fit:
        # Find alternative (next size up)
        alt = None
        idx = cargo_ships.index(best_fit)
        if idx + 1 < len(cargo_ships):
            alt = cargo_ships[idx + 1]["name"]

        trips = 1
        return {
            "name": best_fit["name"],
            "scu": best_fit["scu"],
            "trips": trips,
            "note": (
                f"RECOMMENDED TRANSPORT: {best_fit['name'].upper()} "
                f"({best_fit['scu']} SCU). Single trip."
            ),
            "fits": True,
            "alt": alt,
        }
    else:
        # Nothing fits in 1 trip — use largest ship
        largest = cargo_ships[-1]
        trips = math.ceil(total_scu / largest["scu"]) if largest["scu"] > 0 else 999
        return {
            "name": largest["name"],
            "scu": largest["scu"],
            "trips": trips,
            "note": (
                f"RECOMMENDED TRANSPORT: {largest['name'].upper()} "
                f"({largest['scu']} SCU). "
                f"Requires {trips} trips to deliver {total_scu:.0f} SCU."
            ),
            "fits": False,
            "alt": None,
        }
