# -*- coding: utf-8 -*-
"""
test_courtesy_and_quantum.py — Verify that:
1. Free Supply (Courtesy) items and Paid items of the same name DO NOT merge into a single row on Refresh Cargo Table.
2. Quantum Drives and Quantum Engines are correctly categorized as 'Ship Components'.
"""
import unittest
from src.core.data_tree_engine import audit_cargo_table

class MockVar:
    def __init__(self, val=""):
        self.val = val
    def set(self, val):
        self.val = val
    def get(self):
        return self.val

class MockApp:
    def __init__(self):
        self.cargo_rows = []
        self._in_table_audit = False

    def clear_all_rows(self):
        self.cargo_rows = []

    def add_cargo_row_to_ui(self, name="", qty="1", box_size="1 SCU", price=0, courtesy=False, _skip_autoloader=False):
        row = {
            "name_var": MockVar(name),
            "qty_var": MockVar(qty),
            "box_size_var": MockVar(box_size),
            "price_var": MockVar(price),
            "courtesy_var": MockVar(courtesy),
            "status_var": MockVar("LOOSE")
        }
        self.cargo_rows.append(row)

class TestCourtesyAndQuantum(unittest.TestCase):

    def test_courtesy_and_paid_do_not_merge(self):
        app = MockApp()
        # Add 10 CRUZ Lux purchased (Paid)
        app.add_cargo_row_to_ui("CRUZ Lux", qty="10", price=6, courtesy=False)
        # Add 100 CRUZ Lux Free Supply (Courtesy)
        app.add_cargo_row_to_ui("CRUZ Lux", qty="100", price=0, courtesy=True)

        self.assertEqual(len(app.cargo_rows), 2)

        # Execute Refresh Cargo Table (audit_cargo_table)
        audit_cargo_table(app)

        # Should remain 2 separate rows: 1 paid, 1 courtesy free supply
        self.assertEqual(len(app.cargo_rows), 2, "Free Supply and Paid items must not merge into one row!")
        
        # Verify row 1 (Paid)
        paid_row = [r for r in app.cargo_rows if not r["courtesy_var"].get()][0]
        self.assertEqual(paid_row["name_var"].get(), "CRUZ Lux")
        self.assertEqual(paid_row["qty_var"].get(), "10")
        self.assertEqual(paid_row["price_var"].get(), 6)

        # Verify row 2 (Courtesy Free Supply)
        free_row = [r for r in app.cargo_rows if r["courtesy_var"].get()][0]
        self.assertEqual(free_row["name_var"].get(), "CRUZ Lux")
        self.assertEqual(free_row["qty_var"].get(), "100")
        self.assertEqual(free_row["price_var"].get(), 0)

    def test_quantum_drives_classification(self):
        from src.ui.quick_add_cargo import _get_item_category
        class MockParent: pass
        p = MockParent()

        drives = [
            "VK-00 Quantum Drive",
            "Crossfield Quantum Drive",
            "TS-2 Quantum Drive",
            "Beacon (quantum drive)",
            "Quantum Engine S1",
            "Quantum Drive"
        ]

        for d in drives:
            cat = _get_item_category(d)
            self.assertEqual(cat, "ship components", f"Drive '{d}' was classified as '{cat}' instead of 'ship components'!")

if __name__ == "__main__":
    unittest.main()
