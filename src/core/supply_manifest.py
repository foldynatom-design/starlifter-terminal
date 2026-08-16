# -*- coding: utf-8 -*-
"""
supply_manifest.py - Requisition codes, Stop indexing & Route Optimizer
"""
import random
import re as _re
import uex_sync as _uex

# QT distances imported from sc_wiki_db — single source of truth.
# To update travel times after a game patch, edit sc_wiki_db.STANTON_PLANET_DISTANCES
# and sc_wiki_db.SYSTEM_DISTANCES only.
from sc_wiki_db import STANTON_PLANET_DISTANCES as _STANTON_QT_MINS, SYSTEM_DISTANCES as _SYSTEM_JUMP_PENALTY_RAW

# Remap system-jump penalties to match our (sys_a, sys_b) sorted-tuple key format
_SYSTEM_JUMP_PENALTY = {}
for (_a, _b), _v in _SYSTEM_JUMP_PENALTY_RAW.items():
    _SYSTEM_JUMP_PENALTY[tuple(sorted([_a, _b]))] = _v


def generate_requisition_code():
    """Generate a pseudo-random logistics requisition code."""
    prefixes = ["REQ", "SEC", "LOG", "TAC", "NAV"]
    divisions = ["44BG", "UEE-9N", "FLEET-44", "TAC-DIV"]
    suffixes = ["ALPHA", "BRAVO", "X-RAY", "OMEGA", "DELTA-6"]
    return f"{random.choice(prefixes)}-{random.choice(divisions)}-{random.randint(10000, 99999)}-{random.choice(suffixes)}"

def _guess_planet(loc_name):
    loc_name = loc_name.lower()
    if 'arc' in loc_name or 'area' in loc_name or 'lyria' in loc_name or 'wala' in loc_name: return 'arccorp'
    if 'cru' in loc_name or 'orison' in loc_name or 'yela' in loc_name or 'cellin' in loc_name or 'daymar' in loc_name: return 'crusader'
    if 'hur' in loc_name or 'lorville' in loc_name or 'aberdeen' in loc_name or 'arial' in loc_name or 'ita' in loc_name or 'magda' in loc_name: return 'hurston'
    if 'mic' in loc_name or 'babbage' in loc_name or 'calliope' in loc_name or 'clio' in loc_name or 'euterpe' in loc_name: return 'microtech'
    return ""

def _guess_system(default_sys, loc_name):
    loc_name = loc_name.lower()
    if 'pyro' in loc_name or 'checkmate' in loc_name or 'ruin' in loc_name or 'monox' in loc_name: return 'pyro'
    if 'nyx' in loc_name or 'levski' in loc_name or 'delamar' in loc_name: return 'nyx'
    return default_sys

def _get_terminal_info(terminal_name):
    """Get (system, planet) for a terminal name from locations DB."""
    tn = terminal_name.lower()
    pla = _guess_planet(tn)
    sys = _guess_system("stanton", tn)
    if pla or sys != "stanton":
        return sys, pla
        
    _uex_locations_db = _uex._uex_locations_db or {}
    for cat_locs in _uex_locations_db.values():
        if isinstance(cat_locs, dict):
            for loc_name, loc_info in cat_locs.items():
                if loc_name.lower() in tn or tn in loc_name.lower():
                    sys = (loc_info.get("system") or "stanton").lower()
                    pla = (loc_info.get("planet") or "").lower()
                    return sys, pla
    return "stanton", ""

def get_qt_distance(loading_system, loading_planet, terminal_name):
    """Estimated QT travel time in minutes from loading location. Lower = closer."""
    t_sys, t_pla = _get_terminal_info(terminal_name)
    
    # Cross-system jump penalty
    if t_sys != loading_system:
        pair = tuple(sorted([loading_system, t_sys]))
        penalty = _SYSTEM_JUMP_PENALTY.get(pair, 100)
        return penalty
    
    # Same system
    if not t_pla or not loading_planet:
        return 10
    if t_pla == loading_planet:
        return 2
    
    pair = tuple(sorted([loading_planet, t_pla]))
    return _STANTON_QT_MINS.get(pair, 12)

def enrich_location(terminal_name):
    """Format location strictly as 'SYSTEM -> LOCATION -> DECK/ZONE -> SHOP NAME'."""
    if not terminal_name or "stanton cargo terminal" in str(terminal_name).lower():
        return "STANTON -> HURSTON -> LORVILLE -> CARGO CENTER TERMINAL"
    tn = str(terminal_name).strip()
    tn_low = tn.lower()

    # If already contains delimiters, split and deduplicate repeated segments
    if "->" in tn or " > " in tn:
        parts = [p.strip() for p in tn.replace("->", ">").split(">") if p.strip()]
        clean_parts = []
        for p in parts:
            if not clean_parts or p.upper() != clean_parts[-1].upper():
                clean_parts.append(p)
        
        sys_name = "STANTON"
        for p in clean_parts:
            pl = p.lower()
            if any(k in pl for k in ["pyro", "monox", "bloom", "checkmate", "ruin", "starlight", "patchcity"]):
                sys_name = "PYRO"
            elif any(k in pl for k in ["nyx", "levski", "delamar", "glaciem", "gold horizon", "kepler", "pssa"]):
                sys_name = "NYX"

        filtered = [p.upper() for p in clean_parts if p.upper() not in ["STANTON", "PYRO", "NYX"]]
        if not filtered:
            return f"{sys_name} -> TERMINAL"
        if len(filtered) >= 3:
            return f"{sys_name} -> {' -> '.join(filtered[-3:])}"
        elif len(filtered) == 2:
            return f"{sys_name} -> {filtered[0]} -> {filtered[1]}"
        else:
            return f"{sys_name} -> {filtered[0]}"

    # Determine System
    if any(k in tn_low for k in ["pyro", "checkmate", "ruin", "monox", "bloom", "patchcity", "starlight"]):
        system = "PYRO"
    elif any(k in tn_low for k in ["nyx", "levski", "delamar", "glaciem", "keeger", "porphyr", "vanguard", "gold horizon", "kepler", "nyx-l", "pssa", "psst", "pssl", "pssd", "pssk"]):
        system = "NYX"
    else:
        system = "STANTON"

    # Determine Deck / Zone
    deck = None
    refinery_keywords = ["refinery", "ore", "mining", "smelter", "processing", "unrefined"]
    if any(k in tn_low for k in refinery_keywords):
        deck = "REFINERY DECK"

    cargo_keywords = ["cargo center", "cargo deck", "freight", "covalex", "cargo terminal", "commodity", "warehouse", "storage container", "stor-all", "greycat logistics"]
    if not deck and any(k in tn_low for k in cargo_keywords):
        deck = "CARGO DECK"

    galleria_keywords = [
        "galleria", "gallery", "platinum bay", "platinum", "garrity", "casaba", "cubby", "dumper", "centermass", "center mass",
        "shubin", "tammany", "skutters", "kel-to", "pawn", "weapon", "armor", "clothing", "bar", "food", "drink",
        "burrito", "whistle", "pizza", "noodle", "pharmacy", "ez hab", "hab", "admin", "clinic", "hospital", "apothecary"
    ]
    if not deck and any(k in tn_low for k in galleria_keywords):
        deck = "GALLERIA"

    # Determine Base Station / Landing Zone
    station = None
    if "everus" in tn_low:
        station = "EVERUS HARBOR"
        deck = deck or "GALLERIA"
    elif "tressler" in tn_low:
        station = "PORT TRESSLER"
        deck = deck or "GALLERIA"
    elif "baijini" in tn_low:
        station = "BAIJINI POINT"
        deck = deck or "GALLERIA"
    elif "seraphim" in tn_low:
        station = "SERAPHIM STATION"
        deck = deck or "GALLERIA"
    elif "area18" in tn_low or "area 18" in tn_low:
        return f"STANTON -> ARCCORP -> AREA18 -> {tn.upper()}"
    elif "babbage" in tn_low or "new babbage" in tn_low:
        if "tressler" not in tn_low and "mic-l" not in tn_low:
            return f"STANTON -> MICROTECH -> NEW BABBAGE -> {tn.upper()}"
    elif "lorville" in tn_low:
        if "everus" not in tn_low and "hur-l" not in tn_low:
            return f"STANTON -> HURSTON -> LORVILLE -> {tn.upper()}"
    elif "orison" in tn_low:
        if "seraphim" not in tn_low and "cru-l" not in tn_low:
            return f"STANTON -> CRUSADER -> ORISON -> {tn.upper()}"
    elif "checkmate" in tn_low:
        return f"PYRO -> CHECKMATE STATION -> {deck or 'HANGARS HAB'} -> {tn.upper()}"
    elif "sunset mesa" in tn_low:
        return f"PYRO -> MONOX -> SUNSET MESA OUTPOST -> {tn.upper()}"
    elif "gaslight" in tn_low:
        return f"PYRO -> MONOX -> GASLIGHT OUTPOST -> {tn.upper()}"
    elif "monox" in tn_low:
        return f"PYRO -> MONOX -> OUTPOST VENDOR -> {tn.upper()}"
    elif "orinth" in tn_low:
        return f"STANTON -> HURSTON -> ORINTH SCRAP YARD -> {tn.upper()}"
    elif "gold horizon" in tn_low:
        return f"NYX -> GLACIEM RING -> GOLD HORIZON STATION -> {tn.upper()}"
    elif "kepler" in tn_low:
        return f"NYX -> GLACIEM -> KEPLER STATION -> {tn.upper()}"
    elif "station alpha" in tn_low or "pssa" in tn_low:
        return f"NYX -> PHARKAS RING -> STATION ALPHA (PSSA) -> {tn.upper()}"
    elif "station delta" in tn_low or "pssd" in tn_low:
        return f"NYX -> PHARKAS RING -> STATION DELTA (PSSD) -> {tn.upper()}"
    elif "station theta" in tn_low or "psst" in tn_low:
        return f"NYX -> PHARKAS RING -> STATION THETA (PSST) -> {tn.upper()}"
    elif "station lambda" in tn_low or "pssl" in tn_low:
        return f"NYX -> PHARKAS RING -> STATION LAMBDA (PSSL) -> {tn.upper()}"
    elif "station kappa" in tn_low or "pssk" in tn_low:
        return f"NYX -> PHARKAS RING -> STATION KAPPA (PSSK) -> {tn.upper()}"
    elif "levski" in tn_low or "delamar" in tn_low:
        return f"NYX -> DELAMAR -> LEVSKI HUB -> {tn.upper()}"

    # Station L-points (HUR-L1..5, ARC-L1..5, MIC-L1..5, CRU-L1..5, NYX-L1..5)
    for pfx in ["hur-l", "arc-l", "mic-l", "cru-l", "nyx-l"]:
        if pfx in tn_low:
            for num in ["1", "2", "3", "4", "5"]:
                lp = f"{pfx}{num}"
                if lp in tn_low:
                    station = lp.upper()
                    deck = deck or ("CARGO DECK" if "cargo" in tn_low else ("REFINERY DECK" if "refiner" in tn_low or "ore" in tn_low else "GALLERIA"))
                    return f"{system} -> {station} -> {deck} -> {tn.upper()}"

    if station:
        return f"{system} -> {station} -> {deck} -> {tn.upper()}"

    return f"{system} -> {tn.upper()}"

def build_procurement_route(items, loading_loc, has_loose_items=False):
    """
    Given a list of items and a loading location, returns a structured procurement route
    and a location-sorted summary.
    """
    from sc_wiki_db import get_best_buy_location
    
    loading_loc_low = loading_loc.lower()
    loading_planet = _guess_planet(loading_loc_low)
    loading_system = _guess_system("stanton", loading_loc_low)
    
    if not loading_planet:
        _uex_locations_db = _uex._uex_locations_db or {}
        for cat_locs in _uex_locations_db.values():
            if isinstance(cat_locs, dict):
                for loc_name, loc_info in cat_locs.items():
                    if loc_name.lower() in loading_loc_low or loading_loc_low in loc_name.lower():
                        loading_planet = (loc_info.get("planet") or "").lower()
                        loading_system = (loc_info.get("system") or "stanton").lower()
                        break
            if loading_planet:
                break
                
    procurement = []
    
    _uex_trade_db_local = _uex._uex_trade_db or {}
    _uex_items_trade_db_local = _uex._uex_items_trade_db or {}
    
    for item in items:
        iname = item['name']
        iname_low = iname.lower().strip()
        best_loc = None
        best_price = item.get('price', None)
        
        # Skip Stor-All boxes (auto-added)
        if 'stor' in iname_low and ('all' in iname_low or 'storage' in iname_low):
            has_loose_items = True
            continue
        
        from slang_helper import resolve_slang
        canonical_name = resolve_slang(iname)
        canon_low = canonical_name.lower().strip()

        # 1. Dynamic Database Lookup across ALL star systems (Item -> Shop -> Location -> System)
        try:
            from sc_wiki_db import get_best_buy_location
            wiki_res = get_best_buy_location(canonical_name, from_location=loading_loc, from_system=loading_system)
            if wiki_res:
                best_loc = wiki_res.get("full_buy_path") or wiki_res.get("display") or wiki_res.get("terminal")
                if not best_price or best_price == 0:
                    best_price = wiki_res.get("price", 0)
        except Exception:
            pass

        # 2. Fast local DB lookup
        if not best_loc:
            candidates = []
            if _uex_trade_db_local:
                for db_name, entries in _uex_trade_db_local.items():
                    db_low = db_name.lower().strip()
                    if db_low == iname_low or db_low == canon_low:
                        for e in entries:
                            if isinstance(e, dict) and e.get('buy', e.get('b', 0)) > 0:
                                loc = e.get('terminal', e.get('t', 'UNKNOWN'))
                                price = e.get('buy', e.get('b', 0))
                                is_onsite = loading_loc_low and (loading_loc_low in loc.lower() or loc.lower() in loading_loc_low)
                                dist = -100 if is_onsite else get_qt_distance(loading_system, loading_planet, loc)
                                candidates.append((dist, price, loc))
                        break
            
            if not candidates and _uex_items_trade_db_local:
                for db_name, entries in _uex_items_trade_db_local.items():
                    db_low = db_name.lower().strip()
                    if db_low == iname_low or db_low == canon_low:
                        locs = entries.get('locations', []) if isinstance(entries, dict) else (entries if isinstance(entries, list) else [])
                        for e in locs:
                            if isinstance(e, dict) and e.get('buy', e.get('b', 0)) > 0:
                                loc = e.get('terminal', e.get('t', 'UNKNOWN'))
                                price = e.get('buy', e.get('b', 0))
                                is_onsite = loading_loc_low and (loading_loc_low in loc.lower() or loc.lower() in loading_loc_low)
                                dist = -100 if is_onsite else get_qt_distance(loading_system, loading_planet, loc)
                                candidates.append((dist, price, loc))
                        break
            
            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1]))
                same_sys = [c for c in candidates if c[0] < 50]
                if same_sys:
                    candidates = same_sys
                best_loc = candidates[0][2]
                if not best_price or best_price == 0:
                    best_price = candidates[0][1]

        # 3. Strict Verification & Crafting Fallback (Resolve Blueprint & Ores vs Unobtainable/Loot)
        is_craftable = False
        is_unobtainable = False
        is_raw_mineral = False
        craft_info = None

        if not best_loc:
            # Check if item is raw/unrefined mineral or specific quality ore (user RP directive)
            is_raw_mineral = any(k in iname_low for k in ["unrefined", "raw ore", "raw quantainium", "mined ore", "unprocessed", "deposit", "raw mineral", "pure ore"]) or (bool(_re.search(r'\b(ore|ores)\b', iname_low)) and "pod" not in iname_low and "refined" not in iname_low)
            if is_raw_mineral:
                best_loc = "FIELD LOGISTICS DIRECTIVE // CONTACT MINING OPERATOR"
                display_loc = best_loc
                qt = 10
            else:
                try:
                    from src.core.crafting_helper import resolve_unbuyable_item
                    craft_info = resolve_unbuyable_item(canonical_name, qty=item.get('qty', 1))
                    if craft_info.get("can_craft"):
                        is_craftable = True
                        best_loc = "FABRICATION / CRAFTING"
                        display_loc = craft_info.get("display_directive")
                        qt = 0
                    else:
                        is_unobtainable = True
                        best_loc = "FIELD RECOVERY / LOOT"
                        display_loc = "UNOBTAINABLE // NEEDS TO BE LOOTED (No vendor terminal & no blueprint available)"
                        qt = 99
                except Exception:
                    is_unobtainable = True
                    best_loc = "FIELD RECOVERY / LOOT"
                    display_loc = "UNOBTAINABLE // NEEDS TO BE LOOTED (No vendor terminal & no blueprint available)"
                    qt = 99

        if not (is_craftable or is_unobtainable or is_raw_mineral):
            # Use enriched location for trade-DB results, plain string for vendor fallback
            if best_loc and '(' not in str(best_loc):
                display_loc = enrich_location(best_loc)
                qt = get_qt_distance(loading_system, loading_planet, best_loc)
            elif best_loc:
                display_loc = best_loc
                qt = 5  # vendor fallback = close
            else:
                display_loc = "STANTON -> REQUISITION TERMINAL"
                qt = 99

        procurement.append({
            'name': iname, 'qty': item['qty'],
            'loc': display_loc,
            'price': best_price,
            'raw_loc': best_loc or '',
            'qt_min': qt,
            'is_craftable': is_craftable,
            'is_unobtainable': is_unobtainable,
            'craft_info': craft_info,
        })

    # ── Group by base location (station/planet) to prevent A→B→A ping-pong ──
    def _normalize_base_loc(loc_str):
        """Collapse shops/outposts at the same station/planet into one base key."""
        if not loc_str:
            return ""
        s = str(loc_str).strip()
        s_low = s.lower()

        # Determine system prefix
        if any(k in s_low for k in ["pyro", "monox", "bloom", "checkmate", "orbituary", "ruin", "starlight", "patchcity", "sunset mesa", "gaslight", "jackson", "yang", "ostler", "arid reach"]):
            sys_pfx = "Pyro"
        elif any(k in s_low for k in ["nyx", "levski", "glaciem", "delamar", "porphyr", "vanguard", "gold horizon", "kepler", "nyx-l", "pssa", "psst", "pssl", "pssd", "pssk"]):
            sys_pfx = "Nyx"
        else:
            sys_pfx = "Stanton"

        # Determine main location (station / landing zone / planet)
        if any(k in s_low for k in ["tressler", "platinum tressler"]):
            main = "Port Tressler"
        elif any(k in s_low for k in ["babbage", "microtech", "dunboro", "rayari", "calliope", "clio", "euterpe", "calhoun"]):
            main = "microTech"
        elif any(k in s_low for k in ["everus"]):
            main = "Everus Harbor"
        elif any(k in s_low for k in ["baijini"]):
            main = "Baijini Point"
        elif any(k in s_low for k in ["seraphim"]):
            main = "Seraphim Station"
        elif any(k in s_low for k in ["area18", "area 18", "arccorp", "cubby blast", "centermass", "g-loc", "wala", "lyria"]):
            main = "Area18"
        elif any(k in s_low for k in ["lorville", "hurston", "hdms", "arial", "ita", "magda", "aberdeen", "tammany"]):
            main = "Hurston"
        elif any(k in s_low for k in ["orison", "crusader", "yela", "daymar", "cellin", "brio", "wally"]):
            main = "Crusader"
        elif any(k in s_low for k in ["gold horizon"]):
            main = "Gold Horizon Station"
        elif any(k in s_low for k in ["kepler"]):
            main = "Kepler Station"
        elif any(k in s_low for k in ["levski", "delamar"]):
            main = "Levski"
        elif any(k in s_low for k in ["checkmate"]):
            main = "Checkmate Station"
        elif any(k in s_low for k in ["sunset mesa", "gaslight", "monox"]):
            main = "Monox"
        elif "hur-l" in s_low:
            for lp in ["hur-l1", "hur-l2", "hur-l3", "hur-l4", "hur-l5"]:
                if lp in s_low:
                    main = lp.upper()
                    break
            else:
                main = "HUR-L"
        elif "arc-l" in s_low:
            for lp in ["arc-l1", "arc-l2", "arc-l3", "arc-l4", "arc-l5"]:
                if lp in s_low:
                    main = lp.upper()
                    break
            else:
                main = "ARC-L"
        elif "cru-l" in s_low:
            for lp in ["cru-l1", "cru-l2", "cru-l3", "cru-l4", "cru-l5"]:
                if lp in s_low:
                    main = lp.upper()
                    break
            else:
                main = "CRU-L"
        elif "mic-l" in s_low:
            for lp in ["mic-l1", "mic-l2", "mic-l3", "mic-l4", "mic-l5"]:
                if lp in s_low:
                    main = lp.upper()
                    break
            else:
                main = "MIC-L"
        elif "nyx-l" in s_low:
            for lp in ["nyx-l1", "nyx-l2", "nyx-l3", "nyx-l4", "nyx-l5"]:
                if lp in s_low:
                    main = lp.upper()
                    break
            else:
                main = "NYX-L"
        else:
            parts = [p.strip() for p in s.split(' > ')] if ' > ' in s else (
                     [p.strip() for p in s.split(' -> ')] if ' -> ' in s else [s])
            main = parts[1] if len(parts) >= 2 else parts[0]

        main = _re.sub(r'\s*\([^)]*\)', '', main).strip()
        return f"{sys_pfx} > {main}"

    # Group buyable items by normalized base location (craftable and unobtainable items are handled via directives)
    base_groups = {}   # base_key -> list of procurement dicts
    buyable_procurement = [p for p in procurement if not p.get('is_craftable') and not p.get('is_unobtainable')]
    for p in buyable_procurement:
        base_key = _normalize_base_loc(p['loc']) or _normalize_base_loc(p.get('raw_loc', ''))
        base_groups.setdefault(base_key, []).append(p)

    # Sort base groups strictly by System priority first, then QT distance, then item count
    def _base_sort_key(pair):
        base_key, items_list = pair
        raw = items_list[0].get('raw_loc', '') or items_list[0].get('loc', '')
        
        sys_name = "stanton"
        bk_low = base_key.lower()
        if "pyro" in bk_low or any(k in bk_low for k in ["monox", "bloom", "checkmate", "ruin"]):
            sys_name = "pyro"
        elif "nyx" in bk_low or "levski" in bk_low:
            sys_name = "nyx"
            
        load_sys = str(loading_system or "stanton").lower()
        sys_prio = 0 if sys_name == load_sys else (1 if sys_name == "stanton" else (2 if sys_name == "pyro" else 3))
        
        qt = get_qt_distance(loading_system, loading_planet, raw)
        return (sys_prio, qt, -len(items_list))

    sorted_bases = sorted(base_groups.items(), key=_base_sort_key)

    # Within each base group, sub-group by specific shop/loc for display
    sorted_locs = []
    for _base_key, base_items in sorted_bases:
        shop_pairs = [(p['loc'], p) for p in base_items]
        sorted_locs.append((_base_key, shop_pairs))

    return procurement, sorted_locs, has_loose_items
