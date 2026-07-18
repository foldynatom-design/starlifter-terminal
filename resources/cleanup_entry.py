# -*- coding: utf-8 -*-
"""Remove duplicate lore/signature/section code from entry.py (lines 105-464)."""
import os

entry_path = os.path.join(os.path.dirname(__file__), '..', 'source', 'entry.py')

with open(entry_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Original: {len(lines)} lines")

# Lines to keep: 1-104 (bootstrap + _play_sound) and 465+ (draw_report_paragraph onward)
# Lines to remove: 105-464 (0-indexed: 104-463)
# Replace with compact comment block

replacement = [
    "\r\n",
    "# ── SECTION 2: Lore System → moved to lore_helper.py ──\r\n",
    "# ── SECTION 3: Image Processing → moved to signature_helper.py ──\r\n",
    "\r\n",
    "# RP Stories — imported from rp_stories.py (uses {cargo_type} placeholder)\r\n",
    "from rp_stories import stories\r\n",
    "_stories_loaded = True\r\n",
    "\r\n",
    "# Volume map: use storall_packer's 2371-entry database (from item_volumes.json)\r\n",
    "# instead of old hardcoded dict. Loaded lazily on first access.\r\n",
    "volume_map = load_volume_map()\r\n",
    "\r\n",
    "# ── SECTION 4: PDF Helpers ──\r\n",
    "# ── get_telemetry() → moved to lore_helper.py ──\r\n",
    "\r\n",
]

new_lines = lines[:104] + replacement + lines[464:]

with open(entry_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"New: {len(new_lines)} lines")
print(f"Removed: {len(lines) - len(new_lines)} lines")
print(f"Lines 105-119 preview:")
for i, line in enumerate(new_lines[104:119], start=105):
    print(f"  {i}: {line.rstrip()}")
