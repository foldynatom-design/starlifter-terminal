# -*- coding: utf-8 -*-
"""
pdf_engine.py - PDF generation engine for Starlifter Terminal.

Contains PatchedMilitaryPDF class, draw_signatures, generate_pdf_direct,
and all PDF helper functions extracted from entry.py.

Usage:
    from pdf_engine import PatchedMilitaryPDF, generate_pdf_direct
"""

import os
import sys
import re
import random
import math
import json
from tkinter import messagebox

import main
from path_config import PATHS

# Imports from other modules
from rp_stories import stories
from storall_packer import load_volume_map, calculate_cargo_breakdown
from lore_helper import (
    get_telemetry, get_cargo_context_sentence,
    rephrase_crew_text, apply_synonyms, ore_quality_map,
    extract_rank,
)
from signature_helper import (
    process_signature, get_signatures_dir,
    process_r1_stamp, get_processed_barcode_path,
)
from fleet_helper import _recommend_shuttle, _recommend_cargo_ship, _CONCEPT_SHIPS
from uex_sync import (
    _uex_locations_db, _uex_ships_db,
    _uex_trade_db, _uex_items_trade_db,
    _ensure_trade_dbs,
)

# Shared state
LORE_STORY_CACHE = {}
_story_rng = random.Random()
_SESSION_SEED = hash((os.getpid(), id(sys.modules)))

# Volume map from item_volumes.json
volume_map = load_volume_map()

def draw_report_paragraph(self, x, y, width, text, redacted_sentences_indices=None, fully_redacted=False):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    self.set_xy(x, y)
    self.set_font("Roboto", "", 8)
    line_height = 4.0
    space_w = self.get_string_width(' ')
    current_x = x
    current_y = y
    for idx, sentence in enumerate(sentences):
        is_redacted = fully_redacted or (redacted_sentences_indices and idx in redacted_sentences_indices)
        words = sentence.split(' ')
        for w_idx, word in enumerate(words):
            word_to_draw = word + (' ' if w_idx < len(words) - 1 else '')
            word_w = self.get_string_width(word_to_draw)
            if current_x + word_w > x + width:
                current_x = x
                current_y += line_height
                self.set_xy(current_x, current_y)
            if is_redacted:
                self.set_fill_color(0, 0, 0)
                self.rect(current_x, current_y + 0.5, word_w - 0.5, line_height - 1, 'F')
                current_x += word_w
            else:
                self.set_text_color(30, 40, 60)
                self.cell(word_w, line_height, word_to_draw, ln=0)
                current_x += word_w
        if idx < len(sentences) - 1:
            current_x += space_w
    return current_y

def draw_signatures(self):
    current_y = self.get_y()
    if current_y > (self.h - 85):
        self.add_page()
        current_y = self.get_y()
    box_y = max(current_y + 4, 48)  # Ensure below header
    box_height = 276 - box_y
    if box_height < 75:
        self.add_page()
        box_y = 48
        box_height = 276 - box_y
    self.set_line_width(0.3)
    self.set_draw_color(100, 116, 139)
    # White background with subtle border for manifest
    self.set_fill_color(245, 247, 250)
    self.rect(12, box_y, 186, box_height, 'DF')
    # Navy header bar for section title
    self.set_fill_color(15, 30, 60)
    self.rect(12, box_y, 186, 6, 'F')
    self.set_text_color(220, 220, 220)
    self.set_font("Roboto", "B", 8)
    self.text(14, box_y + 4.2, "LOGISTICS DIRECTIVE & FIELD REPORT")
    severity_level = self.severity.upper()
    danger_level = "LOW"
    if "MINOR" in severity_level:
        danger_level = "LOW"
    elif "SEVERE" in severity_level:
        danger_level = "MEDIUM"
    elif "CATASTROPHIC" in severity_level:
        danger_level = "HIGH"
        
    items_list = getattr(self, "manifest_items", [])
    current_manifest_hash = str([(item["name"], item["qty"]) for item in items_list])
    current_captain = self.captain if self.captain else ""
    current_officer = self.loading_officer if self.loading_officer else ""
    current_crew = self.loading_crew if self.loading_crew else ""
    current_vessel = self.vessel if self.vessel else ""
    
    global LORE_STORY_CACHE
    cache_invalid = (
        LORE_STORY_CACHE.get("text") is None or
        LORE_STORY_CACHE.get("danger_level") != danger_level or
        LORE_STORY_CACHE.get("vessel") != current_vessel or
        LORE_STORY_CACHE.get("manifest_hash") != current_manifest_hash or
        LORE_STORY_CACHE.get("captain") != current_captain or
        LORE_STORY_CACHE.get("officer") != current_officer or
        LORE_STORY_CACHE.get("crew") != current_crew
    )
    
    if cache_invalid:
        # Seed from session + vessel + cargo + danger for per-launch + per-config variation
        combined_seed = hash((_SESSION_SEED, current_vessel, current_manifest_hash, danger_level))
        _story_rng.seed(combined_seed)
        if danger_level == "LOW":
            story_idx = _story_rng.randint(0, 9)
        elif danger_level == "MEDIUM":
            story_idx = _story_rng.randint(10, 19)
        else:
            story_idx = _story_rng.randint(20, 29)
        story_template = stories[story_idx]
        
        cargo_sentence = get_cargo_context_sentence(items_list)
        story_template = story_template.replace("{ship}", "{ship}" + cargo_sentence)
        # Build cargo_type from actual items
        if items_list:
            top_items = sorted(items_list, key=lambda x: int(x.get('qty', 1)) if str(x.get('qty', 1)).isdigit() else 1, reverse=True)[:2]
            cargo_desc_parts = [ti['name'].split(' (')[0][:20] for ti in top_items]
            cargo_type = " and ".join(cargo_desc_parts) if cargo_desc_parts else "supply"
        else:
            cargo_type = "supply"
        
        crew_val = self.loading_crew
        is_crew_empty = not crew_val or crew_val.strip().upper() in ["NONE", "PENDING", "PENDING APPROVED", ""]
        if is_crew_empty:
            formatted_story = rephrase_crew_text(story_template, self.loading_officer)
            formatted_story = formatted_story.format(
                captain=self.captain,
                officer=self.loading_officer,
                ship=self.vessel,
                location=self.location,
                cargo_type=cargo_type
            )
        else:
            formatted_story = story_template.format(
                captain=self.captain,
                officer=self.loading_officer,
                crew=crew_val,
                ship=self.vessel,
                location=self.location,
                cargo_type=cargo_type
            )
        formatted_story = apply_synonyms(formatted_story)
        LORE_STORY_CACHE["text"] = formatted_story
        LORE_STORY_CACHE["danger_level"] = danger_level
        LORE_STORY_CACHE["vessel"] = current_vessel
        LORE_STORY_CACHE["manifest_hash"] = current_manifest_hash
        LORE_STORY_CACHE["captain"] = current_captain
        LORE_STORY_CACHE["officer"] = current_officer
        LORE_STORY_CACHE["crew"] = current_crew
        
    formatted_story = LORE_STORY_CACHE["text"]
    self.set_line_width(0.2)
    self.set_draw_color(180, 190, 200)
    self.line(140, box_y + 8, 140, box_y + box_height - 24)
    sec = self.security_level.upper()
    fully_redacted = False
    redacted_sentences_indices = []
    # CLASSIFIED (OFFICERS) = NO redaction at all
    # SECURED/RESTRICTED = redact every other sentence
    if "RESTRICTED" in sec or ("SECURED" in sec and "OFFICERS" not in sec and "ENCRYPTED" not in sec):
        sentences_count = len(re.split(r'(?<=[.!?])\s+', formatted_story))
        redacted_sentences_indices = [i for i in range(sentences_count) if i % 2 == 1]
    # PUBLIC = fully redacted
    elif "PUBLIC" in sec or "OPEN" in sec:
        fully_redacted = True
    # OFFICERS/ENCRYPTED/CLASSIFIED = no redaction
        
    paragraph_end_y = self.draw_report_paragraph(14, box_y + 10, 122, formatted_story, redacted_sentences_indices, fully_redacted)
    
    loose_items = []
    total_loose_vol = 0.0
    items_list = getattr(self, "manifest_items", [])
    
    # Whitelist: categories of personal items that go into Stor-All boxes
    STOR_ALL_CATEGORIES = [
        "pistol", "rifle", "shotgun", "smg", "lmg", "sniper", "knife", "weapon",
        "grenade", "multitool", "multi-tool", "tractor", "maxlift", "cambio",
        "food", "burrito", "sandwich", "noodle", "drink", "bottle", "bar ", "ration",
        "lux", "cruz", "big benny",
        "medpen", "medkit", "oxypen", "adrenapen",
        "mining gadget", "mining attachment", "mining head", "mining module",
        "armor", "helmet", "undersuit", "backpack", "chest", "legs", "arms",
        "flightsuit", "jacket", "vest",
        "battery", "canister", "srt", "magazine", "fire extinguisher",
    ]

    for item in items_list:
        name_low = item["name"].lower()
        qty = int(item["qty"]) if isinstance(item["qty"], (int, float)) or (isinstance(item["qty"], str) and item["qty"].isdigit()) else 1
        
        # Only whitelist items need Stor-All
        is_stor_all = any(cat in name_low for cat in STOR_ALL_CATEGORIES)
        if not is_stor_all:
            continue
        
        # Skip Stor-All containers themselves
        if "stor" in name_low and ("all" in name_low or "storage" in name_low):
            continue
        
        # Skip large cargo crates (2+ SCU) â€” keep 1 SCU personal items
        box = item["box_size"].lower()
        if any(s in box for s in ["2 scu", "4 scu", "8 scu", "16 scu", "24 scu", "32 scu"]):
            continue
        
        unit_vol = 0.0
        for k, vol in volume_map.items():
            if k in name_low:
                unit_vol = vol
                break
        if unit_vol == 0.0:
            unit_vol = 0.005
        
        item_vol = qty * unit_vol
        total_loose_vol += item_vol
        loose_items.append({
            "name": item["name"],
            "qty": qty,
            "unit_vol": unit_vol,
            "total_vol": item_vol
        })
            
    # Available Stor-All sizes: usable capacity per box
    # Only 1+ SCU sizes â€” sub-1-SCU items don't occupy grid slots
    STOR_ALL_SIZES = [
        (1.0,   "1 SCU",   0.85),
        (2.0,   "2 SCU",   1.70),
        (4.0,   "4 SCU",   3.40),
        (8.0,   "8 SCU",   6.80),
    ]
    
    def _pick_box_size(vol):
        """Pick the smallest Stor-All that fits ALL loose items in one box if possible."""
        for scu, label, cap in STOR_ALL_SIZES:
            if vol <= cap:
                return scu, label, cap
        return 8.0, "8 SCU", 6.80
    
    if total_loose_vol > 0:
        box_scu, box_label, max_capacity = _pick_box_size(total_loose_vol)
        num_boxes = math.ceil(total_loose_vol / max_capacity)
        # Cap at reasonable number
        num_boxes = min(num_boxes, 3)
    else:
        num_boxes = 0
        max_capacity = 0.85
        box_label = "1 SCU"
    
    boxes = [[] for _ in range(num_boxes)]
    box_vols = [0.0] * num_boxes
    
    curr_box_idx = 0
    for item in loose_items:
        qty_remaining = item["qty"]
        while qty_remaining > 0 and curr_box_idx < num_boxes:
            space_left = max_capacity - box_vols[curr_box_idx]
            max_fit = int(space_left // item["unit_vol"]) if item["unit_vol"] > 0 else qty_remaining
            if max_fit <= 0:
                curr_box_idx += 1
                continue
                
            fit_qty = min(qty_remaining, max_fit)
            fit_vol = fit_qty * item["unit_vol"]
            
            boxes[curr_box_idx].append({
                "name": item["name"],
                "qty": fit_qty,
                "vol": fit_vol
            })
            box_vols[curr_box_idx] += fit_vol
            qty_remaining -= fit_qty
            
            if box_vols[curr_box_idx] >= max_capacity:
                curr_box_idx += 1

    # Store autobox data for page 2 rendering (don't render on page 1 â€” no space)
    if num_boxes > 0 and ("VERIFIED" not in sec and "PUBLIC" not in sec):
        self._autobox_data = {
            "boxes": boxes, "box_vols": box_vols,
            "box_label": box_label, "max_capacity": max_capacity,
            "num_boxes": num_boxes
        }

    # â”€â”€ Position cargo directive + rec transport + sigs DYNAMICALLY â”€â”€
    content_bottom_y = max(paragraph_end_y + 2, box_y + 48)
    sig_space_needed = 24
    directive_space = 10
    total_bottom_needed = sig_space_needed + directive_space

    available_for_bottom = (box_y + box_height) - content_bottom_y
    if available_for_bottom < total_bottom_needed:
        content_bottom_y = box_y + box_height - total_bottom_needed

    # â”€â”€ SHIP GRID DATABASE LOOKUP â”€â”€
    grid_db_path = getattr(main, 'resource_path', lambda p: p)(os.path.join('resources', 'ship_grids_db.json'))
    vessel_clean = self.vessel
    for prefix in ["Aegis", "Anvil", "Drake", "RSI", "Crusader", "MISC", "Origin", "Consolidated Outland", "Argo", "Mirai", "Gatac", "Esperia"]:
        if vessel_clean.lower().startswith(prefix.lower()):
            vessel_clean = vessel_clean[len(prefix):].strip()
            break
    ship_grid = None
    if os.path.exists(grid_db_path):
        try:
            with open(grid_db_path, "r", encoding="utf-8") as gf:
                db_data = json.load(gf)
            vessel_low = self.vessel.lower().strip()
            vessel_clean_low = vessel_clean.lower().strip()
            for key, val in db_data.items():
                kl = key.lower()
                if kl == vessel_low or kl == vessel_clean_low:
                    ship_grid = val
                    break
            if not ship_grid:
                for key, val in db_data.items():
                    kl = key.lower()
                    if vessel_clean_low in kl or kl in vessel_clean_low or vessel_low in kl or kl in vessel_low:
                        ship_grid = val
                        break
            if not ship_grid:
                vessel_words = [w for w in vessel_low.split() if len(w) > 2]
                for key, val in db_data.items():
                    kl = key.lower()
                    if any(w in kl for w in vessel_words):
                        ship_grid = val
                        break
        except Exception:
            pass

    # â”€â”€ RIGHT SIDEBAR: Telemetry + Cargo Grid Preview â”€â”€
    grid_area_x = 142
    grid_area_y = box_y + 8
    grid_area_w = 54
    grid_area_h = box_height - 40

    # Draw sidebar background FIRST
    self.set_line_width(0.15)
    self.set_draw_color(180, 190, 200)
    self.set_fill_color(235, 238, 242)
    self.rect(grid_area_x, grid_area_y, grid_area_w, grid_area_h, 'DF')

    # â”€â”€ TELEMETRY SENSORS (top of sidebar) â”€â”€
    telemetry = get_telemetry(formatted_story, danger_level, items_list)
    self.set_font("Roboto", "B", 7)
    self.set_text_color(140, 100, 30)
    self.text(grid_area_x + 2, grid_area_y + 4.5, "HOLD TELEMETRY SENSORS:")

    sensor_y = grid_area_y + 9
    sensors = [
        ("GRAVITY FIELD:", telemetry["gravity"], {"ACTIVE": (46,204,113), "WARNING": (241,196,15)}),
        ("ATM SEAL INTEGRITY:", telemetry["atmosphere"], {"NOMINAL": (46,204,113), "PRESSURE": (241,196,15), "WARNING": (241,196,15)}),
        ("TRACTOR CLAMPS:", telemetry["clamps"], {"LOCKED": (46,204,113), "UNSTABLE": (241,196,15)}),
        ("HAZMAT / RADIATION:", telemetry["hazmat"], {"CLEAR": (46,204,113), "MONITORING": (241,196,15)}),
    ]
    for label, value, color_map in sensors:
        self.set_font("Roboto", "", 6)
        self.set_text_color(60, 70, 90)
        self.text(grid_area_x + 3, sensor_y, label)
        sensor_y += 3
        self.set_font("Roboto", "B", 6)
        # Pick color: green/yellow/red
        color_set = False
        for keyword, rgb in color_map.items():
            if keyword in value:
                self.set_text_color(*rgb)
                color_set = True
                break
        if not color_set:
            self.set_text_color(231, 76, 60)  # Red default
        self.text(grid_area_x + 3, sensor_y, value)
        sensor_y += 5

    # â”€â”€ Divider line â”€â”€
    self.set_draw_color(180, 190, 200)
    self.set_line_width(0.1)
    self.line(grid_area_x + 3, sensor_y, grid_area_x + grid_area_w - 3, sensor_y)
    sensor_y += 3

    # â”€â”€ CARGO GRID INFO (below telemetry) â”€â”€
    if "PUBLIC" in sec or "OPEN" in sec:
        self.set_font("Roboto", "B", 6)
        self.set_text_color(140, 100, 30)
        self.text(grid_area_x + 3, sensor_y, "CARGO [REDACTED]")
    elif ship_grid and "groups" in ship_grid:
        cap = ship_grid.get("capacity", "?")
        grps = len(ship_grid.get("groups", []))
        self.set_font("Roboto", "B", 6)
        self.set_text_color(140, 100, 30)
        self.text(grid_area_x + 3, sensor_y, "CARGO GRID")
        self.set_font("Roboto", "", 5.5)
        self.set_text_color(60, 70, 90)
        sfx = "s" if grps > 1 else ""
        self.text(grid_area_x + 5, sensor_y + 5, f"{cap} SCU / {grps} section{sfx}")
        self.set_font("Roboto", "I", 5)
        self.set_text_color(100, 110, 140)
        self.text(grid_area_x + 5, sensor_y + 10, "SEE PAGE 3")
        self.text(grid_area_x + 5, sensor_y + 14, "FULL SCHEMATIC")
    else:
        self.set_font("Roboto", "I", 6.5)
        self.set_text_color(80, 90, 110)
        self.text(grid_area_x + 5, sensor_y + 5, "NO GRID DATA")

    
    # Render Cargo Grid Placement Directive
    # â”€â”€ DYNAMIC CARGO DIRECTIVE (works for ALL ships) â”€â”€
    vessel_upper = self.vessel.upper()
    load_loc = getattr(self, 'location', '') or ''
    load_type = ''
    try:
        if hasattr(self, '_loading_type_var'):
            load_type = self._loading_type_var.get()
        elif hasattr(self, 'loading_type_var'):
            load_type = self.loading_type_var.get()
    except Exception: pass
    loc_sfx = f" Staging: {load_loc}." if load_loc else ""
    type_sfx = f" Method: {load_type}." if load_type else ""
    if ship_grid and "groups" in ship_grid:
        cap = ship_grid.get("capacity", 0)
        grp_count = len(ship_grid.get("groups", []))
        max_height = 1
        max_width = 1
        for g in ship_grid.get("groups", []):
            for gr in g.get("grids", []):
                max_height = max(max_height, gr.get("height", 1))
                max_width = max(max_width, gr.get("width", 1))
        max_crate = min(32, max_width * max_width)
        holds = f"{grp_count} hold section{'s' if grp_count > 1 else ''}"
        grid_directive = f"CARGO DIRECTIVE: {holds} ({cap} SCU). Stack: {max_height}h, {max_crate} SCU max.{loc_sfx}{type_sfx} Clamps locked."
    else:
        grid_directive = f"CARGO DIRECTIVE: Standard bay. Grid-lock all.{loc_sfx}{type_sfx} Verify clamp power."

    directive_y = content_bottom_y
    self.set_font("Roboto", "I", 5.5)
    self.set_text_color(60, 70, 90)
    # Cargo directive â€” redact for PUBLIC
    if "PUBLIC" in sec or "OPEN" in sec:
        self.text(14, directive_y, "CARGO DIRECTIVE: [REDACTED // PUBLIC CHANNEL]")
    else:
        self.text(14, directive_y, grid_directive[:140])

    # RECOMMENDED TRANSPORT SHIP (only for EVA / Landing Pad, NOT for Hangar)
    is_hangar_loading = "hangar" in load_type.lower() if load_type else False
    if "PUBLIC" not in sec and "OPEN" not in sec and not is_hangar_loading:
        try:
            total_cargo_scu = sum(
                int(float(i.get("qty", 1))) * (
                    8 if "8 scu" in i.get("box_size", "").lower()
                    else 4 if "4 scu" in i.get("box_size", "").lower()
                    else 2 if "2 scu" in i.get("box_size", "").lower()
                    else 1 if "1 scu" in i.get("box_size", "").lower()
                    else 0.05
                )
                for i in items_list
            ) + num_boxes
            cargo_rec = _recommend_cargo_ship(total_cargo_scu)
            if cargo_rec:
                self.set_font("Roboto", "B", 5)
                self.set_text_color(180, 140, 30)
                self.text(14, directive_y + 4, cargo_rec["note"][:130])
        except Exception:
            pass

    sig_section_y = box_y + box_height - sig_space_needed
    self.set_line_width(0.2)
    self.set_draw_color(15, 30, 60)
    self.line(12, sig_section_y, 198, sig_section_y)
    self.set_text_color(15, 30, 60)
    self.set_font("Roboto", "B", 7)
    self.text(15, sig_section_y + 4, "LOADING OFFICER SIGNATURE")
    self.text(108, sig_section_y + 4, "SHIP CAPTAIN SIGNATURE")
    officer_name = self.loading_officer if self.loading_officer else "Authorized Logistics Officer"
    self.set_text_color(40, 50, 70)
    self.set_font("Roboto", "", 6)
    if ("VERIFIED" in sec or "PUBLIC" in sec) and self.loading_officer:
        self.set_fill_color(0, 0, 0)
        self.rect(15, sig_section_y + 6, 80, 10, 'F')
        self.rect(108, sig_section_y + 6, 80, 10, 'F')
        self.text(15, sig_section_y + 9, "REDACTED // SECURED CHANNEL")
        self.text(108, sig_section_y + 9, "REDACTED // SECURED CHANNEL")
    else:
        self.text(15, sig_section_y + 9, f"Name: {officer_name}")
        captain_name = self.captain if self.captain else "Authorized Ship Captain"
        self.text(108, sig_section_y + 9, f"Name: {captain_name}")
        # Extract ranks from names (e.g. "Lt. Wolf" -> "Lieutenant")
        officer_rank, _ = extract_rank(officer_name)
        captain_rank, _ = extract_rank(captain_name)
        # Captain without explicit rank prefix -> "Ship Captain"
        if captain_rank == "UEE Logistics Officer":
            captain_rank = "Ship Captain"
        self.text(15, sig_section_y + 12, f"Rank: {officer_rank}")
        self.text(108, sig_section_y + 12, f"Rank: {captain_rank}")
        
        podpisy_dir = get_signatures_dir()
        officer_sig_img = process_signature(podpisy_dir, officer_name, is_captain=False)
        captain_sig_img = process_signature(podpisy_dir, captain_name, is_captain=True)
        r1_stamp_img = process_r1_stamp(podpisy_dir)
        
        if officer_sig_img and os.path.exists(officer_sig_img):
            self.image(officer_sig_img, x=45, y=sig_section_y + 5, w=35, h=8)
        else:
            self.set_font("Courier", "I", 7)
            self.set_text_color(150, 150, 150)
            self.text(50, sig_section_y + 9, f"~ {officer_name} ~")
            self.set_font("Roboto", "", 6)
            
        if captain_sig_img and os.path.exists(captain_sig_img):
            self.image(captain_sig_img, x=138, y=sig_section_y + 5, w=35, h=8)
        else:
            self.set_font("Courier", "I", 7)
            self.set_text_color(150, 150, 150)
            self.text(143, sig_section_y + 9, f"~ {captain_name} ~")
            self.set_font("Roboto", "", 6)
            
        if r1_stamp_img and os.path.exists(r1_stamp_img):
            self.image(r1_stamp_img, x=51, y=sig_section_y - 2, w=22, h=18)

    self.set_font("Roboto", "B", 6)
    self.set_text_color(80, 90, 110)
    self.text(15, sig_section_y + 15.5, "VERIFIED SECURITY SIGNATURE SEAL - 44TH BATTLE GROUP LOGISTICS")

    # â•â•â•â•â•â• PAGE 3: FULL-SIZE 3D ISOMETRIC CARGO GRID â•â•â•â•â•â•
    if ship_grid and "groups" in ship_grid and "PUBLIC" not in sec and "OPEN" not in sec:
        try:
            from cargo_grid_renderer import render_full_grid_page
            from storall_packer import calculate_cargo_breakdown

            # Build items list from manifest
            items_list = getattr(self, "manifest_items", [])
            bd_items = []
            for item in items_list:
                if isinstance(item, dict):
                    entry = {
                        "name": item.get("name", ""),
                        "qty": int(float(item.get("qty", 1))),
                    }
                    # Pass box_size so breakdown uses actual SCU (e.g. 24 SCU for torpedoes)
                    bs = str(item.get("box_size", "")).strip().upper()
                    if "SCU" in bs:
                        try:
                            scu_val = float(bs.replace("SCU", "").strip())
                            entry["vol_override"] = scu_val
                        except ValueError:
                            pass
                    bd_items.append(entry)

            breakdown = calculate_cargo_breakdown(bd_items)
            render_full_grid_page(
                pdf=self,
                ship_grid=ship_grid,
                breakdown=breakdown,
                vessel_name=self.vessel,
                security_level=sec,
            )
        except Exception as e:
            print(f"[Cargo Grid 3D] Error: {e}")
            import traceback; traceback.print_exc()

    # â”€â”€ AUTOBOX PACKING MANIFEST on page 2/3 (after cargo grid) â”€â”€
    autobox_data = getattr(self, '_autobox_data', None)
    if autobox_data and autobox_data.get("num_boxes", 0) > 0:
        lw, lh = self.w, self.h
        ab_y = lh - 65  # position near bottom of current page
        if ab_y < 50:
            self.add_page()
            ab_y = 20
        self.set_fill_color(15, 30, 60)
        self.rect(14, ab_y, 182, 7, 'F')
        self.set_font("Roboto", "B", 7)
        self.set_text_color(200, 168, 78)
        self.text(16, ab_y + 5, "LOGISTICS AUTO-BOXING PACKING MANIFEST")
        self.text(150, ab_y + 5, f"BOX: {autobox_data['box_label']}")

        # Column headers
        ab_y += 8
        self.set_fill_color(40, 48, 65)
        self.rect(14, ab_y, 182, 5, 'F')
        self.set_font("Roboto", "B", 5.5)
        self.set_text_color(180, 190, 210)
        self.text(16, ab_y + 3.5, "BOX #")
        self.text(36, ab_y + 3.5, "CONTENTS")
        self.text(155, ab_y + 3.5, "USED")
        self.text(175, ab_y + 3.5, "CAPACITY")
        ab_y += 5.5

        boxes = autobox_data["boxes"]
        box_vols = autobox_data["box_vols"]
        max_cap = autobox_data["max_capacity"]
        for idx, box in enumerate(boxes):
            if ab_y > lh - 12:
                break
            if idx % 2 == 0:
                self.set_fill_color(240, 242, 248)
            else:
                self.set_fill_color(248, 249, 253)
            self.rect(14, ab_y, 182, 5, 'F')

            self.set_font("Roboto", "B", 5.5)
            self.set_text_color(40, 50, 70)
            self.text(16, ab_y + 3.5, f"STOR-ALL #{idx+1}")

            self.set_font("Roboto", "", 5)
            self.set_text_color(60, 70, 90)
            items_str = ", ".join(f"{entry['qty']}x {entry['name']}" for entry in box)
            if len(items_str) > 90:
                items_str = items_str[:87] + "..."
            self.text(36, ab_y + 3.5, items_str)

            self.set_text_color(100, 80, 40)
            self.set_font("Roboto", "B", 5)
            self.text(155, ab_y + 3.5, f"{box_vols[idx]:.2f} SCU")
            self.text(175, ab_y + 3.5, f"{max_cap:.2f} SCU")
            ab_y += 5.5
        self._autobox_data = None



# Ä‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚Â
# SECTION 5: Resource Path + Font Cache
# Ä‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚Â

def resource_path_patched(relative_path):
    """Resolve resource paths via PATHS singleton."""
    return PATHS.resource(relative_path)

main.resource_path = resource_path_patched

# Apply logo search paths
local_logo = getattr(main, 'resource_path', lambda p: p)("logo.png")
local_logo_uee = getattr(main, 'resource_path', lambda p: p)("logo_uee44.png")
if os.path.exists(local_logo): main.LOGO_FILE = local_logo
if os.path.exists(local_logo_uee): main.LOGO_UEE_FILE = local_logo_uee

# Subclass FPDF templates to implement v0.6 features
OriginalMilitaryPDF = main.MilitaryPDF

# Pre-cache Roboto font data at module level (parse TTF once, reuse everywhere)
_FONT_CACHE = {}
def _precache_fonts():
    """Parse Roboto TTF files once and store font definitions for reuse.
    
    IMPORTANT: fpdf 1.7.2 generates .pkl cache files next to the .ttf files.
    These .pkl files contain the ABSOLUTE PATH from the machine where they were
    generated. If the installer ships pre-generated .pkl files from a different
    machine (e.g. C:\\Users\\tomas.foldyna\\...), they will cause a
    'No such file or directory' error on any other PC.
    
    Fix: Always delete stale .pkl files before calling add_font so that fpdf
    regenerates them with the correct local paths for the current machine.
    """
    import fpdf
    fonts_dir = getattr(main, 'resource_path', lambda p: p)('fonts')
    if not os.path.exists(fonts_dir):
        fonts_dir = getattr(main, 'resource_path', lambda p: p)('resources/fonts')
    reg_font = os.path.join(fonts_dir, "Roboto-Regular.ttf")
    bold_font = os.path.join(fonts_dir, "Roboto-Bold.ttf")

    # --- Delete stale .pkl files from any previous machine ---
    # This guarantees fpdf always regenerates them with the correct local paths.
    for pkl_name in ("Roboto-Regular.pkl", "Roboto-Regular.cw127.pkl",
                     "Roboto-Bold.pkl", "Roboto-Bold.cw127.pkl"):
        pkl_path = os.path.join(fonts_dir, pkl_name)
        try:
            if os.path.exists(pkl_path):
                os.remove(pkl_path)
        except Exception:
            pass  # Read-only filesystem edge case â€” silently ignore
    # ---------------------------------------------------------

    # Create a temporary PDF just to parse fonts once
    tmp = fpdf.FPDF()
    try:
        if os.path.exists(reg_font):
            tmp.add_font("Roboto", "", reg_font, uni=True)
            tmp.add_font("Roboto", "I", reg_font, uni=True)
        if os.path.exists(bold_font):
            tmp.add_font("Roboto", "B", bold_font, uni=True)
        # Store parsed font definitions
        for key, val in tmp.fonts.items():
            _FONT_CACHE[key] = val
    except Exception as e:
        print(f"[WARNING] Font pre-cache failed: {e}")

_precache_fonts()

# Ä‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚Â
# SECTION 6: PatchedMilitaryPDF Class
# Ä‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚Â

class PatchedMilitaryPDF(OriginalMilitaryPDF):
    def add_font(self, family, style='', fname='', uni=False):
        # fpdf2 >= 2.5.1 handles Unicode natively, uni param is deprecated
        try:
            super().add_font(family, style, fname)
        except Exception as e:
            # Font already added or file missing â€” skip silently
            if 'already added' not in str(e).lower():
                print(f"[Font] Warning: {e}")
    
    # Sanitize Unicode chars that cause font subsetting failures
    _UNICODE_MAP = str.maketrans({
        '\u25c9': '*', '\u26a0': '!', '\u2192': '>', 
        '\u25cf': '*', '\u25cb': 'o', '\u2022': '*',
    })
    
    def _sanitize(self, txt):
        if isinstance(txt, str):
            return txt.translate(self._UNICODE_MAP)
        return txt
    
    def cell(self, *args, **kwargs):
        if 'txt' in kwargs:
            kwargs['txt'] = self._sanitize(kwargs['txt'])
        elif len(args) >= 5:
            args = list(args)
            args[4] = self._sanitize(args[4])
        # Also handle 'text' kwarg (fpdf2 alias)
        if 'text' in kwargs:
            kwargs['text'] = self._sanitize(kwargs['text'])
        return super().cell(*args, **kwargs)
    
    def text(self, *args, **kwargs):
        if 'txt' in kwargs:
            kwargs['txt'] = self._sanitize(kwargs['txt'])
        elif len(args) >= 3:
            args = list(args)
            args[2] = self._sanitize(args[2])
        if 'text' in kwargs:
            kwargs['text'] = self._sanitize(kwargs['text'])
        return super().text(*args, **kwargs)
    
    def multi_cell(self, *args, **kwargs):
        if 'txt' in kwargs:
            kwargs['txt'] = self._sanitize(kwargs['txt'])
        elif len(args) >= 5:
            args = list(args)
            args[4] = self._sanitize(args[4])
        if 'text' in kwargs:
            kwargs['text'] = self._sanitize(kwargs['text'])
        return super().multi_cell(*args, **kwargs)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "font_family_name"):
            self.font_family_name = "Arial"
        self.original_rows = []
        if not hasattr(self, 'security_level'):
            self.security_level = 'ALL'
        # Note: _FONT_CACHE injection removed â€” corrupts font subsetting state
        # Register Roboto Italic/BoldItalic fallbacks (TTFs don't exist)
        try:
            import path_config
            font_dir = os.path.join(path_config.PATHS.app_root, 'fonts')
            regular = os.path.join(font_dir, 'Roboto-Regular.ttf')
            bold = os.path.join(font_dir, 'Roboto-Bold.ttf')
            if os.path.exists(regular):
                fontkey_i = 'roboto' + 'i'
                if fontkey_i not in self.fonts:
                    try: self.add_font('Roboto', 'I', regular)
                    except Exception: pass
                fontkey_bi = 'roboto' + 'bi'
                if fontkey_bi not in self.fonts:
                    try: self.add_font('Roboto', 'BI', bold if os.path.exists(bold) else regular)
                    except Exception: pass
        except Exception:
            pass

    def draw_table_row(self, pdf_row_index, name, box_size, qty, price, is_courtesy, total, unit, total_volume):
        # Force numeric types to avoid '>' str vs int errors in main.pyc
        try: qty = int(float(qty)) if not isinstance(qty, (int, float)) else qty
        except Exception: qty = 1
        try: price = float(price) if not isinstance(price, (int, float)) else price
        except Exception: price = 0.0
        try: total = float(total) if not isinstance(total, (int, float)) else total
        except Exception: total = 0.0
        try: total_volume = float(total_volume) if not isinstance(total_volume, (int, float)) else total_volume
        except Exception: total_volume = 0.0
        self.original_rows.append({
            'pdf_row_index': pdf_row_index,
            'name': str(name),
            'box_size': str(box_size),
            'qty': int(qty),
            'price': float(price),
            'is_courtesy': bool(is_courtesy),
            'unit': str(unit),
            'total_volume': float(total_volume)
        })

    def draw_table_footer(self, grand_total):
        official_uniforms = [
            "tcs-4 undersuit", "tcs-4 undersuit black", "tcs-4 undersuit black/grey",
            "tailwind flight suit", "tailwind helmet",
            "omni-afs sapphire slate", "omni-afs sapphire slate helmet",
            "adp-mk4 helmet woodland", "adp-mk4 core woodland", "adp-mk4 arms woodland", "adp-mk4 legs woodland", "csp-68h backpack",
            "orc-mkx helmet woodland", "orc-mkx core woodland", "orc-mkx arms woodland", "orc-mkx legs woodland", "csp-68m backpack",
            "field recon suit helmet", "field recon suit core", "field recon suit arms", "field recon suit legs", "csp-68l backpack",
            "aril helmet", "aril core", "aril arms", "aril legs", "aril backpack",
            "adiva jacket blue", "adiva jacket dark green", "adiva jacket imperial", "adiva jacket red", "adiva jacket white", "adiva jacket yellow",
            "lemarque pants", "deo black shirt", "prim black shoes", "ventra gloves black"
        ]
        official_weapons = [
            "fs-9 lmg", "fs-9 magazine",
            "p4-ar \"nightstalker\" rifle", "p4-ar rifle", "p4-ar magazine",
            "f55 lmg", "f55 lmg magazine",
            "p8-ar rifle", "p8-ar magazine",
            "p6-lr sniper rifle", "p6-lr magazine",
            "br2 shotgun", "br2 magazine",
            "p8-sc smg", "p8-sc magazine",
            "s-38 pistol", "s-38 magazine"
        ]
        
        for r in self.original_rows:
            name_low = r['name'].lower().strip()
            is_uniform = any(w in name_low for w in ["suit", "helmet", "core", "arms", "legs", "backpack", "jacket", "pants", "shirt", "shoes", "gloves"])
            is_weapon = any(w in name_low for w in ["rifle", "pistol", "smg", "lmg", "shotgun", "sniper", "magazine", "cq7", "coda"])
            
            if is_uniform:
                if name_low not in official_uniforms:
                    r['name'] = r['name'] + " [UNOFFICIAL EQ]"
            elif is_weapon:
                clean_name = name_low.replace('"', '').strip()
                clean_official = [w.replace('"', '').strip() for w in official_weapons]
                if clean_name not in clean_official:
                    r['name'] = r['name'] + " [UNOFFICIAL EQ]"

        # â”€â”€ Auto-boxing: ONLY for items that are truly loose (unit box_size) â”€â”€
        # Skip items that already have a Stor-All / SCU box_size assigned
        total_loose_vol = 0.0
        has_existing_storall = any('stor' in r['name'].lower() for r in self.original_rows)
        for r in self.original_rows:
            name_low = r['name'].lower()
            box_low = r['box_size'].lower()
            # Skip if already in SCU-sized container (not loose)
            if 'scu' in box_low:
                continue
            # Skip if this IS a Stor-All container row
            if 'stor' in name_low:
                continue
            qty = int(r['qty']) if isinstance(r['qty'], (int, float)) or (isinstance(r['qty'], str) and r['qty'].isdigit()) else 1
            
            unit_vol = 0.0
            is_loose = False
            for k, vol in volume_map.items():
                if k in name_low:
                    unit_vol = vol
                    is_loose = True
                    break
                    
            if is_loose or 'unit' in box_low:
                if any(x in name_low for x in ['missile', 'torpedo', 'bomb', 'seeker', 'colossus', 'stormburst']):
                    continue
                if unit_vol == 0.0:
                    unit_vol = 0.005
                total_loose_vol += qty * unit_vol
                
        # Only add auto-boxes if there are loose items AND no existing Stor-All in cargo
        boxes_to_add = []
        if total_loose_vol > 0.001 and not has_existing_storall:
            remaining = total_loose_vol
            STOR_PRICES = {'1 SCU': 1500, '2 SCU': 2800, '4 SCU': 5200, '8 SCU': 9500}
            if remaining <= 1.0:
                boxes_to_add.append(('Stor-All 1 SCU Storage Container', '1 SCU', 1.0))
            elif remaining <= 2.0:
                boxes_to_add.append(('Stor*All 2 SCU Self-Storage Container', '2 SCU', 2.0))
            elif remaining <= 4.0:
                boxes_to_add.append(('Stor*All 4 SCU Self-Storage Container', '4 SCU', 4.0))
            elif remaining <= 8.0:
                boxes_to_add.append(('Stor*All 8 SCU Self-Storage Container', '8 SCU', 8.0))
            else:
                full_8 = int(remaining // 8)
                for _ in range(min(full_8, 2)):
                    boxes_to_add.append(('Stor*All 8 SCU Self-Storage Container', '8 SCU', 8.0))
                leftover = remaining - full_8 * 8
                if leftover > 4.0:
                    boxes_to_add.append(('Stor*All 8 SCU Self-Storage Container', '8 SCU', 8.0))
                elif leftover > 2.0:
                    boxes_to_add.append(('Stor*All 4 SCU Self-Storage Container', '4 SCU', 4.0))
                elif leftover > 1.0:
                    boxes_to_add.append(('Stor*All 2 SCU Self-Storage Container', '2 SCU', 2.0))
                elif leftover > 0.01:
                    boxes_to_add.append(('Stor-All 1 SCU Storage Container', '1 SCU', 1.0))

            for name, box_size, total_vol in boxes_to_add:
                box_price = STOR_PRICES.get(box_size, 1500)
                self.original_rows.append({
                    'pdf_row_index': len(self.original_rows) + 1,
                    'name': name,
                    'box_size': box_size,
                    'qty': '1',
                    'price': box_price,
                    'is_courtesy': False,
                    'unit': 'SCU',
                    'total_volume': total_vol
                })
        self._stor_all_boxes = boxes_to_add
            
        self.manifest_items = []
        for idx, r in enumerate(self.original_rows):
            self.manifest_items.append({
                'name': r['name'],
                'qty': r['qty'],
                'box_size': r['box_size'],
                'total_volume': r['total_volume']
            })
            row_total = float(r['price']) * (int(r['qty']) if str(r['qty']).isdigit() else 1)
            # For loose items (unit), show "LOOSE" instead of "1 unit" in container size
            display_box_size = str(r['box_size'])
            if 'unit' in display_box_size.lower():
                display_box_size = 'LOOSE'
            super().draw_table_row(
                idx + 1,
                str(r['name']),
                display_box_size,
                int(r['qty']),
                float(r['price']),
                bool(r['is_courtesy']),
                float(row_total),
                str(r['unit']),
                float(r['total_volume'])
            )
            
        super().draw_table_footer(grand_total)

    def cell(self, w, h, txt='', border=0, ln=0, align='', fill=False, link=''):
        sec = self.security_level.upper() if hasattr(self, 'security_level') else ''
        redacted = False
        txt_clean = txt.strip().upper() if txt else ''
        
        # ALL / CLASSIFIED = NO redaction Ă˘â‚¬â€ť everything visible
        if 'ALL' in sec or 'CLASSIFIED' in sec or 'OFFICERS' in sec or 'ENCRYPTED' in sec:
            pass  # No redaction
        
        
        # PUBLIC: redact ~90% (names, all prices, totals, locations)
        elif 'PUBLIC' in sec or 'OPEN' in sec:
            # Names
            if self.captain and self.captain.strip() and self.captain.upper() in txt_clean: redacted = True
            elif self.loading_officer and self.loading_officer.strip() and self.loading_officer.upper() in txt_clean: redacted = True
            elif self.loading_crew and self.loading_crew.strip() and self.loading_crew.upper() in txt_clean: redacted = True
            # All price columns
            if w == 26 and h == 7 and txt_clean and txt_clean != "UNIT AUEC": redacted = True
            if w == 30 and h == 7 and txt_clean and txt_clean != "TOTAL AUEC  ": redacted = True
            # Any aUEC value
            if 'AUEC' in txt_clean or 'TOTAL' in txt_clean:
                if 'UNIT' not in txt_clean and 'MANIFEST' not in txt_clean and 'CLASSIFICATION' not in txt_clean:
                    redacted = True
        
        # SECURED/RESTRICTED: redact names only
        elif 'RESTRICTED' in sec or 'SECURED' in sec:
            if self.captain and self.captain.strip() and self.captain.upper() in txt_clean: redacted = True
            elif self.loading_officer and self.loading_officer.strip() and self.loading_officer.upper() in txt_clean: redacted = True
            elif self.loading_crew and self.loading_crew.strip() and self.loading_crew.upper() in txt_clean: redacted = True
        
        if redacted:
            x = self.get_x()
            y = self.get_y()
            self.set_fill_color(0, 0, 0)
            rect_w = w if w > 0 else self.get_string_width(txt)
            self.rect(x, y + 1, rect_w, h - 2, 'F')
            return super().cell(w, h, '', border, ln, align, False, link)
        else:
            return super().cell(w, h, txt, border, ln, align, fill, link)

    def text(self, x, y, txt=''):
        sec = self.security_level.upper() if hasattr(self, 'security_level') else ''
        redacted = False
        txt_clean = txt.strip().upper() if txt else ''
        
        # ALL / CLASSIFIED (OFFICERS) = NO redaction
        if 'ALL' in sec or 'CLASSIFIED' in sec or 'OFFICERS' in sec or 'ENCRYPTED' in sec:
            pass
        
        # PUBLIC: redact names + prices
        elif 'PUBLIC' in sec or 'OPEN' in sec or 'RESTRICTED' in sec or 'SECURED' in sec:
            if self.captain and self.captain.strip() and self.captain.upper() in txt_clean: redacted = True
            elif self.loading_officer and self.loading_officer.strip() and self.loading_officer.upper() in txt_clean: redacted = True
            elif self.loading_crew and self.loading_crew.strip() and self.loading_crew.upper() in txt_clean: redacted = True
        
        if redacted:
            w = self.get_string_width(txt)
            self.set_fill_color(0, 0, 0)
            self.rect(x, y - 3, w, 4, 'F')
        else:
            super().text(x, y, txt)

    def draw_redacted_text(self, text, start_x, start_y, width, height, line_height):
        pass

    draw_signatures = draw_signatures
    draw_report_paragraph = draw_report_paragraph

    def header(self):
        # WHITE background + navy header bar
        self.set_fill_color(255, 255, 255)
        self.rect(0, 0, 210, 297, 'F')
        self.set_fill_color(15, 30, 60)
        self.rect(8, 6, 194, 22, 'F')
        self.set_draw_color(180, 150, 60)
        self.set_line_width(0.5)
        self.line(8, 28, 202, 28)
        bg44_logo = PATHS.resource("cvbg44_logo_dark.png")
        if not os.path.exists(bg44_logo):
            bg44_logo = PATHS.resource("cvbg44_logo.png")
        if os.path.exists(bg44_logo):
            try: self.image(bg44_logo, x=11, y=7, w=18, h=18)
            except Exception: pass
        # SLS29 (Starlifter) logo on right side
        sls29_logo = PATHS.resource("sls29_logo.png")
        if os.path.exists(sls29_logo):
            try: self.image(sls29_logo, x=183, y=7, w=18, h=18)
            except Exception: pass
        try: self.set_font("Roboto", "B", 12)
        except Exception: self.set_font("Helvetica", "B", 12)
        self.set_text_color(255, 255, 255)
        super().text(32, 16, "44th BATTLEGROUP // CARGO MANIFEST")
        try: self.set_font("Roboto", "", 7)
        except Exception: self.set_font("Helvetica", "", 7)
        self.set_text_color(180, 190, 210)
        super().text(32, 22, "UEE FLEET LOGISTICS COMMAND // REQUISITION DOCUMENT")
        podpisy_dir = get_signatures_dir()
        barcode_file = get_processed_barcode_path(podpisy_dir)
        if barcode_file and os.path.exists(barcode_file):
            self.image(barcode_file, x=145, y=29, w=45, h=8)
        _header_rng = random.Random(getattr(self, 'incident_seed', 42))
        hid = f"{_header_rng.choice(['REQ','SEC','LOG','TAC','NAV'])}-{_header_rng.choice(['44BG','UEE-9N','FLEET-44'])}-{_header_rng.randint(10000,99999)}-{_header_rng.choice(['ALPHA','BRAVO','X-RAY','OMEGA'])}"
        try: self.set_font("Roboto", "B", 5)
        except Exception: self.set_font("Helvetica", "B", 5)
        self.set_text_color(100, 116, 139)
        super().text(10, 38, f"LEDGER HASH: {hid}")

        # Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬ Classification Badge (colored pill) Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬
        sec = self.security_level.upper() if hasattr(self, 'security_level') else ""
        # Map exact classification to badge
        badge_text = sec.replace("_", " ") if sec else "CLASSIFIED"
        badge_r, badge_g, badge_b = 180, 30, 30  # Red default
        if not sec or sec == "ALL":
            badge_text = "INACTIVE CHANNEL"
            badge_r, badge_g, badge_b = 30, 30, 30  # Black
        elif "OFFICERS" in sec or "ENCRYPTED" in sec:
            badge_text = "OFFICERS ONLY"
            badge_r, badge_g, badge_b = 180, 30, 30  # Red
        elif "PUBLIC" in sec or "OPEN" in sec:
            badge_text = "OPEN TO PUBLIC"
            badge_r, badge_g, badge_b = 40, 140, 60  # Green
        elif "RESTRICTED" in sec or "SECURED" in sec:
            badge_text = "SECURED MEMBERS"
            badge_r, badge_g, badge_b = 200, 150, 30  # Amber
        
        badge_w = self.get_string_width(badge_text) + 8
        self.set_fill_color(badge_r, badge_g, badge_b)
        self.rect(10, 29.5, badge_w, 5, 'F')
        self.set_text_color(255, 255, 255)
        try: self.set_font("Roboto", "B", 6)
        except Exception: self.set_font("Helvetica", "B", 6)
        super().text(14, 33, badge_text)
        # PNG watermark overlay â€” each classification has its own image
        watermark_map = {
            "OPEN_PUBLIC": "watermark_public.png",
            "OPEN PUBLIC": "watermark_public.png",
            "PUBLIC": "watermark_public.png",
            "RESTRICTED": "watermark_secured.png",
            "SECURED": "watermark_secured.png",
            "OFFICERS_ONLY_ENCRYPTED": "watermark_classified.png",
            "CLASSIFIED": "watermark_classified.png",
        }
        wm_file = None
        for key, fname in watermark_map.items():
            if key in sec:
                wm_file = fname
                break
        if wm_file:
            wm_path = PATHS.resource(wm_file)
            if os.path.exists(wm_path):
                try:
                    page_w = self.w
                    page_h = self.h
                    wm_w = page_w * 0.7
                    wm_x = (page_w - wm_w) / 2
                    wm_y = page_h * 0.25
                    self.image(wm_path, x=wm_x, y=wm_y, w=wm_w)
                except Exception as e:
                    print(f"[Watermark] {e}")
        # Reset
        self.set_text_color(0, 0, 0)

        # â”€â”€ METADATA ROWS: each field on its own line for readability â”€â”€
        # Collect metadata
        req_id = getattr(self, 'req_id', '') or ''
        date_str = getattr(self, 'delivery_date', '') or ''
        vessel = getattr(self, 'vessel', '') or ''
        officer = getattr(self, 'loading_officer', '') or ''
        crew = getattr(self, 'loading_crew', '') or ''
        captain = getattr(self, 'captain', '') or ''
        station = getattr(self, 'location', '') or ''
        severity = getattr(self, 'severity', '') or ''
        loading_type = getattr(self, 'loading_type', '') or ''

        try: self.set_font("Roboto", "", 5)
        except Exception: self.set_font("Helvetica", "", 5)
        self.set_text_color(80, 90, 110)

        # Metadata positioned right of badge
        meta_x = badge_w + 16
        meta_y = 30.5
        line_h = 3.0

        # Row 1: VESSEL | STATION
        r1_parts = []
        if vessel:
            r1_parts.append(f"VESSEL: {vessel}")
        if station:
            ltype = f" ({loading_type})" if loading_type else ""
            r1_parts.append(f"STATION: {station}{ltype}")
        if r1_parts:
            super().text(meta_x, meta_y, "  |  ".join(r1_parts))

        # Row 2: OFFICER | CAPTAIN | SEVERITY
        meta_y2 = meta_y + line_h
        r2_parts = []
        if officer:
            r2_parts.append(f"OFFICER: {officer}")
        if captain and captain.strip():
            r2_parts.append(f"CAPTAIN: {captain}")
        if severity:
            r2_parts.append(f"SEVERITY: {severity}")
        if r2_parts:
            super().text(meta_x, meta_y2, "  |  ".join(r2_parts))

        # Row 3: CREW | DATE
        meta_y3 = meta_y2 + line_h
        r3_parts = []
        if crew and crew.strip().upper() not in ["NONE", "PENDING", ""]:
            r3_parts.append(f"CREW: {crew}")
        if date_str:
            r3_parts.append(f"DELIVERY DATE: {date_str}")
        if r3_parts:
            super().text(meta_x, meta_y3, "  |  ".join(r3_parts))

        # Set Y cursor below header so content doesn't overlap
        self.set_y(46)

main.MilitaryPDF = PatchedMilitaryPDF

# Ä‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚Â
# SECTION 7: Direct Supply Route PDF Generator
# Ä‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚ÂÄ‚ËĂ˘â‚¬ËĂ‚Â

def generate_pdf_direct(self, save_path=None):
    """Generate Supply Route PDF directly using fpdf. Instant, no main.pyc."""
    import fpdf
    from tkinter import filedialog
    
    _ensure_trade_dbs()  # Lazy-load trade databases
    # Rebind after lazy-load (from-import copies reference at import time)
    import uex_sync as _uex
    _uex_trade_db_local = _uex._uex_trade_db or {}
    _uex_items_trade_db_local = _uex._uex_items_trade_db or {}
    
    # Collect items from cargo table
    items = []
    for row in self.cargo_rows:
        name = row['name_var'].get().strip()
        qty_str = row['qty_var'].get().strip()
        unit = row.get('unit', 'unit')
        box_size = row['box_size_var'].get().strip() if 'box_size_var' in row else '1 SCU'
        price_str = row.get('price_var', None)
        if price_str and hasattr(price_str, 'get'):
            price_str = price_str.get().strip()
        else:
            price_str = '0'
        courtesy = row.get('courtesy_var', None)
        is_courtesy = False
        if courtesy and hasattr(courtesy, 'get'):
            is_courtesy = bool(courtesy.get())
        
        if not name or not qty_str or qty_str == '?':
            continue
        try:
            qty = int(float(qty_str))
            if qty <= 0: continue
        except ValueError:
            continue
        try:
            price = float(price_str.replace(',', '').replace(' ', '')) if price_str else 0
        except Exception:
            price = 0
        
        items.append({
            'name': name, 'qty': qty, 'unit': unit,
            'box_size': box_size, 'price': price, 'is_courtesy': is_courtesy
        })
    
    if not items:
        messagebox.showerror("Error", "Cargo table is empty!")
        return
    
    # â”€â”€ Auto-boxing: calculate Stor-All boxes for loose items â”€â”€
    total_loose_vol = 0.0
    has_existing_storall = any('stor' in item['name'].lower() for item in items)
    for item in items:
        name_low = item['name'].lower()
        box_low = item['box_size'].lower()
        # Skip items already in SCU containers
        if 'scu' in box_low:
            continue
        # Skip Stor-All container rows
        if 'stor' in name_low:
            continue
        unit_vol = 0.0
        is_loose = False
        for k, vol in volume_map.items():
            if k in name_low:
                unit_vol = vol
                is_loose = True
                break
        if is_loose or 'unit' in box_low:
            if any(x in name_low for x in ["missile", "torpedo", "bomb", "seeker", "colossus", "stormburst"]):
                continue
            if unit_vol == 0.0:
                unit_vol = 0.005
            total_loose_vol += item['qty'] * unit_vol
    
    boxes_to_add = []
    if total_loose_vol > 0.001 and not has_existing_storall:
        remaining = total_loose_vol
        while remaining > 0.0001:
            if remaining > 4.0:
                boxes_to_add.append(("Stor*All 8 SCU Self-Storage Container", "8 SCU"))
                remaining -= 8.0
            elif remaining > 2.0:
                boxes_to_add.append(("Stor*All 4 SCU Self-Storage Container", "4 SCU"))
                remaining -= 4.0
            elif remaining > 1.0:
                boxes_to_add.append(("Stor*All 2 SCU Self-Storage Container", "2 SCU"))
                remaining -= 2.0
            else:
                boxes_to_add.append(("Stor-All 1 SCU Storage Container", "1 SCU"))
                remaining -= 1.0
    
    for box_name, box_size in boxes_to_add:
        items.append({
            'name': box_name, 'qty': 1, 'unit': 'SCU',
            'box_size': box_size, 'price': 0, 'is_courtesy': True
        })
    
    # Calculate cargo breakdown using storall_packer
    bd_items = [{"name": i["name"], "qty": i["qty"]} for i in items]
    cargo_breakdown = calculate_cargo_breakdown(bd_items)
    
    # Get classification for filename
    classification_pre = self._classify_var.get() if hasattr(self, '_classify_var') else 'ALL'
    req_id_pre = self.req_id_var.get() if hasattr(self, 'req_id_var') else 'SR'
    safe_req = req_id_pre.replace(' ', '_').replace('/', '-')[:30]
    default_fn = f"{safe_req}_supply_route.pdf"
    
    if not save_path:
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_fn,
            title="Save Supply Route PDF"
        )
    if not save_path:
        return
    
    # Gather metadata
    req_id = self.req_id_var.get() if hasattr(self, 'req_id_var') else 'N/A'
    vessel = self.ship_selector.get() if hasattr(self, 'ship_selector') else ''
    officer = self.loading_officer_var.get() if hasattr(self, 'loading_officer_var') else ''
    captain = self.captain_var.get() if hasattr(self, 'captain_var') else ''
    crew = self.loading_crew_var.get() if hasattr(self, 'loading_crew_var') else ''
    location = self.location_var.get() if hasattr(self, 'location_var') else ''
    classification = self._classify_var.get() if hasattr(self, '_classify_var') else 'ALL'
    severity = self.severity_var.get() if hasattr(self, 'severity_var') else 'NOMINAL'
    delivery = self.delivery_date_var.get() if hasattr(self, 'delivery_date_var') else ''
    mission = self.mission_var.get() if hasattr(self, 'mission_var') else ''
    
    # Build PDF
    pdf = fpdf.FPDF('P', 'mm', 'A4')
    pdf.set_auto_page_break(auto=False)
    
    # Note: _FONT_CACHE injection disabled â€” fpdf2 font subsetting 
    # breaks when sharing font objects between instances.
    
    pdf.add_page()
    
    # â”€â”€ PAGE BACKGROUND (white, same as manifest) â”€â”€
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, 210, 297, 'F')
    
    # â”€â”€ HEADER (military style, same as manifest) â”€â”€
    pdf.set_fill_color(15, 30, 60)
    pdf.rect(8, 6, 194, 22, 'F')
    pdf.set_draw_color(180, 150, 60)
    pdf.set_line_width(0.5)
    pdf.line(8, 28, 202, 28)
    
    # CVBG44 logo left
    bg44_logo = PATHS.resource("cvbg44_logo_dark.png")
    if not os.path.exists(bg44_logo):
        bg44_logo = PATHS.resource("cvbg44_logo.png")
    if os.path.exists(bg44_logo):
        try: pdf.image(bg44_logo, x=11, y=7, w=18, h=18)
        except Exception: pass
    # SLS29 logo right
    sls29_logo = PATHS.resource("sls29_logo.png")
    if os.path.exists(sls29_logo):
        try: pdf.image(sls29_logo, x=183, y=7, w=18, h=18)
        except Exception: pass
    
    # Title
    try: pdf.set_font("Roboto", "B", 12)
    except Exception: pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 255, 255)
    pdf.text(32, 16, "44th BATTLEGROUP // SUPPLY ROUTE")
    try: pdf.set_font("Roboto", "", 7)
    except Exception: pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(180, 190, 210)
    pdf.text(32, 22, "UEE FLEET LOGISTICS COMMAND // SUPPLY ROUTE MANIFEST")
    
    # Barcode
    podpisy_dir = get_signatures_dir()
    barcode_file = get_processed_barcode_path(podpisy_dir)
    if barcode_file and os.path.exists(barcode_file):
        pdf.image(barcode_file, x=145, y=29, w=45, h=8)
    
    # Ledger hash
    import random as _sr_rng_mod
    _sr_rng = _sr_rng_mod.Random(hash(req_id) if req_id else 42)
    sr_hid = f"{_sr_rng.choice(['REQ','SEC','LOG','TAC','NAV'])}-{_sr_rng.choice(['44BG','UEE-9N','FLEET-44'])}-{_sr_rng.randint(10000,99999)}-{_sr_rng.choice(['ALPHA','BRAVO','X-RAY','OMEGA'])}"
    try: pdf.set_font("Roboto", "B", 5)
    except Exception: pdf.set_font("Helvetica", "B", 5)
    pdf.set_text_color(100, 116, 139)
    pdf.text(10, 38, f"LEDGER HASH: {sr_hid}")
    
    # Classification badge
    sec_upper = classification.upper()
    badge_text = "CLASSIFIED"
    badge_r, badge_g, badge_b = 180, 30, 30
    if sec_upper == "ALL" or not sec_upper:
        badge_text = "INACTIVE CHANNEL"
        badge_r, badge_g, badge_b = 30, 30, 30
    elif sec_upper == "CLASSIFIED":
        badge_text = "OFFICERS ONLY"
        badge_r, badge_g, badge_b = 180, 30, 30
    elif sec_upper == "PUBLIC":
        badge_text = "OPEN TO PUBLIC"
        badge_r, badge_g, badge_b = 40, 140, 60
    elif sec_upper == "SECURED":
        badge_text = "SECURED MEMBERS"
        badge_r, badge_g, badge_b = 200, 150, 30
    
    badge_w = pdf.get_string_width(badge_text) + 8
    pdf.set_fill_color(badge_r, badge_g, badge_b)
    pdf.rect(10, 29.5, badge_w, 5, 'F')
    pdf.set_text_color(255, 255, 255)
    try: pdf.set_font("Roboto", "B", 6)
    except Exception: pdf.set_font("Helvetica", "B", 6)
    pdf.text(14, 33, badge_text)
    
    # Watermark overlay
    _sr_wm_map = {"PUBLIC": "watermark_public.png", "SECURED": "watermark_secured.png", "CLASSIFIED": "watermark_classified.png"}
    _sr_wm_file = _sr_wm_map.get(sec_upper)
    if _sr_wm_file:
        _sr_wm_path = PATHS.resource(_sr_wm_file)
        if os.path.exists(_sr_wm_path):
            try:
                _sr_wm_w = 210 * 0.7
                pdf.image(_sr_wm_path, x=(210 - _sr_wm_w) / 2, y=297 * 0.25, w=_sr_wm_w)
            except Exception: pass
    
    # â”€â”€ METADATA ROWS (compact, same as manifest) â”€â”€
    try: pdf.set_font("Roboto", "", 5)
    except Exception: pdf.set_font("Helvetica", "", 5)
    pdf.set_text_color(80, 90, 110)
    
    meta_x = badge_w + 16
    meta_y = 30.5
    line_h = 3.0
    
    loading_type = self.loading_type_var.get() if hasattr(self, 'loading_type_var') else ''
    
    # Row 1: VESSEL | STATION
    r1_parts = []
    if vessel: r1_parts.append(f"VESSEL: {vessel}")
    if location:
        ltype = f" ({loading_type})" if loading_type else ""
        r1_parts.append(f"STATION: {location}{ltype}")
    if r1_parts:
        pdf.text(meta_x, meta_y, "  |  ".join(r1_parts))
    
    # Row 2: OFFICER | CAPTAIN | SEVERITY
    r2_parts = []
    if officer: r2_parts.append(f"OFFICER: {officer}")
    if captain and captain.strip(): r2_parts.append(f"CAPTAIN: {captain}")
    if severity: r2_parts.append(f"SEVERITY: {severity}")
    if r2_parts:
        pdf.text(meta_x, meta_y + line_h, "  |  ".join(r2_parts))
    
    # Row 3: CREW | DATE | REQ
    r3_parts = []
    if crew and crew.strip().upper() not in ["NONE", "PENDING", ""]:
        r3_parts.append(f"CREW: {crew}")
    if delivery: r3_parts.append(f"DELIVERY DATE: {delivery}")
    if req_id: r3_parts.append(f"REQ: {req_id}")
    if r3_parts:
        pdf.text(meta_x, meta_y + line_h * 2, "  |  ".join(r3_parts))
    
    # â”€â”€ PROCUREMENT ROUTE (rendered before cargo table) â”€â”€
    table_y = 46
    
    # Build procurement data: find where to buy each item
    # Determine loading location's system + planet for proximity sorting
    loading_planet = ""
    loading_system = "stanton"
    loading_loc = location.lower().strip()
    for cat_locs in _uex_locations_db.values():
        if isinstance(cat_locs, dict):
            for loc_name, loc_info in cat_locs.items():
                if loc_name.lower() in loading_loc or loading_loc in loc_name.lower():
                    loading_planet = (loc_info.get("planet") or "").lower()
                    loading_system = (loc_info.get("system") or "stanton").lower()
                    break
        if loading_planet:
            break
    
    # Realistic QT distances in minutes between planets/moons within Stanton
    # Same planet = 0, nearby = actual QT time in minutes
    _STANTON_QT_MINS = {
        ("hurston", "arccorp"): 6,
        ("hurston", "crusader"): 8,
        ("hurston", "microtech"): 14,
        ("arccorp", "crusader"): 5,
        ("arccorp", "microtech"): 11,
        ("crusader", "microtech"): 9,
    }
    # Pyro internal distances (all roughly 5-10 min)
    # Cross-system penalty: Stantonâ†”Pyro = 50 min (wormhole), Stantonâ†”Nyx = 80 min, Pyroâ†”Nyx = 40 min
    _SYSTEM_JUMP_PENALTY = {
        ("stanton", "pyro"): 50,
        ("stanton", "nyx"): 80,
        ("pyro", "nyx"): 40,
    }
    
    def _get_terminal_info(terminal_name):
        """Get (system, planet) for a terminal name from locations DB."""
        tn = terminal_name.lower()
        for cat_locs in _uex_locations_db.values():
            if isinstance(cat_locs, dict):
                for loc_name, loc_info in cat_locs.items():
                    if loc_name.lower() in tn or tn in loc_name.lower():
                        sys = (loc_info.get("system") or "stanton").lower()
                        pla = (loc_info.get("planet") or "").lower()
                        return sys, pla
        # Guess from name prefixes
        if "arc-l" in tn or "area 18" in tn or "area18" in tn: return "stanton", "arccorp"
        if "cru-l" in tn or "orison" in tn or "port olisar" in tn: return "stanton", "crusader"
        if "hur-l" in tn or "lorville" in tn or "everus" in tn: return "stanton", "hurston"
        if "mic-l" in tn or "new babbage" in tn or "port tressler" in tn: return "stanton", "microtech"
        if "levski" in tn: return "nyx", "delamar"
        if "ruin" in tn or "checkmate" in tn or "pyro" in tn: return "pyro", ""
        return "stanton", ""
    
    def _qt_distance(terminal_name):
        """Estimated QT travel time in minutes from loading location. Lower = closer."""
        t_sys, t_pla = _get_terminal_info(terminal_name)
        
        # Cross-system jump penalty
        if t_sys != loading_system:
            pair = tuple(sorted([loading_system, t_sys]))
            penalty = _SYSTEM_JUMP_PENALTY.get(pair, 100)
            return penalty  # wormhole jump + internal travel
        
        # Same system
        if not t_pla or not loading_planet:
            return 15  # unknown planet within same system
        if t_pla == loading_planet:
            return 0  # same planet / orbital station
        
        # Known intra-system distances
        pair = tuple(sorted([loading_planet, t_pla]))
        return _STANTON_QT_MINS.get(pair, 12)  # default ~12 min if unknown
    
    def _enrich_location(terminal_name):
        """Format location as 'System > Planet > Location'."""
        tn = terminal_name.lower()
        for cat_locs in _uex_locations_db.values():
            if isinstance(cat_locs, dict):
                for loc_name, loc_info in cat_locs.items():
                    if loc_name.lower() == tn or tn in loc_name.lower() or loc_name.lower() in tn:
                        system = loc_info.get("system", "Stanton")
                        planet = loc_info.get("planet", "")
                        if planet:
                            return f"{system} > {planet} > {loc_name}"
                        return f"{system} > {loc_name}"
        # Fallback: guess from name
        if "arc-l" in tn or "area" in tn: return f"Stanton > ArcCorp > {terminal_name}"
        if "cru-l" in tn or "orison" in tn: return f"Stanton > Crusader > {terminal_name}"
        if "hur-l" in tn or "lorville" in tn: return f"Stanton > Hurston > {terminal_name}"
        if "mic-l" in tn or "babbage" in tn: return f"Stanton > MicroTech > {terminal_name}"
        if "levski" in tn: return f"Nyx > Delamar > {terminal_name}"
        return terminal_name
    
    procurement = []
    has_loose_items = total_loose_vol > 0.0001 if 'total_loose_vol' in dir() else False
    
    for item in items:
        iname = item['name']
        iname_low = iname.lower().strip()
        best_loc = None
        best_price = None
        
        # Skip Stor-All boxes (auto-added)
        if 'stor' in iname_low and ('all' in iname_low or 'storage' in iname_low):
            has_loose_items = True
            continue
        
        # 1) Commodity trade DB â€” prefer nearby locations
        candidates = []
        for db_name, entries in _uex_trade_db_local.items():
            if db_name.lower() == iname_low or iname_low in db_name.lower() or db_name.lower() in iname_low:
                for e in entries:
                    if isinstance(e, dict) and e.get('buy', e.get('b', 0)) > 0:
                        loc = e.get('terminal', e.get('t', 'UNKNOWN'))
                        price = e.get('buy', e.get('b', 0))
                        dist = _qt_distance(loc)
                        candidates.append((dist, price, loc))
                break
        
        # 2) Items trade DB
        if not candidates and _uex_items_trade_db_local:
            for db_name, entries in _uex_items_trade_db_local.items():
                if db_name.lower() == iname_low or iname_low in db_name.lower() or db_name.lower() in iname_low:
                    for e in entries:
                        if isinstance(e, dict) and e.get('buy', e.get('b', 0)) > 0:
                            loc = e.get('terminal', e.get('t', 'UNKNOWN'))
                            price = e.get('buy', e.get('b', 0))
                            dist = _qt_distance(loc)
                            candidates.append((dist, price, loc))
                    break
        
        if candidates:
            # Sort by distance first, then price
            candidates.sort(key=lambda x: (x[0], x[1]))
            # Prefer same-system: if any candidate < 50 min, filter out wormhole ones
            same_sys = [c for c in candidates if c[0] < 50]
            if same_sys:
                candidates = same_sys
            best_loc = candidates[0][2]
            best_price = candidates[0][1]
        
        # 3) SC Wiki API cache â€” real item locations from star-citizen.wiki
        if not best_loc:
            try:
                from sc_wiki_db import get_best_buy_location
                wiki_result = get_best_buy_location(
                    iname, from_location=location or "",
                    from_system=loading_system or "stanton")
                if wiki_result:
                    best_loc = wiki_result["display"]
                    best_price = wiki_result["price"]
            except Exception:
                pass
        
        # 3b) Ship ammunition commodities → Admin offices (wiki-verified)
        if not best_loc:
            import re as _re_ammo
            _ammo_size_m = _re_ammo.search(r'size\s*(\d+)\s*ammunition', iname_low)
            if _ammo_size_m:
                # Wiki-verified prices per SCU (starcitizen.tools, July 2026)
                _ammo_prices = {
                    '1': 6868, '2': 7126, '3': 7384, '4': 7641, '5': 7985
                }
                _ammo_vendors = [
                    ('Admin', 'Seraphim Station'),
                    ('Admin', 'Port Tressler'),
                    ('Admin', 'Baijini Point'),
                    ('Admin', 'Everus Harbor'),
                    ('Admin', 'Lorville'),
                    ('Admin', 'GrimHEX'),
                    ('Admin', 'Orbituary'),
                    ('Admin', 'Gaslight'),
                    ('Admin', 'Checkmate'),
                    ('Admin', 'Ruin Station'),
                    ('Admin', 'Megumi Refueling'),
                ]
                best_vendor = None
                best_dist = 999
                for vendor, loc in _ammo_vendors:
                    d = _qt_distance(loc)
                    if d < best_dist:
                        best_dist = d
                        best_vendor = f"{vendor} ({loc})"
                if best_vendor:
                    best_loc = best_vendor
                _sz = _ammo_size_m.group(1)
                if _sz in _ammo_prices:
                    best_price = _ammo_prices[_sz]

        # 4) Ordnance fallback: known weapons/missile vendors
        if not best_loc:
            _ord_kw = ['missile', 'torpedo', 'bomb', 'ammunition', 'countermeasure',
                        'seeker', 'colossus',
                        'stormburst', 'vanquisher', 'thunderbolt', 'arrester',
                        'reaper', 'typhoon', 'argus', 'raptor', 'stalker',
                        'viper', 'spark', 'marksman', 'tempest', 'strikeforce',
                        'ignite', 'dominator', 'pioneer']
            if any(kw in iname_low for kw in _ord_kw):
                best_loc = 'Centermass'  # Primary weapons dealer
                # Pick closest known weapons shop
                _ord_vendors = [
                    ('Centermass', 'Area18'),
                    ('Centermass', 'New Babbage'),
                    ('Dumpers Depot', 'Port Olisar'),
                    ('Platinum Bay', 'Port Olisar'),
                ]
                best_vendor = None
                best_dist = 999
                for vendor, loc in _ord_vendors:
                    d = _qt_distance(loc)
                    if d < best_dist:
                        best_dist = d
                        best_vendor = f"{vendor} ({loc})"
                if best_vendor:
                    best_loc = best_vendor
        
        # General equipment fallback: weapons, tools, food, armor
        if not best_loc:
            _equip_map = {
                # Weapons & ammo â€” Centermass is primary weapons dealer
                'grenade': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'magazine': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'pistol': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'rifle': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'p4-ar': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'smg': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'shotgun': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'lmg': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'railgun': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'knife': [('Centermass', 'Area18'), ('Cubby Blast', 'New Babbage')],
                'mine': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'launcher': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'scorch': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                # Mining/tractor tools
                'tractor': [('Tammany and Sons', 'Lorville'), ('Shubin Interstellar', 'New Babbage')],
                'maxlift': [('Tammany and Sons', 'Lorville'), ('Shubin Interstellar', 'New Babbage')],
                'cambio': [('Tammany and Sons', 'Lorville'), ('Shubin Interstellar', 'New Babbage')],
                'multitool': [('Tammany and Sons', 'Lorville'), ('Shubin Interstellar', 'New Babbage')],
                'multi-tool': [('Tammany and Sons', 'Lorville'), ('Shubin Interstellar', 'New Babbage')],
                'mining': [('Shubin Interstellar', 'New Babbage'), ('Tammany and Sons', 'Lorville')],
                'fabricator': [('Tammany and Sons', 'Lorville'), ('Shubin Interstellar', 'New Babbage')],
                'flare': [('Tammany and Sons', 'Lorville'), ('Cubby Blast', 'Area18')],
                'extinguisher': [('Tammany and Sons', 'Lorville'), ('Admin Office', 'Port Olisar')],
                'canister': [('Tammany and Sons', 'Lorville'), ('Admin Office', 'Port Olisar')],
                'battery': [('Tammany and Sons', 'Lorville'), ('Admin Office', 'Port Olisar')],
                # Food & drinks & consumables
                'food': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'drink': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'lux': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'cruz': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'burrito': [('G-Loc Bar', 'Area18')],
                'bar': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'energy': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'fizzz': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'mug': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'veggie': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'snaggle': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'readymeal': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'meal': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'water bottle': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'chocolate': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'nutrition': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                'pips': [('G-Loc Bar', 'Area18'), ('Wally\'s Bar', 'Lorville')],
                # Medical â€” pens, devices, refills
                'medpen': [('Pharmacy', 'Area18'), ('Pharmacy', 'New Babbage')],
                'medkit': [('Pharmacy', 'Area18'), ('Pharmacy', 'New Babbage')],
                'pen': [('Pharmacy', 'Area18'), ('Pharmacy', 'New Babbage')],
                'paramed': [('Pharmacy', 'Area18'), ('Pharmacy', 'New Babbage')],
                'medical': [('Pharmacy', 'Area18'), ('Pharmacy', 'New Babbage')],
                'refill': [('Pharmacy', 'Area18'), ('Pharmacy', 'New Babbage')],
                # Armor & gear â€” full sets (helmet, core, arms, legs, backpack, undersuit)
                'armor': [('Cubby Blast', 'Area18'), ('Cubby Blast', 'New Babbage')],
                'helmet': [('Cubby Blast', 'Area18'), ('Cubby Blast', 'New Babbage')],
                'backpack': [('Cubby Blast', 'Area18'), ('Cubby Blast', 'New Babbage')],
                'undersuit': [('Cubby Blast', 'Area18'), ('Cubby Blast', 'New Babbage')],
                'arms': [('Cubby Blast', 'Area18'), ('Cubby Blast', 'New Babbage')],
                'legs': [('Cubby Blast', 'Area18'), ('Cubby Blast', 'New Babbage')],
                'core': [('Cubby Blast', 'Area18'), ('Cubby Blast', 'New Babbage')],
                'suit': [('Cubby Blast', 'Area18'), ('Cubby Blast', 'New Babbage')],
                'flight suit': [('Cubby Blast', 'Area18'), ('Cubby Blast', 'New Babbage')],
                # Clothing â€” Casaba Outlet
                'jacket': [('Casaba Outlet', 'Area18'), ('Casaba Outlet', 'New Babbage')],
                'pants': [('Casaba Outlet', 'Area18'), ('Casaba Outlet', 'New Babbage')],
                'shoes': [('Casaba Outlet', 'Area18'), ('Casaba Outlet', 'New Babbage')],
                'shirt': [('Casaba Outlet', 'Area18'), ('Casaba Outlet', 'New Babbage')],
                'gloves': [('Casaba Outlet', 'Area18'), ('Casaba Outlet', 'New Babbage')],
                # Refined materials â€” Refinery Decks
                'refined': [('Refinery Deck', 'ARC-L1'), ('Refinery Deck', 'CRU-L1')],
                'construction': [('Admin Office', 'Port Olisar'), ('TDD', 'Area18')],
                'rmc': [('TDD', 'Area18'), ('TDD', 'New Babbage')],
                'composite': [('TDD', 'Area18'), ('TDD', 'New Babbage')],
                # Fuel
                'fuel': [('Refueling Station', 'Port Olisar'), ('Refueling Station', 'Everus Harbor')],
                # Weapon optics & attachments
                'omni': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'scope': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'sight': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
                'attachment': [('Centermass', 'Area18'), ('Centermass', 'New Babbage')],
            }
            matched_vendors = None
            for kw, vendors in _equip_map.items():
                if kw in iname_low:
                    matched_vendors = vendors
                    break
            if matched_vendors:
                best_vendor = None
                best_dist = 999
                for vendor, loc in matched_vendors:
                    d = _qt_distance(loc)
                    if d < best_dist:
                        best_dist = d
                        best_vendor = f"{vendor} ({loc})"
                if best_vendor:
                    best_loc = best_vendor
        
        fallback_loc = 'STAGING AREA // CHECK ON-SITE'
        # Use enriched location for trade-DB results, plain string for vendor fallback
        if best_loc and '(' not in str(best_loc):
            display_loc = _enrich_location(best_loc)
            qt = _qt_distance(best_loc)
        elif best_loc:
            display_loc = best_loc
            qt = 5  # vendor fallback = close
        else:
            display_loc = fallback_loc
            qt = 99
        procurement.append({
            'name': iname, 'qty': item['qty'],
            'loc': display_loc,
            'price': best_price,
            'raw_loc': best_loc or '',
            'qt_min': qt,
        })
    
    if procurement:
        proc_y = table_y
        if proc_y > 230:
            pdf.add_page()
            pdf.set_fill_color(245, 238, 220)
            pdf.rect(0, 0, 210, 297, 'F')
            pdf.set_draw_color(180, 150, 60)
            pdf.set_line_width(1.5)
            pdf.rect(5, 5, 200, 287)
            pdf.set_line_width(0.3)
            pdf.rect(7, 7, 196, 283)
            proc_y = 15
        
        # Header
        pdf.set_fill_color(25, 32, 45)
        pdf.rect(10, proc_y, 190, 7, 'F')
        pdf.set_text_color(200, 168, 78)
        try: pdf.set_font("Roboto", "B", 7)
        except Exception: pdf.set_font("Helvetica", "B", 7)
        origin = location if location else "ORIGIN"
        pdf.text(12, proc_y + 5, f"PROCUREMENT ROUTE // FROM {origin[:30].upper()} (UEX PROXIMITY DATA)")
        
        try: pdf.set_font("Roboto", "", 5.5)
        except Exception: pdf.set_font("Helvetica", "", 5.5)
        
        py = proc_y + 9
        
        # Per-item procurement list
        for i, p in enumerate(procurement):
            if py > 250:
                pdf.add_page()
                pdf.set_fill_color(245, 238, 220)
                pdf.rect(0, 0, 210, 297, 'F')
                pdf.set_draw_color(180, 150, 60)
                pdf.set_line_width(1.5)
                pdf.rect(5, 5, 200, 287)
                pdf.set_line_width(0.3)
                pdf.rect(7, 7, 196, 283)
                py = 15
            
            if i % 2 == 0:
                pdf.set_fill_color(235, 228, 210)
            else:
                pdf.set_fill_color(245, 238, 220)
            pdf.rect(10, py - 1, 190, 4.5, 'F')
            
            pdf.set_text_color(40, 35, 25)
            pdf.text(12, py + 2, f"{p['qty']}x {p['name'][:35]}")
            
            if p['price']:
                pdf.set_text_color(34, 120, 34)
                try: pdf.set_font("Roboto", "", 4.5)
                except Exception: pdf.set_font("Helvetica", "", 4.5)
                qt = p.get('qt_min', 99)
                qt_str = f" (~{qt} min QT)" if qt > 0 else " (local)"
                if qt >= 50:
                    pdf.set_text_color(180, 50, 30)  # Red for wormhole
                    qt_str = f" [!] WORMHOLE ~{qt} min)"
                # Show terminal name + enriched location
                raw = p.get('raw_loc', '')
                if raw and raw.lower() not in p['loc'].lower():
                    loc_display = f"@ {raw[:25]} // {p['loc'][:30]}{qt_str}"
                else:
                    loc_display = f"@ {p['loc'][:50]}{qt_str}"
                pdf.text(68, py + 2, loc_display)
                pdf.set_text_color(120, 100, 50)
                pdf.text(178, py + 2, f"{p['price']:,.0f}/u")
                try: pdf.set_font("Roboto", "", 5.5)
                except Exception: pdf.set_font("Helvetica", "", 5.5)
            else:
                pdf.set_text_color(180, 80, 30)
                pdf.text(68, py + 2, p['loc'][:65])
            
            py += 4.5
        
        # Route summary grouped by location
        py += 3
        loc_items = {}
        for p in procurement:
            loc_items.setdefault(p['loc'], []).append(p)
        
        # Sort locations by planet distance (use raw_loc for accurate distance)
        def _loc_sort_key(loc_items_pair):
            loc, litems = loc_items_pair
            raw = litems[0].get('raw_loc', loc) if litems else loc
            return (_qt_distance(raw), -len(litems))
        sorted_locs = sorted(loc_items.items(), key=_loc_sort_key)
        
        if py < 245 and len(sorted_locs) >= 1:
            # Add Stor-All purchase as first stop if needed
            stor_all_stop = None
            if has_loose_items:
                # Find nearest Stor-All vendor
                stor_loc = "STAGING AREA"
                if _uex_items_trade_db_local:
                    stor_candidates = []
                    for db_name, entries in _uex_items_trade_db_local.items():
                        if "stor" in db_name.lower() and "scu" in db_name.lower() and "self-storage" in db_name.lower():
                            for e in entries:
                                if isinstance(e, dict) and e.get('buy', e.get('b', 0)) > 0:
                                    loc = e.get('terminal', e.get('t', 'UNKNOWN'))
                                    price = e.get('buy', e.get('b', 0))
                                    dist = _qt_distance(loc)
                                    stor_candidates.append((dist, price, loc))
                    if stor_candidates:
                        stor_candidates.sort(key=lambda x: (x[0], x[1]))
                        stor_loc = stor_candidates[0][2]
                # Build exact container list from Stor-All items in cargo
                box_counts = {}
                for item in items:
                    ilow = item['name'].lower()
                    if 'stor' in ilow and ('all' in ilow or 'storage' in ilow):
                        box_counts[item['name']] = box_counts.get(item['name'], 0) + int(item['qty'])
                if box_counts:
                    box_list = ", ".join(f"{v}x {k[:25]}" for k, v in box_counts.items())
                else:
                    box_list = "Stor-All containers"
                stor_all_stop = f"STOP 0: {_enrich_location(stor_loc)} -> Buy {box_list}"
            
            num_stops = min(len(sorted_locs), 5) + (1 if stor_all_stop else 0)
            # Add lines for autobox packing contents
            _ab = getattr(pdf, '_autobox_data', None)
            if stor_all_stop and _ab and _ab.get('num_boxes', 0) > 0:
                num_stops += len(_ab.get('boxes', []))
            summary_h = num_stops * 4 + 6
            pdf.set_fill_color(35, 42, 55)
            pdf.rect(10, py - 1, 190, summary_h, 'F')
            pdf.set_text_color(200, 168, 78)
            try: pdf.set_font("Roboto", "B", 6)
            except Exception: pdf.set_font("Helvetica", "B", 6)
            pdf.text(12, py + 3, f"OPTIMIZED ROUTE ({origin[:20].upper()}):")
            
            try: pdf.set_font("Roboto", "", 5.5)
            except Exception: pdf.set_font("Helvetica", "", 5.5)
            pdf.set_text_color(200, 210, 220)
            
            stop_idx = 0
            stop_y = py + 7
            
            if stor_all_stop:
                pdf.set_text_color(120, 200, 80)
                pdf.text(14, stop_y, stor_all_stop)
                stop_y += 4
                # Show autobox packing contents below STOP 0
                autobox_data = getattr(pdf, '_autobox_data', None)
                if autobox_data and autobox_data.get('num_boxes', 0) > 0:
                    pdf.set_text_color(150, 180, 160)
                    for bx_idx, bx in enumerate(autobox_data.get('boxes', [])):
                        contents = ", ".join(f"{e['qty']}x {e['name'][:18]}" for e in bx)
                        if len(contents) > 80:
                            contents = contents[:77] + "..."
                        pdf.text(20, stop_y, f"  STOR-ALL #{bx_idx+1}: {contents}")
                        stop_y += 3.5
                        num_stops += 1
                pdf.set_text_color(200, 210, 220)
                stop_idx = 1
            
            for j, (loc, litems) in enumerate(sorted_locs[:5]):
                item_names = ", ".join(f"{p['qty']}x {p['name'][:15]}" for p in litems[:3])
                if len(litems) > 3:
                    item_names += f" +{len(litems)-3} more"
                # Show terminal/shop name from raw_loc
                raw = litems[0].get('raw_loc', '') if litems else ''
                if raw and raw.lower() not in loc.lower():
                    stop_label = f"{loc[:30]} ({raw[:20]})"
                else:
                    stop_label = loc[:50]
                pdf.text(14, stop_y, f"STOP {stop_idx + j + 1}: {stop_label} -> {item_names[:65]}")
                stop_y += 4
            
            py += summary_h + 2
        
        table_y = py + 8
    
    # âš“âš“ CARGO TABLE âš“âš“
    # Header
    pdf.set_fill_color(25, 32, 45)
    pdf.rect(10, table_y, 190, 7, 'F')
    pdf.set_text_color(200, 168, 78)
    try: pdf.set_font("Roboto", "B", 6.5)
    except Exception: pdf.set_font("Helvetica", "B", 6.5)
    
    cols = [("Item / Description", 12), ("Box Size", 82), ("Qty", 105),
            ("Unit Price", 118), ("Total", 148), ("Courtesy", 172)]
    for label, x in cols:
        pdf.text(x, table_y + 5, label)
    
    # Rows
    row_y = table_y + 8
    grand_total = 0
    try: pdf.set_font("Roboto", "", 6.5)
    except Exception: pdf.set_font("Helvetica", "", 6.5)
    
    for i, item in enumerate(items):
        if row_y > 240:
            # Need new page
            pdf.add_page()
            pdf.set_fill_color(245, 238, 220)
            pdf.rect(0, 0, 210, 297, 'F')
            pdf.set_draw_color(180, 150, 60)
            pdf.set_line_width(1.5)
            pdf.rect(5, 5, 200, 287)
            pdf.set_line_width(0.3)
            pdf.rect(7, 7, 196, 283)
            row_y = 15
        
        # Alternating row colors
        if i % 2 == 0:
            pdf.set_fill_color(235, 228, 210)
        else:
            pdf.set_fill_color(245, 238, 220)
        pdf.rect(10, row_y - 1, 190, 6, 'F')
        
        # Row line
        pdf.set_draw_color(200, 185, 140)
        pdf.set_line_width(0.1)
        pdf.line(10, row_y + 5, 200, row_y + 5)
        
        try:
            total = int(float(item['qty'])) * float(item['price'])
        except (ValueError, TypeError):
            total = 0
        if item['is_courtesy']:
            total = 0
        grand_total += total
        
        pdf.set_text_color(40, 35, 25)
        pdf.text(12, row_y + 3.5, item['name'][:40])
        pdf.text(82, row_y + 3.5, str(item['box_size']))
        pdf.text(105, row_y + 3.5, str(item['qty']))
        
        pdf.text(118, row_y + 3.5, f"{item['price']:,.0f} aUEC")
        pdf.text(148, row_y + 3.5, f"{total:,.0f}")
        
        if item['is_courtesy']:
            pdf.set_text_color(34, 139, 34)
            pdf.text(175, row_y + 3.5, "YES")
            pdf.set_text_color(40, 35, 25)
        
        row_y += 6
    
    # Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬ FOOTER / TOTALS Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬
    pdf.set_draw_color(180, 150, 60)
    pdf.set_line_width(0.5)
    pdf.line(10, row_y, 200, row_y)
    
    try: pdf.set_font("Roboto", "B", 7)
    except Exception: pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(120, 100, 50)
    pdf.text(12, row_y + 5, f"TOTAL ITEMS: {len(items)}")
    
    pdf.text(148, row_y + 5, f"TOTAL: {grand_total:,.0f} aUEC")
    
    # Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ ORE QUALITY + ORDNANCE ADVISORIES Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
    advisory_y = row_y + 8
    has_ores = False
    has_ordnance = False
    ore_notes = []
    for item in items:
        name_low = item["name"].lower()
        # Check for refined ores
        if name_low in ore_quality_map:
            oq = ore_quality_map[name_low]
            ore_notes.append(f"  {item['name']}: Tier {oq['tier']} (Q{oq['min_good']}+ recommended) - {oq['note']}")
            has_ores = True
        # Check for ordnance (missiles/torpedoes/bombs)
        if any(x in name_low for x in ["missile", "torpedo", "bomb", "ammunition", "countermeasure"]):
            has_ordnance = True
    
    if has_ores or has_ordnance:
        try: pdf.set_font("Roboto", "B", 5.5)
        except Exception: pdf.set_font("Helvetica", "B", 5.5)
        
        # (ordnance notice removed per user request)
        
        if has_ores and ore_notes:
            pdf.set_fill_color(35, 40, 30)
            note_h = min(len(ore_notes), 4) * 4 + 5
            pdf.rect(10, advisory_y - 1.5, 190, note_h, 'F')
            pdf.set_text_color(120, 200, 80)
            pdf.text(14, advisory_y + 1.5, "MATERIAL QUALITY ADVISORY // Recommended refinery quality grade 700+ for all Tier A/B ores:")
            try: pdf.set_font("Roboto", "", 5)
            except Exception: pdf.set_font("Helvetica", "", 5)
            pdf.set_text_color(160, 190, 140)
            for i, note in enumerate(ore_notes[:4]):
                pdf.text(16, advisory_y + 5 + i * 3.5, note[:130])
            advisory_y += note_h + 1
        
        row_y = advisory_y - 6
    
    # â”€â”€ SIGNATURE â”€â”€
    sig_y = row_y + 20  # Extra spacing to avoid overlap with rec transport
    if sig_y > 250:
        pdf.add_page()
        pdf.set_fill_color(245, 238, 220)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_draw_color(180, 150, 60)
        pdf.set_line_width(1.5)
        pdf.rect(5, 5, 200, 287)
        pdf.set_line_width(0.3)
        pdf.rect(7, 7, 196, 283)
        sig_y = 20
    
    # Extract rank using lore_helper
    officer_rank, officer_clean = extract_rank(officer)
    
    # â”€â”€ OFFICER SIGNATURE (only officer signs supply route) â”€â”€
    pdf.set_text_color(200, 168, 78)
    try: pdf.set_font("Roboto", "B", 8)
    except Exception: pdf.set_font("Helvetica", "B", 8)
    pdf.text(12, sig_y, "LOADING OFFICER SIGNATURE")
    pdf.set_draw_color(200, 168, 78)
    pdf.set_line_width(0.2)
    pdf.line(12, sig_y + 1.5, 120, sig_y + 1.5)
    
    try: pdf.set_font("Roboto", "", 6.5)
    except Exception: pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(80, 70, 50)
    pdf.text(12, sig_y + 7, f"Name: {officer}")
    pdf.text(12, sig_y + 11, f"Rank: {officer_rank}")
    
    # Officer signature line + PNG
    pdf.set_draw_color(150, 140, 110)
    pdf.set_line_width(0.1)
    pdf.line(40, sig_y + 20, 110, sig_y + 20)
    
    podpisy_dir = get_signatures_dir()
    sig_file = process_signature(podpisy_dir, officer)
    if sig_file and os.path.exists(sig_file):
        pdf.image(sig_file, x=42, y=sig_y + 8, w=55, h=13)
    
    # R1 Stamp (right)
    stamp_file = process_r1_stamp(podpisy_dir)
    if stamp_file and os.path.exists(stamp_file):
        pdf.image(stamp_file, x=155, y=sig_y, w=22, h=22)
    
    # â”€â”€ SECURITY FOOTER â”€â”€
    notice_y = sig_y + 24
    pdf.set_draw_color(200, 168, 78)
    pdf.set_line_width(0.2)
    pdf.line(10, notice_y, 200, notice_y)
    try: pdf.set_font("Roboto", "B", 5)
    except Exception: pdf.set_font("Helvetica", "B", 5)
    pdf.set_text_color(30, 100, 180)
    pdf.text(12, notice_y + 3.5, "VERIFIED SECURITY SIGNATURE SEAL - 44TH BATTLE GROUP LOGISTICS")
    try: pdf.set_font("Roboto", "I", 4.5)
    except Exception: pdf.set_font("Helvetica", "I", 4.5)
    # CARGO SHIP RECOMMENDATION â€” what ship to use to transport this cargo
    total_scu = 0
    for item in items:
        name_low = item.get("name", "").lower().strip()
        box_sz = item.get("box_size", "1 unit").lower()
        try:
            qty = int(float(item.get("qty", 1)))
        except (ValueError, TypeError):
            qty = 1
        # Use volume_map first (most accurate, includes bounding box cage for ordnance)
        if name_low in volume_map:
            total_scu += qty * volume_map[name_low]
        # Fallback: parse box_size string for SCU multiplier
        elif "8 scu" in box_sz: total_scu += qty * 8
        elif "4 scu" in box_sz: total_scu += qty * 4
        elif "2 scu" in box_sz: total_scu += qty * 2
        elif "1 scu" in box_sz or "scu" in box_sz: total_scu += qty * 1
        elif "cscu" in box_sz: total_scu += qty * 1
        else: total_scu += qty * 0.01  # minimal default
    
    # Recommend cargo ship to transport the full load
    try:
        cargo_rec = _recommend_cargo_ship(total_scu)
        if cargo_rec:
            try: pdf.set_font("Roboto", "B", 6)
            except Exception: pdf.set_font("Helvetica", "B", 6)
            pdf.set_text_color(180, 140, 30)
            rec_text = f"RECOMMENDED TRANSPORT: {cargo_rec['name'].upper()} ({cargo_rec['scu']} SCU)"
            if cargo_rec['trips'] > 1:
                rec_text += f" // {cargo_rec['trips']} TRIPS REQUIRED"
            pdf.text(12, row_y + 10, rec_text[:140])
            row_y += 4
            # Alt ship note
            if cargo_rec.get("alt"):
                try: pdf.set_font("Roboto", "I", 5)
                except Exception: pdf.set_font("Helvetica", "I", 5)
                pdf.set_text_color(120, 110, 80)
                pdf.text(12, row_y + 10, f"Alt: {cargo_rec['alt']}")
                row_y += 3
    except Exception:
        pass
    
    # CONCEPT ADVISORY (no capacity warning in supply route â€” that's in manifest only)
    is_concept = False
    vessel_low = vessel.lower().strip()
    for k, v in _uex_ships_db.items():
        sname = v.get("name", k).lower()
        if vessel_low == k.lower() or vessel_low == sname or vessel_low in sname:
            is_concept = v.get("is_concept", False) or k.lower() in _CONCEPT_SHIPS
            break
    
    if is_concept:
        row_y += 2
        wy = row_y + 8
        try: pdf.set_font("Roboto", "B", 5.5)
        except Exception: pdf.set_font("Helvetica", "B", 5.5)
        pdf.set_fill_color(255, 248, 220)
        pdf.rect(10, wy - 2, 190, 6, 'F')
        pdf.set_draw_color(180, 150, 50)
        pdf.set_line_width(0.3)
        pdf.rect(10, wy - 2, 190, 6, 'D')
        pdf.set_text_color(150, 120, 30)
        pdf.text(14, wy + 1.8, "ADVISORY // VESSEL CLASSIFIED AS CONCEPT-STAGE -- CARGO DATA MAY BE APPROXIMATE")
        row_y += 7
    
    
    # Ledger hash
    seed = hash(req_id + vessel + officer)
    random.seed(seed)
    prefixes = ["REQ", "SEC", "LOG", "TAC", "NAV"]
    divisions = ["44BG", "UEE-9N", "FLEET-44", "TAC-DIV"]
    suffixes = ["ALPHA", "BRAVO", "X-RAY", "OMEGA", "DELTA-6"]
    hash_id = f"{random.choice(prefixes)}-{random.choice(divisions)}-{random.randint(10000, 99999)}-{random.choice(suffixes)}"
    try: pdf.set_font("Roboto", "B", 4.5)
    except Exception: pdf.set_font("Helvetica", "B", 4.5)
    pdf.set_text_color(120, 110, 90)
    pdf.text(82, sig_y + 38, f"LEDGER HASH: {hash_id}")
    
    # Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬ SAVE Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬
    try:
        pdf.output(save_path)
    except PermissionError as e:
        messagebox.showerror("Error", f"Cannot save PDF (file in use?): {e}")
        return
    except Exception as e:
        # fpdf2 font subsetting may raise warnings about glyph names
        # but the PDF is usually still written. Check if file exists.
        if os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
            print(f"[PDF] Font subsetting warning (PDF saved OK): {e}")
        else:
            messagebox.showerror("Error", f"Failed to generate PDF: {e}")
            return
    
    # Only show success for single generation (not batch)
    if not hasattr(self, '_gen3_running') or not self._gen3_running:
        messagebox.showinfo("Success", f"Supply Route PDF saved to:\n{save_path}")

def _patched_generate_supply_route_pdf(self):
    """Direct PDF generation Ä‚ËĂ˘â€šÂ¬Ă˘â‚¬ĹĄ no main.pyc, instant."""
    generate_pdf_direct(self)



