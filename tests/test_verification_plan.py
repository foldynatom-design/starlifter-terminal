# -*- coding: utf-8 -*-
"""
test_verification_plan.py — Automated test suite for logistics data validation.

Tests:
1. Aril Core returns a location containing "Providence Surplus" or "Orison".
2. No item in frequent_items.json has category "Commodities" if it is armor or clothing.
3. Procurement chain never generates the non-existent location "Stanton Cargo Terminal".
4. Items from Pyro system do not get assigned Stanton locations and vice versa.
"""
import os
import sys
import json
import unittest

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from path_config import PATHS
from sc_wiki_db import get_best_buy_location, lookup_item
from src.core.supply_manifest import build_procurement_route, enrich_location


class TestVerificationPlan(unittest.TestCase):

    def test_01_aril_core_location(self):
        """Test that Aril Core returns a location containing 'Providence Surplus' or 'Orison'."""
        loc = get_best_buy_location("Aril Core", from_location="Orison", from_system="stanton")
        self.assertIsNotNone(loc, "Aril Core location lookup returned None!")
        
        full_path = loc.get("full_buy_path", "") or loc.get("display", "") or loc.get("terminal", "")
        print(f"[TEST 1] Aril Core location: {full_path}")
        
        has_match = ("Providence Surplus" in full_path or "Orison" in full_path)
        self.assertTrue(has_match, f"Aril Core location '{full_path}' does not contain 'Providence Surplus' or 'Orison'")

    def test_02_armor_not_commodities(self):
        """Test that no item in frequent_items.json has category 'Commodities' if it is armor or clothing."""
        freq_path = PATHS.resource("frequent_items.json")
        self.assertTrue(os.path.exists(freq_path), "frequent_items.json missing!")
        
        with open(freq_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        armor_keywords = [
            "helmet", "core", "arms", "legs", "backpack", "undersuit", "suit",
            "armor", "gloves", "visor", "gauntlets", "greaves", "chest",
            "aril", "adp", "orc-", "lynx", "macflex", "strata", "pab-",
            "morozov", "novikov", "pembroke", "stitcher", "paladin",
            "manticore", "geist", "chiron", "argus", "artimex", "aztalan",
            "bokto", "carrion", "clash", "monde", "wrecker", "arden",
            "shirt", "goggles", "pumps", "pants", "jacket", "coat", "hat",
            "boots", "shoes", "trousers", "dress", "vest", "beret", "sweater"
        ]
        not_armor_keywords = ["coolcore", "cooler", "power plant", "shield generator", "quantum drive"]

        violations = []
        for item in items:
            cat = item.get("category", "")
            if cat == "Commodities":
                name_low = item.get("name", "").lower()
                if any(k in name_low for k in not_armor_keywords):
                    continue
                if any(k in name_low for k in armor_keywords):
                    violations.append(item["name"])

        print(f"[TEST 2] Miscategorized armor violations found: {len(violations)}")
        self.assertEqual(len(violations), 0, f"Found armor items categorized as Commodities: {violations}")

    def test_03_no_stanton_cargo_terminal(self):
        """Test that procurement chain never generates non-existent location 'Stanton Cargo Terminal'."""
        test_items = [
            {"name": "P4-AR Rifle", "qty": 5, "price": 4500},
            {"name": "Aril Core", "qty": 2, "price": 5168},
            {"name": "Recycled Material Composite (RMC)", "qty": 10, "price": 10710},
            {"name": "Unknown Quantum Converter", "qty": 1, "price": 1000}
        ]
        
        procurement, sorted_locs, _ = build_procurement_route(test_items, loading_loc="Area18")
        
        for item_res in procurement:
            loc_str = str(item_res.get("loc", ""))
            raw_loc = str(item_res.get("raw_loc", ""))
            self.assertNotIn("stanton cargo terminal", loc_str.lower(),
                             f"Procurement item '{item_res['name']}' produced invalid location: '{loc_str}'")
            self.assertNotIn("stanton cargo terminal", raw_loc.lower(),
                             f"Procurement item '{item_res['name']}' produced invalid raw location: '{raw_loc}'")

        # Test enrich_location directly
        enriched = enrich_location("Stanton Cargo Terminal")
        self.assertNotIn("stanton cargo terminal", enriched.lower(),
                         f"enrich_location produced invalid output: '{enriched}'")

    def test_04_system_isolation(self):
        """Test that items from Pyro system do not get Stanton locations and vice versa."""
        # Query Aril Core when loading location is Orison (Stanton)
        proc_stanton, _, _ = build_procurement_route([{"name": "Aril Core", "qty": 1}], loading_loc="Orison")
        loc_stanton = proc_stanton[0]["loc"]
        
        # Query Pyro-exclusive item (e.g. checkmate/ruin station item or Pyro query)
        proc_pyro, _, _ = build_procurement_route([{"name": "MedPen", "qty": 5}], loading_loc="Ruin Station")
        loc_pyro = proc_pyro[0]["loc"]
        
        print(f"[TEST 4] Stanton route location: {loc_stanton}")
        print(f"[TEST 4] Pyro route location: {loc_pyro}")
        
        self.assertTrue(loc_pyro.startswith("PYRO"), f"Pyro loading location route should start with PYRO: '{loc_pyro}'")
        self.assertTrue(loc_stanton.startswith("STANTON"), f"Stanton loading location route should start with STANTON: '{loc_stanton}'")


if __name__ == '__main__':
    unittest.main()
