import os
import sys
import customtkinter as ctk

# Ensure correct DLL paths and paths are loaded before importing main
from path_config import PATHS

# Load main application module and apply UI patches
import main
import ui_panel

# Import modular components
from src.ui.quick_add_cargo import setup_quick_add_panel
from src.ui.create_package import CreatePackageModal
from src.core.data_tree_engine import audit_cargo_table
from src.pdf.dynamic_pdf_engine import generate_pdf_direct
from src.agents.cargo_packer import unpack_packages_and_autoload
from src.core.update_checker import check_for_updates

class StarlifterApp(main.RequisitionApp):
    """
    Core application logic inheriting from the legacy patched system.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        check_for_updates()
        
    def create_left_panel(self, *args, **kwargs):
        """Override to implement the new UI layout with Quick-Add separation."""
        super().create_left_panel(*args, **kwargs)
        setup_quick_add_panel(self, *args, **kwargs)
        
    def add_cargo_row_to_ui(self, name, qty, box_size, price, status="LOOSE", **kwargs):
        """Override to implement Universal Autoloader logic."""
        unpacked_items = unpack_packages_and_autoload(name, qty, box_size, price, status)
        for item in unpacked_items:
            # Do NOT pass status to super() as the legacy method does not accept it
            super().add_cargo_row_to_ui(
                name=item["name"], 
                qty=item["qty"], 
                box_size=item["box_size"], 
                price=item["price"],
                **kwargs
            )
            
    def show_create_package_modal(self):
        """Custom logic for the Create Package Modal."""
        CreatePackageModal(self)
        
    def consolidate_table(self):
        """Override for Table Consolidator & Courtesy updates."""
        audit_cargo_table(self)
        
    def generate_supply_route_pdf(self, *args, **kwargs):
        """Override for dynamic multi-page PDF generation."""
        generate_pdf_direct(self)
        
    def generate_requisition_pdf(self, *args, **kwargs):
        super().generate_requisition_pdf(*args, **kwargs)
        
    def show_main_app_layout(self, *args, **kwargs):
        super().show_main_app_layout(*args, **kwargs)
        
    def load_vessel_loadout(self, *args, **kwargs):
        super().load_vessel_loadout(*args, **kwargs)
        
    def open_officer_rulebook(self, *args, **kwargs):
        """Override the base compiled manual to show the updated v0.6.1 manual."""
        import customtkinter as ctk
        
        rule_win = ctk.CTkToplevel(self)
        rule_win.title("Logistics Manual v0.6.1")
        rule_win.geometry("700x500")
        rule_win.attributes('-topmost', True)
        
        textbox = ctk.CTkTextbox(rule_win, width=680, height=480, font=("Consolas", 12))
        textbox.pack(padx=10, pady=10, fill="both", expand=True)
        
        manual_text = """UEE NAVY LOGISTICS FIELD REFERENCE MANUAL (v0.6.1)
==================================================
BY ORDER OF SUPPLY COMMAND // SECURE STANTON SUPPLY LINES AT ALL COSTS

1. STOR-ALL PACKAGING CAPACITIES
--------------------------------
The physical grid volume is now strictly enforced 1:1.
- Stor-All 1 SCU  = 1.00 SCU Grid Space
- Stor-All 2 SCU  = 2.00 SCU Grid Space
- Stor-All 4 SCU  = 4.00 SCU Grid Space
- Stor-All 8 SCU  = 8.00 SCU Grid Space

2. UNIVERSAL AUTOLOADER RATIOS
--------------------------------
- Rifles (e.g., P4-AR): 1 weapon per 40 magazines.
- Medical (ParaMed / LifeGuard): 1 device per 4 refills.
- Multi-tools: 1 tool per 1 battery.

3. PURE-CARGO ROUTING RULES
--------------------------------
PDF generated supply routes are strictly limited to Pure-Cargo haulers.
Exploration and touring vessels (Carrack, 890 Jump, Odyssey, Corsair, 
Constellation Aquila/Phoenix, 600i) are explicitly BANNED from cargo reports 
regardless of theoretical SCU capacities. Only C2, Caterpillar, RAFT, 
and similar haulers will be recommended for route logistics.

4. CRUZ LUX VERIFICATION
--------------------------------
Locations for Cruz Lux are dynamically pulled from global supply databases 
(trade and wiki), completely removing local 3-station restrictions. All 
Cruz Lux entries bypass UEX limits with a forced VERIFIED status.
"""
        textbox.insert("1.0", manual_text)
        textbox.configure(state="disabled")
