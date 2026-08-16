import os
import sys
import unittest
import tkinter as tk
import customtkinter as ctk

# Ensure paths
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_path not in sys.path:
    sys.path.insert(0, base_path)

import ui_panel
from src.core.app import StarlifterApp
from src.ui.create_package import BUILT_IN_PACKAGES
from src.ui.quick_add_cargo import setup_quick_add_panel

class TestLogistics(unittest.TestCase):
    def setUp(self):
        ctk.set_appearance_mode("dark")
        self.app = StarlifterApp()
        if hasattr(self.app, 'show_main_app_layout'):
            try:
                for child in list(self.app.winfo_children()):
                    try:
                        child.pack_forget()
                        child.destroy()
                    except Exception: pass
                self.app.show_main_app_layout()
            except Exception:
                pass
        setup_quick_add_panel(self.app)
        
    def tearDown(self):
        self.app.destroy()

    def test_ui_layout_verification(self):
        """
        UI Layout Verification: Confirm [ QUICK-ADD CARGO ITEM ] contains ONLY single items 
        and [ QUICK-ADD ITEM PACKAGE ] exists directly below it.
        """
        # 1. Verify single item combo exists and does not contain built-in packages
        single_combo = getattr(self.app, 'quick_add_combo', None) or getattr(self.app, 'item_combo', None) or getattr(self.app, 'item_dropdown', None)
        self.assertIsNotNone(single_combo, "Single item combo box not found in UI.")
        
        single_items = single_combo.cget("values")
        for pkg_name in BUILT_IN_PACKAGES.keys():
            self.assertNotIn(pkg_name, single_items, f"Package '{pkg_name}' should not be in Single Items dropdown!")
            
        # 2. Verify Package combo exists
        package_combo = getattr(self.app, 'package_combo', None)
        if not package_combo:
            def _find_pkg_combo(w):
                for sub in w.winfo_children():
                    if isinstance(sub, ctk.CTkComboBox):
                        try:
                            vals = sub.cget("values")
                            if any(k in vals for k in BUILT_IN_PACKAGES.keys()):
                                return sub
                        except Exception: pass
                    if hasattr(sub, 'winfo_children'):
                        res = _find_pkg_combo(sub)
                        if res: return res
                return None
            package_combo = _find_pkg_combo(self.app)

        self.assertIsNotNone(package_combo, "Package combo box not found in UI.")
        
        package_items = package_combo.cget("values")
        for pkg_name in BUILT_IN_PACKAGES.keys():
            self.assertIn(pkg_name, package_items, f"Package '{pkg_name}' should be in Packages dropdown!")

if __name__ == '__main__':
    unittest.main()
