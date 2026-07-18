# Extract UI functions from entry.py into ui_panel.py
import os

# Read entry.py
with open('source/entry.py', 'r', encoding='utf-8') as f:
    entry_lines = f.readlines()

# Extract L126-L1571 (0-indexed: 125-1570)
ui_block = entry_lines[125:1571]

# Read current ui_panel.py header
with open('source/ui_panel.py', 'r', encoding='utf-8') as f:
    header = f.read()

# Build the extracted content
# Remove inline monkey-patch assignments that reference `main.` at module level
# These will be handled by apply_all_patches() instead
lines_to_skip = set()
skip_patterns = [
    'main.RequisitionApp.__init__ = patched_init',
    'main.RequisitionApp.create_left_panel = patched_create_left_panel',
    'main.RequisitionApp.resolve_slang = resolve_slang',
    'main.RequisitionApp.handle_global_paste = handle_global_paste',
    'main.RequisitionApp.show_main_app_layout = _patched_show_main',
    'main.RequisitionApp.add_new_vessel_dialog = _patched_add_new_vessel',
]

cleaned_block = []
for line in ui_block:
    stripped = line.strip()
    skip = False
    for pat in skip_patterns:
        if pat in stripped:
            skip = True
            break
    if not skip:
        cleaned_block.append(line)

# Build apply_all_patches function
apply_fn = '''

# ══════════════════════════════════════════════════════════════════════════
# SECTION: apply_all_patches() — centralizes all monkey-patches
# ══════════════════════════════════════════════════════════════════════════

def apply_all_patches(main_module):
    """Apply all UI monkey-patches to main.RequisitionApp.
    
    Called once from entry.py after all imports are resolved.
    """
    # Store original init for chaining
    _orig_init = main_module.RequisitionApp.__init__
    
    def _wrapped_init(self, *args, **kwargs):
        patched_init(self, *args, **kwargs)
    _wrapped_init._original = _orig_init
    
    # Apply patches
    main_module.RequisitionApp.__init__ = _wrapped_init
    main_module.RequisitionApp.create_left_panel = patched_create_left_panel
    main_module.RequisitionApp.resolve_slang = resolve_slang
    main_module.RequisitionApp.handle_global_paste = handle_global_paste
    main_module.RequisitionApp.show_main_app_layout = _patched_show_main
    main_module.RequisitionApp.add_new_vessel_dialog = _patched_add_new_vessel
    main_module.RequisitionApp.animate_generate_supply_route_pdf = _patched_animate_generate
    main_module.RequisitionApp.run_supply_route_generation = lambda self, items=None, warehouse="": generate_pdf_direct(self)
    main_module.RequisitionApp.generate_supply_route_pdf = _patched_generate_supply_route_pdf
    
    # Manifest generation patch
    _orig_gen_req = main_module.RequisitionApp.generate_requisition_pdf
    
    def _patched_gen_req(self):
        cls_val = self._classify_var.get().upper() if hasattr(self, "_classify_var") else "ALL"
        if cls_val == "ALL":
            messagebox.showwarning("Classification Required",
                "Select a specific classification (PUBLIC / SECURED / CLASSIFIED) before generating.")
            return
        cls_to_sec = {
            "CLASSIFIED": "OFFICERS_ONLY_ENCRYPTED",
            "SECURED": "RESTRICTED",
            "PUBLIC": "OPEN_PUBLIC",
        }
        sec_val = cls_to_sec.get(cls_val, "OFFICERS_ONLY_ENCRYPTED")
        if hasattr(self, "security_level_var"):
            self.security_level_var.set(sec_val)
        _play_sound("pdf_generated.wav")
        return _orig_gen_req(self)
    
    main_module.RequisitionApp.generate_requisition_pdf = _patched_gen_req
    
    # MilitaryPDF class patch
    main_module.MilitaryPDF = PatchedMilitaryPDF
'''

# Write combined file
with open('source/ui_panel.py', 'w', encoding='utf-8') as f:
    f.write(header)
    f.write('\n')
    f.write(''.join(cleaned_block))
    f.write(apply_fn)

# Count lines
with open('source/ui_panel.py', 'r', encoding='utf-8') as f:
    total = sum(1 for _ in f)

print(f"ui_panel.py created: {total} lines")
print(f"Extracted {len(cleaned_block)} lines from entry.py")
