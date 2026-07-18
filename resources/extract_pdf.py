# -*- coding: utf-8 -*-
"""Extract PDF engine code from entry.py into pdf_engine.py"""
import os

# Read entry.py
with open('source/entry.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"entry.py: {len(lines)} lines")

# Extract lines 120-2007 (0-indexed: 119:2007)
pdf_block = lines[119:2007]
print(f"PDF block: {len(pdf_block)} lines (L120-L2007)")

# Build pdf_engine.py header
header_lines = [
    '# -*- coding: utf-8 -*-\n',
    '"""\n',
    'pdf_engine.py - PDF generation engine for Starlifter Terminal.\n',
    '\n',
    'Contains PatchedMilitaryPDF class, draw_signatures, generate_pdf_direct,\n',
    'and all PDF helper functions extracted from entry.py.\n',
    '\n',
    'Usage:\n',
    '    from pdf_engine import PatchedMilitaryPDF, generate_pdf_direct\n',
    '"""\n',
    '\n',
    'import os\n',
    'import sys\n',
    'import re\n',
    'import random\n',
    'import math\n',
    'import json\n',
    'from tkinter import messagebox\n',
    '\n',
    'import main\n',
    '\n',
    '# Imports from other modules\n',
    'from rp_stories import stories\n',
    'from storall_packer import load_volume_map\n',
    'from lore_helper import (\n',
    '    get_telemetry, get_cargo_context_sentence,\n',
    '    rephrase_crew_text, apply_synonyms, ore_quality_map,\n',
    ')\n',
    'from signature_helper import (\n',
    '    extract_rank, process_signature, get_signatures_dir,\n',
    '    process_r1_stamp, get_processed_barcode_path,\n',
    ')\n',
    'from fleet_helper import _recommend_shuttle, _CONCEPT_SHIPS\n',
    'from uex_sync import (\n',
    '    _uex_locations_db, _uex_ships_db,\n',
    '    _uex_trade_db, _uex_items_trade_db,\n',
    '    _ensure_trade_dbs,\n',
    ')\n',
    '\n',
    '# Shared state\n',
    'LORE_STORY_CACHE = {}\n',
    '_story_rng = random.Random()\n',
    '_SESSION_SEED = hash((os.getpid(), id(sys.modules)))\n',
    '\n',
    '# Volume map from item_volumes.json\n',
    'volume_map = load_volume_map()\n',
    '\n',
]

# Write pdf_engine.py
with open('source/pdf_engine.py', 'w', encoding='utf-8') as f:
    f.writelines(header_lines)
    f.writelines(pdf_block)

total_pe = len(header_lines) + len(pdf_block)
print(f"Written pdf_engine.py: {total_pe} lines")

# Now remove lines 120-2007 from entry.py and replace with import block
import_lines = [
    '# PDF Engine -> moved to pdf_engine.py\n',
    'from pdf_engine import (\n',
    '    PatchedMilitaryPDF, generate_pdf_direct,\n',
    '    draw_report_paragraph, draw_signatures,\n',
    '    _FONT_CACHE, _precache_fonts,\n',
    '    LORE_STORY_CACHE, _story_rng, _SESSION_SEED,\n',
    '    volume_map,\n',
    ')\n',
    'from pdf_engine import _patched_generate_supply_route_pdf\n',
    '\n',
    '# Apply monkey-patches that pdf_engine defines\n',
    'main.MilitaryPDF = PatchedMilitaryPDF\n',
    '\n',
]

new_lines = lines[:119] + import_lines + lines[2007:]
with open('source/entry.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"entry.py: {len(lines)} -> {len(new_lines)} lines")
print("Done!")
