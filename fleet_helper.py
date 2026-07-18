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

    # ── SELF-LOAD: ship itself can carry the cargo ──
    if vessel_scu >= total_scu and not has_hangar:
        return {
            "hangar_shuttles": [],
            "pad_shuttles": [],
            "recommended": {
                "name": vessel_display, "scu": vessel_scu, "trips": 1,
                "pad": vessel_pad, "is_cargo": 1,
            },
            "loading_method": "self",
            "note": (
                f"SELF-LOAD: {vessel_display} has {vessel_scu} SCU capacity. "
                f"Load {total_scu} SCU directly at trade terminal or landing pad."
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

        # Track ALL cargo ships for pad/EVA recommendations
        if scu > 0 and pad:
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

    # ── Determine best recommendation ──
    best_hangar = hangar_ships[0] if hangar_ships else None
    best_pad = pad_ships[0] if pad_ships else None
    best_multi = multi_trip_ships[0] if multi_trip_ships else None

    if has_hangar:
        ship_label = hangar_info["name"]

        if best_hangar and best_hangar["trips"] <= 2:
            loading_method = "hangar"
            recommended = best_hangar
            trip_txt = "Single trip" if best_hangar["trips"] == 1 else "2 trips required"
            note = (
                f"SHUTTLE RECOMMENDATION: Use {best_hangar['name']} "
                f"({best_hangar['scu']} SCU, pad {best_hangar['pad']}). "
                f"{trip_txt} via {ship_label} internal hangar.{concept_note}"
            )
        elif best_hangar and best_hangar["trips"] > 2:
            loading_method = "landing_pad"
            recommended = best_pad if best_pad else best_hangar
            pad_opt = (
                f"Alt: {best_pad['name']} ({best_pad['scu']} SCU) on landing pad. "
                if best_pad else ""
            )
            note = (
                f"⚠️ CARGO VOLUME HIGH ({best_hangar['trips']} trips via "
                f"{best_hangar['name']}). Consider landing pad loading. {pad_opt}{concept_note}"
            )
        elif best_pad:
            loading_method = "landing_pad"
            recommended = best_pad
            note = (
                f"NO CARGO SHUTTLE FITS IN {ship_label.upper()} HANGAR. "
                f"Use {best_pad['name']} ({best_pad['scu']} SCU) via landing pad.{concept_note}"
            )
        else:
            loading_method = "eva"
            recommended = best_multi
            note = (
                f"NO SHUTTLE AVAILABLE for {total_scu} SCU in {ship_label}. "
                f"EVA manual transfer required.{concept_note}"
            )

        hangar_note = hangar_info.get("note", "")
        if hangar_note:
            note += f" [{hangar_note}]"
    else:
        # ── Non-carrier ship: landing pad or EVA ──
        ship_label = vessel_display
        if best_pad:
            loading_method = "landing_pad"
            recommended = best_pad
            note = (
                f"TRANSFER: Use {best_pad['name']} ({best_pad['scu']} SCU, "
                f"pad {best_pad['pad']}) to ferry cargo to {ship_label}."
            )
        elif best_multi:
            loading_method = "landing_pad"
            recommended = best_multi
            note = (
                f"TRANSFER: Use {best_multi['name']} ({best_multi['scu']} SCU), "
                f"{best_multi['trips']} trips to load {ship_label}."
            )
        elif vessel_scu > 0:
            loading_method = "self"
            recommended = {
                "name": vessel_display, "scu": vessel_scu,
                "trips": max(1, -(-total_scu // vessel_scu)),
                "pad": vessel_pad, "is_cargo": 1,
            }
            note = (
                f"SELF-LOAD: {vessel_display} ({vessel_scu} SCU). "
                f"Multiple trade terminal runs needed for {total_scu} SCU."
            )
        else:
            loading_method = "eva"
            recommended = None
            note = f"MANUAL LOAD: EVA cargo transfer required for {ship_label}."

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

    Returns dict:
        name: ship display name
        scu: ship's cargo capacity
        trips: number of trips required
        note: human-readable text for PDF
        fits: bool — True if 1 trip, False if multiple
        alt: alternative ship name (larger) or None
    """
    if not total_scu or total_scu <= 0:
        return None

    if ships_db is None:
        ships_db = _load_uex_ships_db()

    # Build sorted list of cargo ships (only real, non-concept, SCU > 0)
    cargo_ships = []
    for k, v in ships_db.items():
        scu = v.get("scu", 0)
        if scu <= 0:
            continue
        if not v.get("is_spaceship", 1):
            continue
        if k.lower() in _CONCEPT_SHIPS:
            continue
        name = v.get("name", v.get("short_name", k))
        cargo_ships.append({"name": name, "scu": scu, "key": k})

    cargo_ships.sort(key=lambda x: x["scu"])

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
