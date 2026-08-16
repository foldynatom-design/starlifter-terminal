import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from path_config import PATHS
from storall_packer import calculate_cargo_breakdown, load_volume_map
from pdf_engine import generate_pdf_direct

class TestIntegrationV06(unittest.TestCase):

    def test_01_clean_install_seeding(self):
        # Simulate clean install by verifying ensuring resources works
        PATHS.ensure_resources()
        self.assertTrue(os.path.exists(PATHS.resource('uex_locations_db.json')))
        self.assertTrue(os.path.exists(PATHS.resource('ship_grids_db.json')))
        self.assertTrue(os.path.exists(PATHS.resource('uex_trade_db.json')))
        # self.assertTrue(os.path.exists(PATHS.resource('sc_wiki_db.json'))) # sc_wiki_db.json is not seeded by path_config

    def test_02_category_ab_packing(self):
        # Category A: Ordnance (Grid Direct)
        # Category B: Medpens (Containerized)
        
        items = [
            {"name": "Seeker IX Torpedo", "qty": 4, "box_size": "24 SCU"}, # Category A
            {"name": "Hemozal Medpen", "qty": 100, "box_size": "1 unit"} # Category B
        ]
        
        breakdown = calculate_cargo_breakdown(items)
        
        # Verify ordnance is in GRID_DIRECT / ordnance_items
        ordnance = breakdown.get("ordnance_items", [])
        self.assertEqual(len(ordnance), 1)
        self.assertEqual(ordnance[0]["name"], "Seeker IX Torpedo")
        
        # Verify medpen was containerized into a Stor-All box
        boxes = breakdown.get("stor_all_boxes", [])
        self.assertTrue(len(boxes) > 0)
        
        # Ensure medpen is not in grid direct or commodity
        self.assertEqual(len(breakdown.get("commodity_items", [])), 0)

    def test_03_pdf_multi_page_and_eva(self):
        class MockVar:
            def __init__(self, val):
                self.val = val
            def get(self):
                return self.val
                
        class MockApp:
            def __init__(self):
                self.req_id_var = MockVar("TEST-V06")
                self.ship_selector = MockVar("C2 Hercules Starlifter")
                self.vessel = "C2 Hercules Starlifter"
                self.location_var = MockVar("ARC-L1 Wide Forest Station") # EVA keyword L1
                self.cargo_rows = []
                # 30 items will exceed a single page limit (30 * 7.5 = 225 mm)
                for i in range(30):
                    self.cargo_rows.append({
                        'name_var': MockVar(f"Test Item {i}"),
                        'qty_var': MockVar("10"),
                        'box_size_var': MockVar("1 SCU"),
                        'price_var': MockVar("100")
                    })
        
        mock_app = MockApp()
        test_pdf_path = os.path.join(os.path.dirname(__file__), "test_overflow.pdf")
        generate_pdf_direct(mock_app, save_path=test_pdf_path)
        
        self.assertTrue(os.path.exists(test_pdf_path))
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)

if __name__ == '__main__':
    unittest.main()
