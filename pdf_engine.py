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
    extract_rank, generate_dynamic_lore_story,
)
from signature_helper import (
    process_signature, get_signatures_dir,
    process_r1_stamp, get_processed_barcode_path,
)
from fleet_helper import _recommend_shuttle, _recommend_cargo_ship, _CONCEPT_SHIPS, _load_uex_ships_db
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

def format_auec(amount, include_unit=True):
    """Centralized currency formatter for aUEC values.
    Ensures thousand separators and clean aUEC suffixes. Returns 'undefined' when price is unknown.
    """
    if amount is None or str(amount).lower().strip() in ("", "undefined", "none", "null"):
        return "undefined"
    try:
        val = float(amount)
        if val.is_integer():
            val_str = f"{int(val):,}"
        else:
            val_str = f"{val:,.2f}"
    except (ValueError, TypeError):
        val_str = str(amount)
    return f"{val_str} aUEC" if include_unit else val_str


def _to_general_category(name):
    n = str(name).lower()
    if any(k in n for k in ["fuel", "quantum", "hydrogen"]):
        return "Fuel & Volatiles"
    elif any(k in n for k in ["torpedo", "missile", "bomb", "seeker", "decoy", "noise", "countermeasure"]):
        return "Ordnance & Munitions"
    elif any(k in n for k in ["rmc", "composite", "construction", "material", "refined", "ore", "ingot"]):
        return "Raw & Refined Commodities"
    elif any(k in n for k in ["rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "launcher", "weapon", "p4-ar", "fs-9", "s-38", "p8-sc", "p6-lr", "br2", "magazine", "mag", "ammo"]):
        return "Weapons & Ammunition"
    elif any(k in n for k in ["helmet", "core", "arms", "legs", "undersuit", "backpack", "armor", "suit", "jacket", "pants", "shoes", "shirt", "gloves", "cap", "overalls", "vest", "dress"]):
        return "Armor & Field Gear"
    elif any(k in n for k in ["medpen", "medkit", "paramed", "lifeguard", "refill", "hemozal", "oxypen", "adrenapen", "medical"]):
        return "Medical Supplies"
    elif any(k in n for k in ["cruz", "lux", "drink", "food", "bottle", "burrito", "snaggle", "pips", "water", "meal", "ration"]):
        return "Rations & Consumables"
    elif any(k in n for k in ["multitool", "multi-tool", "tractor", "maxlift", "cambio", "battery", "canister", "attachment", "mining"]):
        return "Utility Tools & Attachments"
    else:
        return "General Equipment & Gear"

def draw_report_paragraph(self, x, y, width, text, redacted_sentences_indices=None, fully_redacted=False):
    try: self.set_font("Roboto", "", 7.5)
    except Exception: self.set_font("Helvetica", "", 7.5)
    line_height = 4.2
    space_w = self.get_string_width(' ')
    current_x = x
    current_y = y

    # Replace any unsupported unicode block characters
    clean_text = (text or "").replace("█", "__REDACTED__").replace("𖠀", "__REDACTED__")

    words = clean_text.split()
    for w_idx, word in enumerate(words):
        is_redacted = fully_redacted or ("__REDACTED__" in word) or ("[REDACTED]" in word)
        
        if is_redacted:
            word_w = 14.0
        else:
            word_w = self.get_string_width(word)

        if current_x + word_w > x + width:
            current_x = x
            current_y += line_height

        if is_redacted:
            self.set_fill_color(20, 20, 20)
            self.rect(current_x, current_y + 0.5, word_w, line_height - 1.0, 'F')
        else:
            self.set_text_color(30, 40, 60)
            self.text(current_x, current_y + 3.2, word)

        current_x += word_w + space_w

    return current_y + line_height


def draw_classified_invoice_breakdown(pdf, current_y, items, req_id="N/A", delivery_date=""):
    """
    Renders official UEE Tactical Requisition Invoice / Billing breakdown
    with itemized costs, procurement directives, unit prices, and financial total.
    """
    if not items:
        return current_y

    from sc_wiki_db import get_item_procurement_resolution, lookup_item
    
    needed_h = 24 + len(items) * 4.5 + 14
    if current_y + min(needed_h, 50) > 265:
        pdf.add_page()
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(0, 0, 210, 297, 'F')
        current_y = 35

    # Invoice Header Banner
    pdf.set_fill_color(15, 30, 60)
    pdf.rect(10, current_y, 190, 6.5, 'F')
    pdf.set_text_color(212, 175, 55)
    try: pdf.set_font("Roboto", "B", 6.5)
    except Exception: pdf.set_font("Helvetica", "B", 6.5)
    pdf.text(12, current_y + 4.5, "UEE NAVAL LOGISTICS // PROCUREMENT INVOICE & REQUISITION AUDIT")
    
    pdf.set_text_color(200, 210, 230)
    try: pdf.set_font("Roboto", "", 5.5)
    except Exception: pdf.set_font("Helvetica", "", 5.5)
    pdf.text(135, current_y + 4.5, f"REF: INV-{str(req_id)[:10]} | AUTH: CLASSIFIED")
    
    current_y += 7.0

    # Column Headers Bar
    pdf.set_fill_color(35, 48, 72)
    pdf.rect(10, current_y, 190, 5.0, 'F')
    pdf.set_text_color(255, 255, 255)
    try: pdf.set_font("Roboto", "B", 5.5)
    except Exception: pdf.set_font("Helvetica", "B", 5.5)

    pdf.text(12, current_y + 3.5, "LINE #")
    pdf.text(26, current_y + 3.5, "ITEM SPECIFICATION")
    pdf.text(95, current_y + 3.5, "QTY")
    pdf.text(108, current_y + 3.5, "UNIT COST")
    pdf.text(130, current_y + 3.5, "TOTAL (aUEC)")
    pdf.text(154, current_y + 3.5, "PROCUREMENT DIRECTIVE")

    current_y += 5.5
    row_idx = 0
    total_commercial_auec = 0.0

    for it in items:
        if not isinstance(it, dict): continue
        raw_name = str(it.get("name", "")).strip()
        if not raw_name: continue
        
        try: qty_val = int(float(str(it.get("qty", 1)).strip()))
        except Exception: qty_val = 1
        
        unit_price = float(it.get("price", 0.0))
        if unit_price == 0.0:
            locs = lookup_item(raw_name)
            if locs:
                unit_price = float(locs[0].get("price", 0.0))
        
        row_subtotal = unit_price * qty_val
        total_commercial_auec += row_subtotal
        
        proc_info = get_item_procurement_resolution(raw_name)
        p_status = proc_info.get("status", "BUYABLE")
        if p_status == "BUYABLE":
            directive_str = "Commercial Purchase"
        elif p_status == "NEED_TO_BE_CRAFTED":
            directive_str = "Fabrication (Blueprint)"
        else:
            directive_str = "Field Recovery / Subscriber"

        row_h = 4.2
        if current_y + row_h > 265:
            pdf.add_page()
            pdf.set_fill_color(255, 255, 255)
            pdf.rect(0, 0, 210, 297, 'F')
            current_y = 35

        bg_col = (248, 249, 250) if row_idx % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg_col)
        pdf.set_draw_color(210, 218, 226)
        pdf.set_line_width(0.1)
        pdf.rect(10, current_y, 190, row_h, 'DF')

        pdf.set_text_color(40, 50, 70)
        try: pdf.set_font("Roboto", "", 5.2)
        except Exception: pdf.set_font("Helvetica", "", 5.2)
        
        pdf.text(12, current_y + 3.0, f"#{row_idx + 1:02d}")
        pdf.text(26, current_y + 3.0, raw_name[:42])
        pdf.text(95, current_y + 3.0, f"x{qty_val}")
        
        p_str = f"{unit_price:,.0f} aUEC" if unit_price > 0 else "0 aUEC"
        t_str = f"{row_subtotal:,.0f} aUEC" if row_subtotal > 0 else "0 aUEC"
        pdf.text(108, current_y + 3.0, p_str)
        
        try: pdf.set_font("Roboto", "B", 5.2)
        except Exception: pdf.set_font("Helvetica", "B", 5.2)
        pdf.text(130, current_y + 3.0, t_str)
        
        try: pdf.set_font("Roboto", "", 5.0)
        except Exception: pdf.set_font("Helvetica", "", 5.0)
        pdf.set_text_color(60, 100, 150)
        pdf.text(154, current_y + 3.0, directive_str[:30])

        current_y += row_h
        row_idx += 1

    # Financial Total Summary Box
    current_y += 1.5
    pdf.set_fill_color(15, 30, 60)
    pdf.rect(10, current_y, 190, 6.0, 'F')
    pdf.set_text_color(212, 175, 55)
    try: pdf.set_font("Roboto", "B", 6.0)
    except Exception: pdf.set_font("Helvetica", "B", 6.0)
    pdf.text(12, current_y + 4.2, "TOTAL COMMERCIAL PROCUREMENT BUDGET:")
    pdf.text(130, current_y + 4.2, f"{total_commercial_auec:,.0f} aUEC")
    
    pdf.set_text_color(140, 200, 160)
    try: pdf.set_font("Roboto", "B", 5.0)
    except Exception: pdf.set_font("Helvetica", "B", 5.0)
    pdf.text(154, current_y + 4.2, "[STATUS: DISBURSEMENT CLEARED]")

    return current_y + 8.0


def draw_autoboxing_packing_manifest(pdf, start_y, items_list, volume_map, sec_level="OFFICERS_ONLY_ENCRYPTED", vessel=None):
    """Renders the Auto-Boxing Packing Manifest block with capital ship category multi-box breakdown and deck routing."""
    from storall_packer import pack_items

    if not items_list:
        return start_y

    packing = pack_items(items_list, volume_map, vessel=vessel)
    if not packing or packing.get("num_boxes", 0) <= 0:
        return start_y

    num_boxes = packing["num_boxes"]
    box_label = packing["box_label"]
    max_capacity = packing["max_capacity"]
    boxes = packing["boxes"]
    box_vols = packing["box_vols"]
    box_labels = packing.get("box_labels", [])

    sec_low = str(sec_level).upper()
    is_classified = ("OFFICERS" in sec_low or "ENCRYPTED" in sec_low or "CLASSIFIED" in sec_low)
    is_public = ("PUBLIC" in sec_low or "OPEN" in sec_low)
    is_sr = getattr(pdf, '_is_supply_route', False)

    def _add_manifest_continuation_page(b_idx=0, c_label="BOX #1", dest_tag="", used_v=0.0, max_cap=1.0, used_pct=0):
        pdf.add_page()
        if is_sr:
            pdf.set_fill_color(245, 238, 220)
            pdf.rect(0, 0, 210, 297, 'F')
            pdf.set_draw_color(180, 150, 60)
            pdf.set_line_width(1.5)
            pdf.rect(5, 5, 200, 287)
            pdf.set_line_width(0.3)
            pdf.rect(7, 7, 196, 283)
            new_y = 15
        else:
            new_y = 55
        
        pdf.set_fill_color(15, 30, 60)
        pdf.rect(10, new_y, 190, 6, 'F')
        pdf.set_text_color(200, 168, 78)
        try: pdf.set_font("Roboto", "B", 7)
        except Exception: pdf.set_font("Helvetica", "B", 7)
        pdf.text(12, new_y + 4.2, "LOGISTICS AUTO-BOXING PACKING MANIFEST (CONT.)")
        new_y += 7.5

        if c_label:
            pdf.set_fill_color(30, 45, 70)
            pdf.rect(10, new_y, 190, 5, 'F')
            pdf.set_text_color(220, 220, 220)
            try: pdf.set_font("Roboto", "B", 6)
            except Exception: pdf.set_font("Helvetica", "B", 6)
            pdf.text(12, new_y + 3.5, f"STOR-ALL #{b_idx+1}: {c_label}{dest_tag} (CONT.)  (Capacity Used: {used_v:.3f}/{max_cap:.2f} SCU - {used_pct}%)")
            new_y += 5.5
        return new_y

    curr_y = start_y + 4
    if curr_y > 235:
        curr_y = _add_manifest_continuation_page(0, "", "", 0, max_capacity, 0)
    else:
        pdf.set_fill_color(15, 30, 60)
        pdf.rect(10, curr_y, 190, 6, 'F')
        pdf.set_text_color(200, 168, 78)
        try: pdf.set_font("Roboto", "B", 7)
        except Exception: pdf.set_font("Helvetica", "B", 7)
        pdf.text(12, curr_y + 4.2, f"LOGISTICS AUTO-BOXING PACKING MANIFEST (CONTAINERS: {num_boxes} BOXES | MAX: {box_label})")
        curr_y += 8

    v_low = str(vessel or "").lower().strip()
    is_idris = "idris" in v_low
    is_capital = is_idris or any(c in v_low for c in ["polaris", "kraken", "javelin"])

    for b_idx in range(num_boxes):
        bx_items = boxes[b_idx] if b_idx < len(boxes) else []
        if not bx_items:
            continue

        used_v = box_vols[b_idx]
        used_pct = int(min(used_v / max_capacity * 100, 100))
        c_label = box_labels[b_idx] if b_idx < len(box_labels) else f"BOX #{b_idx+1}"

        dest_tag = ""
        if is_idris:
            if any(k in c_label.upper() for k in ["REPAIR", "RMC", "FUEL", "ORDNANCE", "MISSILE", "TORPEDO"]):
                dest_tag = " -> DEST: FLIGHT DECK / CARGO BAY (LOWER)"
            else:
                dest_tag = " -> DEST: HANGAR 1 / UPPER DECK (READY ROOM)"
        elif is_capital:
            if any(k in c_label.upper() for k in ["REPAIR", "RMC", "FUEL", "ORDNANCE"]):
                dest_tag = " -> DEST: FLIGHT DECK / CARGO BAY"
            else:
                dest_tag = " -> DEST: HANGAR / ARMORY LOCKERS"

        if curr_y > 230:
            curr_y = _add_manifest_continuation_page(b_idx, c_label, dest_tag, used_v, max_capacity, used_pct)
        else:
            pdf.set_fill_color(30, 45, 70)
            pdf.rect(10, curr_y, 190, 5, 'F')
            pdf.set_text_color(220, 220, 220)
            try: pdf.set_font("Roboto", "B", 6)
            except Exception: pdf.set_font("Helvetica", "B", 6)
            pdf.text(12, curr_y + 3.5, f"STOR-ALL #{b_idx+1}: {c_label}{dest_tag}  (Capacity Used: {used_v:.3f}/{max_capacity:.2f} SCU - {used_pct}%)")
            curr_y += 5.5

        if is_classified:
            display_items = [{"name": it["name"], "qty_str": f"{it['qty']}x", "vol_str": f"{it.get('total_vol', it.get('vol', 0.0)):.3f} SCU"} for it in bx_items]
        elif is_public:
            cat_set = set()
            for item in bx_items:
                cat_set.add(_to_general_category(item["name"]))
            display_items = [{"name": gcat, "qty_str": "XXXx", "vol_str": "XXX SCU"} for gcat in sorted(cat_set)]
        else:
            cat_counts = {}
            cat_vols = {}
            for item in bx_items:
                gcat = _to_general_category(item["name"])
                cat_counts[gcat] = cat_counts.get(gcat, 0) + item["qty"]
                v_item = item.get('total_vol', item.get('vol', 0.0))
                cat_vols[gcat] = cat_vols.get(gcat, 0.0) + v_item
            display_items = [{"name": gcat, "qty_str": f"{c_qty}x", "vol_str": f"{cat_vols[gcat]:.3f} SCU"} for gcat, c_qty in cat_counts.items()]

        for i, item in enumerate(display_items):
            if curr_y > 250:
                curr_y = _add_manifest_continuation_page(b_idx, c_label, dest_tag, used_v, max_capacity, used_pct)
            if i % 2 == 0: pdf.set_fill_color(240, 242, 245)
            else: pdf.set_fill_color(250, 252, 255)
            pdf.rect(10, curr_y, 190, 4.5, 'F')
            pdf.set_text_color(30, 40, 50)
            try: pdf.set_font("Roboto", "", 5.5)
            except Exception: pdf.set_font("Helvetica", "", 5.5)
            pdf.text(14, curr_y + 3, f"{item['qty_str']} {item['name']}")
            pdf.text(175, curr_y + 3, item['vol_str'])
            curr_y += 4.5
        curr_y += 2

    return curr_y

def draw_signatures(self):
    # Always push Auto-Boxing Packing Manifest & Narrative Lore Record to Page 4 so Page 3 is reserved for Cargo Grid
    self.add_page()
    box_y = max(54, getattr(self, 'get_y', lambda: 54)() + 2)
    page_box_h = 276 - box_y
    self.set_line_width(0.3)
    self.set_draw_color(100, 116, 139)
    # White background with subtle border for manifest
    self.set_fill_color(245, 247, 250)
    self.rect(10, box_y, 190, page_box_h, 'DF')
    # Navy header bar for section title
    self.set_fill_color(15, 30, 60)
    self.rect(10, box_y, 190, 6, 'F')
    self.set_text_color(220, 220, 220)
    self.set_font("Roboto", "B", 8)
    self.text(13, box_y + 4.2, "LOGISTICS DIRECTIVE & FIELD REPORT")
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
        # Combined seed from time, vessel, manifest, and danger level
        combined_seed = hash((_SESSION_SEED, current_vessel, current_manifest_hash, danger_level, os.urandom(4)))
        formatted_story = generate_dynamic_lore_story(
            items_list=items_list,
            vessel=current_vessel,
            location=self.location,
            captain=current_captain,
            loading_officer=current_officer,
            loading_crew=current_crew,
            danger_level=danger_level,
            seed_entropy=combined_seed
        )
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
    self.line(140, box_y + 8, 140, min(box_y + page_box_h - 24, box_y + 40))
    sec = self.security_level.upper()
    fully_redacted = False
    redacted_sentences_indices = []
    
    # PUBLIC = fully redacted
    if "PUBLIC" in sec or "OPEN" in sec:
        fully_redacted = True
    elif "RESTRICTED" in sec or ("SECURED" in sec and "OFFICERS" not in sec and "ENCRYPTED" not in sec):
        # VERIFIED / SECURED / RESTRICTED -> Targeted redaction of sensitive names/vessel/location only
        for sensitive_term in [self.loading_officer, self.captain, self.loading_crew, self.vessel, self.location]:
            if sensitive_term and str(sensitive_term).strip():
                term_str = str(sensitive_term).strip()
                # Extract clean name without rank title
                rank_title, clean_name = extract_rank(term_str)
                target_names = [term_str]
                if clean_name and len(clean_name) > 2:
                    target_names.append(clean_name)
                for tname in target_names:
                    if tname and tname in formatted_story:
                        formatted_story = formatted_story.replace(tname, " __REDACTED__ ")

    # ── v0.6.1: RP Fluff Disclaimer Notice & Redaction ──
    _disclaimer_y = box_y + 8.5
    try:
        self.set_draw_color(140, 130, 100)
        self.set_line_width(0.15)
        self.line(14, _disclaimer_y, 136, _disclaimer_y)
        try:
            self.set_font("Courier", "", 5.0)
        except Exception:
            self.set_font("Helvetica", "", 5.0)
        self.set_text_color(130, 120, 90)
        if fully_redacted:
            self.set_fill_color(0, 0, 0)
            self.rect(14, _disclaimer_y + 1.2, 122, 4.5, 'F')
            _disclaimer_end_y = _disclaimer_y + 6.0
        else:
            _disc_text = ("[SIMULATED DISPATCH LOG // OOC FLUFF RECORD]: THE FOLLOWING NARRATIVE DISPATCH LOG IS "
                          "PROCEDURALLY GENERATED FLUFF TEXT FOR IMMERSION (OOC) AND DOES NOT AFFECT REAL IN-GAME "
                          "RP PERSISTENCE OR BATTLEGROUP WORLD STATE.")
            self.set_xy(14, _disclaimer_y + 1.5)
            self.multi_cell(122, 2.2, _disc_text, border=0, align="L")
            _disclaimer_end_y = self.get_y() + 1.0
        self.line(14, _disclaimer_end_y, 136, _disclaimer_end_y)
        _narrative_start_y = _disclaimer_end_y + 2.0

    except Exception:
        _narrative_start_y = _disclaimer_y + 8

    paragraph_end_y = self.draw_report_paragraph(14, _narrative_start_y, 122, formatted_story, redacted_sentences_indices, fully_redacted)
    
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
        
        from storall_packer import get_item_unit_volume
        unit_vol = get_item_unit_volume(item["name"], volume_map)
        
        item_vol = qty * unit_vol
        total_loose_vol += item_vol
        loose_items.append({
            "name": item["name"],
            "qty": qty,
            "unit_vol": unit_vol,
            "total_vol": item_vol
        })
            
    # ── Stor-All Auto-Boxing using canonical storall_packer (respecting Capital ship multi-box categories) ──
    from storall_packer import pack_items
    pack_res = pack_items(items_list, volume_map, vessel=self.vessel)
    boxes = pack_res.get("boxes", [])
    box_vols = pack_res.get("box_vols", [])
    num_boxes = pack_res.get("num_boxes", 0)
    max_capacity = pack_res.get("max_capacity", 1.0)
    box_label = pack_res.get("box_label", "1 SCU")
    box_labels = pack_res.get("box_labels", [])

    # Format container contents based on 3-tier classification level:
    # 1. CLASSIFIED / OFFICERS -> Exact item names & quantities
    # 2. VERIFIED / SECURED / RESTRICTED -> General category names ONLY (e.g. Weapons & Ammunition, Armor & Field Gear)
    # 3. PUBLIC -> Redacted entries ([REDACTED // FREIGHT CLASS])
    def _to_general_category(name):
        n = name.lower()
        if any(k in n for k in ["rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "launcher", "weapon", "p4-ar", "fs-9", "s-38", "p8-sc", "p6-lr", "br2", "magazine", "mag", "ammo"]):
            return "Weapons & Ammunition"
        elif any(k in n for k in ["helmet", "core", "arms", "legs", "undersuit", "backpack", "armor", "suit", "jacket", "pants", "shoes", "shirt", "gloves", "cap", "overalls", "vest", "dress"]):
            return "Armor & Field Gear"
        elif any(k in n for k in ["medpen", "medkit", "paramed", "lifeguard", "refill", "hemozal", "oxypen", "adrenapen", "medical"]):
            return "Medical Supplies"
        elif any(k in n for k in ["cruz", "lux", "drink", "food", "bottle", "burrito", "snaggle", "pips", "water", "meal", "ration"]):
            return "Rations & Consumables"
        elif any(k in n for k in ["multitool", "multi-tool", "tractor", "maxlift", "cambio", "battery", "canister", "attachment", "mining"]):
            return "Utility Tools & Attachments"
        else:
            return "General Equipment & Gear"

    formatted_boxes = []
    is_public = ("PUBLIC" in sec or "OPEN" in sec)

    for bx in boxes:
        formatted_bx = []
        if not is_public:
            # CLASSIFIED, VERIFIED, SECURED, RESTRICTED -> Exact item names & quantities for 44th BG members
            merged = {}
            for item in bx:
                iname = item["name"]
                if iname in merged:
                    merged[iname]["qty"] += item["qty"]
                    merged[iname]["vol"] += item.get("total_vol", item.get("vol", 0.0))
                else:
                    merged[iname] = {
                        "name": iname,
                        "qty": item["qty"],
                        "vol": item.get("total_vol", item.get("vol", 0.0))
                    }
            formatted_bx = list(merged.values())
        else:
            # PUBLIC -> General category names ONLY with masked quantities
            cat_counts = {}
            for item in bx:
                gcat = _to_general_category(item["name"])
                cat_counts[gcat] = cat_counts.get(gcat, 0) + item["qty"]
            for gcat in sorted(cat_counts.keys()):
                formatted_bx.append({
                    "name": gcat,
                    "qty": "XXXx",
                    "vol": 0.0
                })
        formatted_boxes.append(formatted_bx)

    if num_boxes > 0:
        self._autobox_data = {
            "boxes": formatted_boxes, "box_vols": box_vols,
            "box_label": box_label, "max_capacity": max_capacity,
            "num_boxes": num_boxes, "box_labels": box_labels
        }

    # ── Position cargo directive + rec transport + sigs DYNAMICALLY ──
    content_bottom_y = max(paragraph_end_y + 4, box_y + 48)
    sig_space_needed = 24
    directive_space = 10

    # ── SHIP GRID DATABASE LOOKUP ──
    ship_grid = None
    try:
        from cargo_grid_renderer import load_ship_grid
        ship_grid = load_ship_grid(self.vessel)
    except Exception as e:
        print(f"[Cargo Grid Lookup] Error: {e}")

    # ── RIGHT SIDEBAR: Telemetry + Cargo Grid Preview ──
    grid_area_x = 142
    grid_area_y = box_y + 8
    grid_area_w = 54
    grid_area_h = 62  # Bounded telemetry sidebar height so it does NOT intrude into lower sections

    # Draw sidebar background FIRST
    self.set_line_width(0.15)
    self.set_draw_color(180, 190, 200)
    self.set_fill_color(235, 238, 242)
    self.rect(grid_area_x, grid_area_y, grid_area_w, grid_area_h, 'DF')


    # ── TELEMETRY SENSORS (top of sidebar) ──
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

    # ── Divider line ──
    self.set_draw_color(180, 190, 200)
    self.set_line_width(0.1)
    self.line(grid_area_x + 3, sensor_y, grid_area_x + grid_area_w - 3, sensor_y)
    sensor_y += 3

    # ── CARGO GRID INFO (below telemetry) ──
    if "PUBLIC" in sec or "OPEN" in sec:
        self.set_font("Roboto", "B", 6)
        self.set_text_color(140, 100, 30)
        self.text(grid_area_x + 3, sensor_y, "CARGO [REDACTED]")
        sensor_y += 6
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
        sensor_y += 18
    else:
        self.set_font("Roboto", "I", 6.5)
        self.set_text_color(80, 90, 110)
        self.text(grid_area_x + 5, sensor_y + 5, "NO GRID DATA")
        sensor_y += 8

    # Calculate starting point for full-width sections below narrative and sidebar!
    content_bottom_y = max(paragraph_end_y + 4, sensor_y + 4)

    # Render Cargo Grid Placement Directive
    # ── DYNAMIC CARGO DIRECTIVE (Planetary vs In Hangar) ──
    vessel_upper = self.vessel.upper()
    load_loc = getattr(self, 'location', '') or ''
    load_type = ''
    try:
        if hasattr(self, '_loading_type_var'):
            load_type = self._loading_type_var.get()
        elif hasattr(self, 'loading_type_var'):
            load_type = self.loading_type_var.get()
    except Exception: pass

    # Calculate total SCU for directive text
    def _safe_scu_directive(item):
        try: q = float(str(item.get("qty", 1)).strip())
        except Exception: q = 1.0
        bs = str(item.get("box_size", "")).lower().strip()
        if "32 scu" in bs: return q * 32.0
        if "24 scu" in bs: return q * 24.0
        if "16 scu" in bs: return q * 16.0
        if "8 scu" in bs:  return q * 8.0
        if "4 scu" in bs:  return q * 4.0
        if "2 scu" in bs:  return q * 2.0
        return q * 0.005

    autobox_data = getattr(self, '_autobox_data', None)
    num_b = autobox_data.get("num_boxes", 0) if autobox_data else 0
    tot_scu_val = max(sum(_safe_scu_directive(i) for i in items_list) + float(num_b), 1.0)

    # Classify loading environment
    ltype_low = str(load_type).lower().strip()
    lloc_low = str(load_loc).lower().strip()
    is_planetary = any(k in ltype_low for k in ["planetary", "surface", "outpost", "ground"]) or \
                   any(k in lloc_low for k in ["outpost", "babbage", "lorville", "area18", "area 18", "orison", "levski", "rayari", "shubin", "hdms", "surface", "land", "revolux", "zeus", "rappel"])
    is_hangar = any(k in ltype_low for k in ["hangar", "bay", "elevator", "in hangar"]) or \
                any(k in lloc_low for k in ["hangar", "bay", "freight elevator", "in hangar"])

    marine_note = " Marine security escort recommended for planetary surface operations." if is_planetary else ""

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
        if is_planetary:
            grid_directive = f"PLANETARY DIRECTIVE: {holds} ({cap} SCU). Stack: {max_height}h max. Direct surface loading.{marine_note}"
        elif is_hangar:
            grid_directive = f"IN-HANGAR DIRECTIVE: {holds} ({cap} SCU). Freight elevator staging. Stack: {max_height}h max."
        else:
            grid_directive = f"CARGO DIRECTIVE: {holds} ({cap} SCU). Stack: {max_height}h, {max_crate} SCU max. Clamps locked.{marine_note}"
    else:
        if is_planetary:
            grid_directive = f"PLANETARY DIRECTIVE: Ground/Pad loading at {load_loc or 'Surface Outpost'}. Use of ATLS advised.{marine_note}"
        elif is_hangar:
            grid_directive = f"IN-HANGAR DIRECTIVE: Freight elevator staging at {load_loc or 'Station Hangar'}. Bay tractor active."
        else:
            grid_directive = f"CARGO DIRECTIVE: Standard bay staging ({tot_scu_val:.1f} SCU). Grid-lock all.{marine_note}"

    # ── UNIFIED LOGISTICS DIRECTIVE & FLEET PLANNER ADVISORY ──
    base_y = max(paragraph_end_y, content_bottom_y) if 'content_bottom_y' in locals() else paragraph_end_y
    directive_y = base_y + 2

    # Query fleet_helper for shuttle/fleet directive note
    rec_text = ""
    try:
        from fleet_helper import _recommend_shuttle, _recommend_cargo_ship
        vessel_name = getattr(self, 'vessel', '') or ''
        rec_info = _recommend_shuttle(vessel_name, tot_scu_val, loading_type=load_type, location=load_loc)
        if rec_info and rec_info.get("note"):
            rec_text = rec_info["note"]
        else:
            cargo_rec = _recommend_cargo_ship(tot_scu_val)
            if cargo_rec and "note" in cargo_rec:
                rec_text = cargo_rec["note"]
            elif cargo_rec and "name" in cargo_rec:
                rec_text = f"RECOMMENDED TRANSPORT SHIP: {cargo_rec['name']} ({cargo_rec.get('scu', 0)} SCU) for {tot_scu_val:.1f} SCU manifest.{marine_note}"
    except Exception as e:
        print(f"[Fleet Transport Rec] Error in pdf_engine: {e}")

    if "PUBLIC" in sec or "OPEN" in sec:
        combined_text = "LOGISTICS DIRECTIVE: [REDACTED // PUBLIC CHANNEL]"
    else:
        parts = []
        if rec_text:
            parts.append(rec_text.strip())
        if grid_directive and grid_directive != rec_text:
            parts.append(grid_directive.strip())
        combined_text = "\n".join(parts) if parts else "CARGO DIRECTIVE: Standard bay staging. Clamps locked."

    # Compute dynamic box height (width = 122mm, max_char ~ 90 per line)
    # Compute dynamic box height (width = 124mm, max_char ~ 90 per line)
    line_count = max(1, len(combined_text) // 85 + combined_text.count('\n') + 1)
    directive_box_h = max(14, line_count * 3.2 + 7)

    # Render dark blue background box with gold border
    self.set_fill_color(25, 35, 56)
    self.rect(12, directive_y, 126, directive_box_h, 'F')
    self.set_draw_color(212, 175, 55)
    self.set_line_width(0.3)
    self.rect(12, directive_y, 126, directive_box_h, 'D')

    # Title
    self.set_text_color(212, 175, 55)
    try: self.set_font("Roboto", "B", 6)
    except Exception: self.set_font("Helvetica", "B", 6)
    self.text(15, directive_y + 4.5, "LOGISTICS DIRECTIVE & FLEET PLANNER ADVISORY")

    # Body
    self.set_text_color(220, 230, 245)
    try: self.set_font("Roboto", "", 5.5)
    except Exception: self.set_font("Helvetica", "", 5.5)
    self.set_xy(14, directive_y + 6.0)
    self.multi_cell(122, 3.0, combined_text)

    # Set curr_end_y fluidly to Y position after box
    curr_end_y = max(directive_y + directive_box_h + 2, self.get_y() + 2)

    sig_space_needed = 24
    sig_section_y = 276 - sig_space_needed
    if curr_end_y + 2 > sig_section_y:
        self.add_page()
        sig_section_y = 35

    # ── CLASSIC DUAL SIGNATURE BOXES ──
    box_w = 93
    box_h = 24
    left_x = 10
    right_x = 107

    # Box 1 Outline (Loading Officer)
    self.set_line_width(0.2)
    self.set_draw_color(180, 190, 200)
    self.set_fill_color(248, 250, 252)
    self.rect(left_x, sig_section_y, box_w, box_h, 'DF')
    self.set_draw_color(15, 30, 60)
    self.line(left_x, sig_section_y + 6, left_x + box_w, sig_section_y + 6)
    self.set_text_color(15, 30, 60)
    try: self.set_font("Roboto", "B", 7)
    except Exception: self.set_font("Helvetica", "B", 7)
    self.text(left_x + 3, sig_section_y + 4.2, "LOADING OFFICER SIGNATURE")

    # Box 2 Outline (Ship Captain)
    self.set_draw_color(180, 190, 200)
    self.set_fill_color(248, 250, 252)
    self.rect(right_x, sig_section_y, box_w, box_h, 'DF')
    self.set_draw_color(15, 30, 60)
    self.line(right_x, sig_section_y + 6, right_x + box_w, sig_section_y + 6)
    self.set_text_color(15, 30, 60)
    self.text(right_x + 3, sig_section_y + 4.2, "SHIP CAPTAIN SIGNATURE")

    officer_name = self.loading_officer if self.loading_officer else "Authorized Logistics Officer"
    captain_name = self.captain if self.captain else "Authorized Ship Captain"
    officer_rank, officer_clean = extract_rank(officer_name)
    captain_rank, captain_clean = extract_rank(captain_name)
    if not officer_clean: officer_clean = officer_name
    if not captain_clean: captain_clean = captain_name
    if captain_rank == "UEE Logistics Officer": captain_rank = "Ship Captain"

    if ("VERIFIED" in sec or "PUBLIC" in sec) and self.loading_officer:
        self.set_fill_color(0, 0, 0)
        self.rect(left_x + 2, sig_section_y + 8, box_w - 4, 12, 'F')
        self.rect(right_x + 2, sig_section_y + 8, box_w - 4, 12, 'F')
        self.set_text_color(255, 255, 255)
        self.text(left_x + 5, sig_section_y + 15, "REDACTED // SECURED CHANNEL")
        self.text(right_x + 5, sig_section_y + 15, "REDACTED // SECURED CHANNEL")
    else:
        self.set_text_color(40, 50, 70)
        try: self.set_font("Roboto", "", 6)
        except Exception: self.set_font("Helvetica", "", 6)

        # Name + Rank inside signature boxes
        self.text(left_x + 3, sig_section_y + 11, f"Name: {officer_clean}")
        self.text(left_x + 3, sig_section_y + 15, f"Rank: {officer_rank}")

        self.text(right_x + 3, sig_section_y + 11, f"Name: {captain_clean}")
        self.text(right_x + 3, sig_section_y + 15, f"Rank: {captain_rank}")

        # Signature underline bars inside boxes
        self.set_draw_color(160, 170, 185)
        self.set_line_width(0.15)
        self.line(left_x + 38, sig_section_y + 20, left_x + box_w - 4, sig_section_y + 20)
        self.line(right_x + 38, sig_section_y + 20, right_x + box_w - 4, sig_section_y + 20)

        podpisy_dir = get_signatures_dir()
        officer_sig_img = process_signature(podpisy_dir, officer_name, is_captain=False)
        captain_sig_img = process_signature(podpisy_dir, captain_name, is_captain=True)

        if officer_sig_img and os.path.exists(officer_sig_img):
            self.image(officer_sig_img, x=left_x + 42, y=sig_section_y + 8, w=36, h=9)
        else:
            self.set_font("Courier", "I", 7)
            self.set_text_color(120, 130, 150)
            self.text(left_x + 44, sig_section_y + 14, f"~ {officer_clean} ~")
            try: self.set_font("Roboto", "", 6)
            except Exception: self.set_font("Helvetica", "", 6)

        if captain_sig_img and os.path.exists(captain_sig_img):
            self.image(captain_sig_img, x=right_x + 42, y=sig_section_y + 8, w=36, h=9)
        else:
            self.set_font("Courier", "I", 7)
            self.set_text_color(120, 130, 150)
            self.text(right_x + 44, sig_section_y + 14, f"~ {captain_clean} ~")
            try: self.set_font("Roboto", "", 6)
            except Exception: self.set_font("Helvetica", "", 6)

    # ——— DEDICATED AUTO-BOXING PACKING MANIFEST PAGE(S) (BEFORE CARGO GRID) ———
    autobox_data = getattr(self, '_autobox_data', None)
    if autobox_data and autobox_data.get("num_boxes", 0) > 0:
        try:
            self.add_page(orientation="P")
            draw_autoboxing_packing_manifest(
                pdf=self,
                start_y=54,
                items_list=self.original_rows or getattr(self, 'manifest_items', []),
                volume_map=volume_map,
                sec_level=sec,
                vessel=self.vessel
            )
        except Exception as e:
            print(f"[Auto-Boxing Manifest Page] Error: {e}")
            import traceback; traceback.print_exc()

    # ——— FULL-SIZE 3D ISOMETRIC CARGO GRID (FINAL SCHEMATIC PAGE) ———
    if ship_grid and "groups" in ship_grid and "PUBLIC" not in sec and "OPEN" not in sec:
        try:
            from cargo_grid_renderer import render_full_grid_page
            from storall_packer import calculate_cargo_breakdown

            items_list = getattr(self, "manifest_items", None) or getattr(self, "original_rows", [])
            bd_items = []
            for item in items_list:
                if isinstance(item, dict):
                    try:
                        q_val = int(float(str(item.get("qty", 0)).strip()))
                    except (ValueError, TypeError):
                        q_val = 0
                    if q_val <= 0:
                        continue
                    entry = {
                        "name": item.get("name", ""),
                        "qty": q_val,
                        "box_size": item.get("box_size", ""),
                    }
                    bs = str(item.get("box_size", "")).strip().upper()
                    if "SCU" in bs:
                        try:
                            scu_val = float(bs.replace("SCU", "").strip())
                            entry["vol_override"] = scu_val
                        except ValueError:
                            pass
                    bd_items.append(entry)

            breakdown = calculate_cargo_breakdown(bd_items, vessel=self.vessel)
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



# SECTION 5: Resource Path + Font Cache

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
    def footer(self):
        self.set_y(-10)
        try: self.set_font("Roboto", "", 7)
        except Exception: self.set_font("Helvetica", "", 7)
        self.set_text_color(120, 130, 145)
        self.cell(0, 8, f"Page {self.page_no()}", border=0, ln=0, align="C")


    def add_font(self, family, style='', fname='', uni=True):
        try:
            try:
                super().add_font(family, style=style, fname=fname, uni=uni)
            except TypeError:
                super().add_font(family, style=style, fname=fname)
        except Exception as e:
            print(f"[PDF_ENGINE] add_font error for {family} {style}: {e}", file=__import__('sys').stderr)

    
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
            self.font_family_name = "Roboto"
        self.original_rows = []
        if not hasattr(self, 'security_level'):
            self.security_level = 'ALL'
        try:
            import path_config
            font_dir = path_config.PATHS.fonts
            if not os.path.exists(font_dir):
                font_dir = os.path.join(path_config.PATHS.app_root, 'fonts')
            regular = os.path.join(font_dir, 'Roboto-Regular.ttf')
            bold = os.path.join(font_dir, 'Roboto-Bold.ttf')

            if os.path.exists(regular):
                try: self.add_font('Roboto', '', regular)
                except Exception: pass
                try: self.add_font('Roboto', 'I', regular)
                except Exception: pass

            if os.path.exists(bold):
                try: self.add_font('Roboto', 'B', bold)
                except Exception: pass
                try: self.add_font('Roboto', 'BI', bold)
                except Exception: pass
            elif os.path.exists(regular):
                try: self.add_font('Roboto', 'B', regular)
                except Exception: pass
                try: self.add_font('Roboto', 'BI', regular)
                except Exception: pass
        except Exception:
            pass

    def draw_table_row(self, pdf_row_index, name, box_size, qty, price, is_courtesy, total, unit, total_volume):
        # Force numeric types to avoid '>' str vs int errors in main.pyc
        try:
            qty_str = str(qty).strip()
            if not qty_str or qty_str == '0':
                qty = 0
            else:
                qty = int(float(qty_str))
        except Exception:
            qty = 0
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
        official_uniform_prefixes = [
            "tcs-4", "tailwind", "omni-afs", "adp-mk4", "orc-mkx", "cq7", 
            "field recon", "csp-68", "aril", "adiva jacket", "lemarque pants",
            "deo shirt", "prim shoes", "ventra gloves", "horizon", "beacon", "stoneface",
            "novikov", "calva", "stoneskin", "stitcher", "defiance", "truedef", "morozov"
        ]
        official_weapon_prefixes = [
            "fs-9", "p4-ar", "f55", "p8-ar", "p6-lr", "br2", "p8-sc", "s-38",
            "a03", "lh86", "arclight", "custodian", "karna", "gallant", "coda",
            "salvage", "tractor", "cambio", "maxlift", "paramed", "lifeguard", 
            "medpen", "oxypen", "flare", "cruz", "pyro rmc", "multitool", "multi-tool"
        ]
        
        for r in self.original_rows:
            name_low = r['name'].lower().strip()
            is_uniform = any(w in name_low for w in ["suit", "helmet", "core", "arms", "legs", "backpack", "jacket", "pants", "shirt", "shoes", "gloves", "undersuit"])
            is_weapon = any(w in name_low for w in ["rifle", "pistol", "smg", "lmg", "shotgun", "sniper", "magazine", "cq7", "coda", "gun"])
            
            if is_uniform:
                is_off = any(p in name_low for p in official_uniform_prefixes)
                if not is_off:
                    r['name'] = r['name'] + " [UNOFFICIAL EQ]"
            elif is_weapon:
                clean_name = name_low.replace('"', '').strip()
                is_off_w = any(p in clean_name for p in official_weapon_prefixes)
                if not is_off_w:
                    r['name'] = r['name'] + " [UNOFFICIAL EQ]"

        # ── Auto-boxing: ONLY for items that are truly loose (unit box_size) ──
        # Skip items that already have a Stor-All / SCU box_size assigned
        total_loose_vol = 0.0
        has_existing_storall = any('stor' in r['name'].lower() for r in self.original_rows)
        from storall_packer import get_item_unit_volume
        for r in self.original_rows:
            name_low = r['name'].lower()
            box_low = str(r.get('box_size', '')).lower()
            # Skip if already in SCU-sized container (not loose)
            if 'scu' in box_low or 'stor' in name_low:
                continue
            qty = int(r.get('qty', 1)) if str(r.get('qty', 1)).isdigit() else 1
            total_loose_vol += qty * get_item_unit_volume(r['name'])

        # Only add auto-boxes if there are loose items AND no existing Stor-All in cargo
        boxes_to_add = []
        if total_loose_vol > 0.001 and not has_existing_storall:
            from storall_packer import pack_items
            v_name = getattr(self, "vessel", "")
            pack_res = pack_items(self.original_rows, vessel=v_name)
            num_b = pack_res.get("num_boxes", 0)
            if num_b > 0:
                box_labels = pack_res.get("box_labels", [])
                STOR_PRICES = {'1 SCU': 2100, '2 SCU': 4250, '4 SCU': 8500, '8 SCU': 15960, '16 SCU': 32000}
                for idx in range(num_b):
                    custom_lbl = box_labels[idx] if idx < len(box_labels) else pack_res.get("box_label", "1 SCU")
                    b_name = f"Stor-All [{custom_lbl}] Container"
                    b_size = "2 SCU" if "CAPITAL" in custom_lbl or len(box_labels) > 1 else "1 SCU"
                    b_price = STOR_PRICES.get(b_size, 2100)
                    boxes_to_add.append((b_name, b_size, 2.0 if b_size == "2 SCU" else 1.0))
                    self.original_rows.append({
                        'pdf_row_index': len(self.original_rows) + 1,
                        'name': b_name,
                        'box_size': b_size,
                        'qty': '1',
                        'price': b_price,
                        'total_price': b_price,
                        'courtesy': False
                    })
        self._stor_all_boxes = boxes_to_add
            
        self.manifest_items = []
        sec = self.security_level.upper() if hasattr(self, 'security_level') else ''
        is_public = ('PUBLIC' in sec or 'OPEN' in sec)

        if is_public:
            # PUBLIC mode: group items by general category, hide specific item names and exact quantities
            cat_groups = {}
            for r in self.original_rows:
                gcat = _to_general_category(r['name'])
                if gcat not in cat_groups:
                    cat_groups[gcat] = {
                        'name': gcat,
                        'box_size': 'FREIGHT CONTAINER',
                        'qty': 0,
                        'price': 0.0,
                        'is_courtesy': False,
                        'unit': 'SCU',
                        'total_volume': 0.0
                    }
                qty_val = int(r['qty']) if str(r['qty']).isdigit() else 1
                cat_groups[gcat]['qty'] += qty_val
                cat_groups[gcat]['total_volume'] += float(r.get('total_volume', 0.0))

            pub_rows = sorted(cat_groups.values(), key=lambda x: x['name'])
            for idx, r in enumerate(pub_rows):
                self.manifest_items.append({
                    'name': r['name'],
                    'qty': 0,
                    'box_size': 'FREIGHT CONTAINER',
                    'total_volume': r['total_volume']
                })
                super().draw_table_row(
                    idx + 1,
                    str(r['name']),
                    'FREIGHT CONTAINER',
                    0,
                    0.0,
                    False,
                    0.0,
                    'SCU',
                    float(r['total_volume'])
                )
        else:
            row_idx_out = 0
            for idx, r in enumerate(self.original_rows):
                if not isinstance(r, dict):
                    continue
                try:
                    row_qty = int(float(str(r.get('qty', 1)).strip()))
                except Exception:
                    row_qty = 0
                if row_qty <= 0:
                    continue
                row_idx_out += 1
                row_price = float(r.get('price', 0.0))
                row_total = row_price * row_qty
                display_box_size = str(r.get('box_size', '1 SCU'))
                if 'unit' in display_box_size.lower():
                    display_box_size = 'LOOSE'
                
                # Correct unit volume for MedPens and loose items
                tot_vol = float(r.get('total_volume', 0.0))
                name_str = str(r.get('name', ''))
                name_low = name_str.lower()
                if any(x in name_low for x in ['medpen', 'hemozal', 'oxypen', 'adrenapen', 'corticopen']):
                    tot_vol = row_qty * 0.001

                is_courtesy_val = bool(r.get('is_courtesy') or r.get('courtesy') or False)
                unit_val = str(r.get('unit', 'unit'))

                self.manifest_items.append({
                    'name': name_str,
                    'qty': row_qty,
                    'box_size': display_box_size,
                    'total_volume': tot_vol,
                    'is_courtesy': is_courtesy_val,
                    'price': row_price,
                    'unit': unit_val
                })
                super().draw_table_row(
                    row_idx_out,
                    name_str,
                    display_box_size,
                    row_qty,
                    row_price,
                    is_courtesy_val,
                    float(row_total),
                    unit_val,
                    float(tot_vol)
                )

            
        super().draw_table_footer(grand_total)

    def cell(self, w, h, txt='', border=0, ln=0, align='', fill=False, link=''):
        sec = self.security_level.upper() if hasattr(self, 'security_level') else ''
        redacted = False
        txt_clean = txt.strip().upper() if txt else ''
        
        # ALL / CLASSIFIED = NO redaction — everything visible
        if 'ALL' in sec or 'CLASSIFIED' in sec or 'OFFICERS' in sec or 'ENCRYPTED' in sec:
            pass  # No redaction
        
        # PUBLIC: redact ~90% (names, prices, totals, locations, box quantities)
        elif 'PUBLIC' in sec or 'OPEN' in sec:
            # Names
            if self.captain and self.captain.strip() and self.captain.upper() in txt_clean: redacted = True
            elif self.loading_officer and self.loading_officer.strip() and self.loading_officer.upper() in txt_clean: redacted = True
            elif self.loading_crew and self.loading_crew.strip() and self.loading_crew.upper() in txt_clean: redacted = True
            # All price & quantity columns
            if w in [20, 22, 26, 30, 18, 16] and h == 7 and txt_clean and txt_clean not in ["UNIT AUEC", "TOTAL AUEC", "BOX QTY", "QTY"]: redacted = True
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
        
        if 'ALL' in sec or 'CLASSIFIED' in sec or 'OFFICERS' in sec or 'ENCRYPTED' in sec:
            pass
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
            self.image(barcode_file, x=145, y=36, w=48, h=10)

        # Classification Badge (colored pill)
        sec = self.security_level.upper() if hasattr(self, 'security_level') else ""
        badge_text = sec.replace("_", " ") if sec else "CLASSIFIED"
        badge_r, badge_g, badge_b = 180, 30, 30
        if not sec or sec == "ALL":
            badge_text = "INACTIVE CHANNEL"
            badge_r, badge_g, badge_b = 30, 30, 30
        elif "OFFICERS" in sec or "ENCRYPTED" in sec:
            badge_text = "OFFICERS ONLY"
            badge_r, badge_g, badge_b = 180, 30, 30
        elif "PUBLIC" in sec or "OPEN" in sec:
            badge_text = "OPEN TO PUBLIC"
            badge_r, badge_g, badge_b = 40, 140, 60
        elif "RESTRICTED" in sec or "SECURED" in sec:
            badge_text = "SECURED MEMBERS"
            badge_r, badge_g, badge_b = 200, 150, 30
        
        badge_w = self.get_string_width(badge_text) + 8
        self.set_fill_color(badge_r, badge_g, badge_b)
        self.rect(10, 29.5, badge_w, 5, 'F')
        self.set_text_color(255, 255, 255)
        try: self.set_font("Roboto", "B", 6)
        except Exception: self.set_font("Helvetica", "B", 6)
        super().text(14, 33, badge_text)

        # Watermark overlay
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
                    wm_w = 130
                    wm_x = (210 - wm_w) / 2
                    wm_y = 85
                    self.image(wm_path, x=wm_x, y=wm_y, w=wm_w)
                except Exception as e:
                    print(f"[Watermark] {e}")
        self.set_text_color(0, 0, 0)

        # ── METADATA ROWS: positioned below header banner starting at y=36.5 ──
        req_id = getattr(self, 'req_id', '') or ''
        date_str = getattr(self, 'delivery_date', '') or ''
        vessel = getattr(self, 'vessel', '') or ''
        officer = getattr(self, 'loading_officer', '') or ''
        crew = getattr(self, 'loading_crew', '') or ''
        captain = getattr(self, 'captain', '') or ''
        station = getattr(self, 'location', '') or ''
        severity = getattr(self, 'severity', '') or ''
        loading_type = getattr(self, 'loading_type', '') or ''
        sec = str(getattr(self, 'security_level', '') or '').upper()
        is_pub = 'PUBLIC' in sec or 'OPEN' in sec

        try: self.set_font("Roboto", "B", 6)
        except Exception: self.set_font("Helvetica", "B", 6)
        self.set_text_color(30, 41, 59)

        meta_x = 10
        meta_y = 36.5
        line_h = 3.5

        # Row 1: VESSEL | STATION
        r1_parts = []
        if vessel:
            r1_parts.append(f"VESSEL: {'[REDACTED // CLASSIFIED]' if is_pub else vessel}")
        if station:
            ltype = f" ({loading_type})" if loading_type else ""
            r1_parts.append(f"STATION: {'[REDACTED // CLASSIFIED]' if is_pub else f'{station}{ltype}'}")
        if r1_parts:
            super().text(meta_x, meta_y, "  |  ".join(r1_parts))

        # Row 2: OFFICER | CAPTAIN | SEVERITY
        meta_y2 = meta_y + line_h
        r2_parts = []
        if officer:
            r2_parts.append(f"OFFICER: {'[REDACTED]' if is_pub else officer}")
        if captain and captain.strip():
            r2_parts.append(f"CAPTAIN: {'[REDACTED]' if is_pub else captain}")
        if severity:
            r2_parts.append(f"SEVERITY: {severity}")
        if r2_parts:
            super().text(meta_x, meta_y2, "  |  ".join(r2_parts))

        # Row 3: CREW | DATE
        meta_y3 = meta_y2 + line_h
        r3_parts = []
        if crew and crew.strip().upper() not in ["NONE", "PENDING", ""]:
            r3_parts.append(f"CREW: {'[REDACTED]' if is_pub else crew}")
        if date_str:
            r3_parts.append(f"DELIVERY DATE: {'[REDACTED // CLASSIFIED]' if is_pub else date_str}")
        if r3_parts:
            super().text(meta_x, meta_y3, "  |  ".join(r3_parts))

        # Row 4: LEDGER HASH / REQ ID (SINGLE ENTRY ONLY!)
        meta_y4 = meta_y3 + line_h
        if req_id:
            super().text(meta_x, meta_y4, f"LEDGER HASH: {req_id}")

        self.set_y(53)


main.MilitaryPDF = PatchedMilitaryPDF

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: Direct Supply Route PDF Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_pdf_direct(self, save_path=None):
    """Generate Supply Route PDF directly using fpdf. Instant, no main.pyc."""
    import fpdf
    import time as _time
    from tkinter import filedialog, messagebox

    _pdf_start_time = _time.perf_counter()

    def _safe_str(obj, attr_list, fallback=""):
        for a in attr_list:
            if hasattr(obj, a):
                v = getattr(obj, a)
                if v is not None:
                    if hasattr(v, 'get') and callable(getattr(v, 'get')):
                        try:
                            res = str(v.get() or "").strip()
                            if res: return res
                        except Exception: pass
                    elif isinstance(v, str) and v.strip():
                        return v.strip()
        return fallback

    # Safely bind vessel and metadata attributes on app (self)
    vessel_val = _safe_str(self, ['vessel', 'ship_selector', 'vessel_var'], '')
    self.vessel = vessel_val
    self.loading_officer = _safe_str(self, ['loading_officer', 'loading_officer_var'], '')
    self.captain = _safe_str(self, ['captain', 'captain_var'], '')
    self.loading_crew = _safe_str(self, ['loading_crew', 'loading_crew_var'], '')
    self.location = _safe_str(self, ['location', 'location_var'], '')

    _ensure_trade_dbs()  # Lazy-load trade databases
    # Rebind after lazy-load (from-import copies reference at import time)
    import uex_sync as _uex
    _uex_trade_db_local = _uex._uex_trade_db or {}
    _uex_items_trade_db_local = _uex._uex_items_trade_db or {}

    
    # Collect items from cargo table
    items = []
    for row in getattr(self, 'cargo_rows', []):
        name = row['name_var'].get().strip() if hasattr(row.get('name_var'), 'get') else str(row.get('name_var', '')).strip()
        qty_str = row['qty_var'].get().strip() if hasattr(row.get('qty_var'), 'get') else str(row.get('qty_var', '')).strip()
        unit = row.get('unit', 'unit')
        box_size = row['box_size_var'].get().strip() if 'box_size_var' in row and hasattr(row['box_size_var'], 'get') else str(row.get('box_size_var', '1 SCU')).strip()
        price_str = row.get('price_var', None)
        if price_str and hasattr(price_str, 'get'):
            try: price_str = price_str.get().strip()
            except Exception: price_str = '0'
        else:
            price_str = str(price_str or '0').strip()
        courtesy = row.get('courtesy_var', None)
        is_courtesy = False
        if courtesy and hasattr(courtesy, 'get'):
            try: is_courtesy = bool(courtesy.get())
            except Exception: is_courtesy = False
        
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
        try: messagebox.showerror("Error", "Cargo table is empty!")
        except Exception: pass
        return
    
    # ── Auto-boxing: calculate Stor-All boxes for loose items using storall_packer ──
    from storall_packer import pack_items
    has_existing_storall = any('stor' in item['name'].lower() for item in items)
    boxes_to_add = []
    total_loose_vol = 0.0
    if not has_existing_storall:
        pack_res = pack_items(items, vessel=self.vessel)
        total_loose_vol = pack_res.get("total_loose_vol", 0.0)
        num_b = pack_res.get("num_boxes", 0)
        if num_b > 0:
            box_labels = pack_res.get("box_labels", [])
            for idx in range(num_b):
                custom_lbl = box_labels[idx] if idx < len(box_labels) else pack_res.get("box_label", "1 SCU")
                b_name = f"Stor-All [{custom_lbl}] Container"
                boxes_to_add.append((b_name, "2 SCU" if "CAPITAL" in custom_lbl or len(box_labels) > 1 else "1 SCU"))
    
    STOR_PRICES = {
        "1 SCU": 2100, "2 SCU": 4250, "4 SCU": 8500, "8 SCU": 15960, "16 SCU": 32000
    }
    for box_name, box_size in boxes_to_add:
        price_val = STOR_PRICES.get(box_size, 1500)
        items.append({
            'name': box_name, 'qty': 1, 'unit': 'SCU',
            'box_size': box_size, 'price': price_val, 'is_courtesy': False
        })
    
    # Calculate cargo breakdown using storall_packer
    bd_items = [{"name": i["name"], "qty": i["qty"], "box_size": i.get("box_size", "")} for i in items if isinstance(i, dict)]
    cargo_breakdown = calculate_cargo_breakdown(bd_items, vessel=self.vessel)

    # Get classification for filename
    classification_pre = _safe_str(self, ['_classify_var', 'classification'], 'ALL')
    req_id_pre = _safe_str(self, ['req_id_var', 'req_id'], 'SR')
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
    req_id = _safe_str(self, ['req_id_var', 'req_id'], 'N/A')
    vessel = self.vessel
    officer = self.loading_officer
    captain = self.captain
    crew = self.loading_crew
    location = self.location
    classification = _safe_str(self, ['_classify_var', 'classification'], 'ALL')
    severity = _safe_str(self, ['severity_var', 'severity'], 'NOMINAL')
    delivery = _safe_str(self, ['delivery_date_var', 'delivery_date'], '')
    mission = _safe_str(self, ['mission_var', 'mission'], '')
    
    # ── EVA Logic & Nearest Station ──
    is_eva = False
    loc_low = location.lower() if location else ""
    if any(kw in loc_low for kw in ["l1", "l2", "l3", "l4", "l5", "orbit", "space", "jump point", "comm array"]):
        is_eva = True

    shuttle_rec = None
    if is_eva:
        sdb = _load_uex_ships_db()
        shuttle_rec = _recommend_shuttle(vessel, cargo_breakdown.get("total_vol", 0), sdb)
        if shuttle_rec and shuttle_rec.get("trips", 0) > 2:
            cargo_ship = _recommend_cargo_ship(cargo_breakdown.get("total_vol", 0), sdb)
            if cargo_ship:
                shuttle_rec = cargo_ship
                shuttle_rec["is_override"] = True
    # Build PDF
    pdf = fpdf.FPDF('P', 'mm', 'A4')
    pdf._is_supply_route = True
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=False)

    def check_page_break(current_y, required_space):
        if current_y + required_space > 275:
            pdf.add_page()
            pdf.set_fill_color(245, 238, 220)
            pdf.rect(0, 0, 210, 297, 'F')
            pdf.set_draw_color(180, 150, 60)
            pdf.set_line_width(1.5)
            pdf.rect(5, 5, 200, 287)
            pdf.set_line_width(0.3)
            pdf.rect(7, 7, 196, 283)
            # Page header
            pdf.set_fill_color(15, 30, 60)
            pdf.rect(8, 6, 194, 22, 'F')
            pdf.set_draw_color(180, 150, 60)
            pdf.set_line_width(0.5)
            pdf.line(8, 28, 202, 28)
            try: pdf.set_font("Roboto", "B", 12)
            except: pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(255, 255, 255)
            pdf.text(32, 16, "44th BATTLEGROUP // SUPPLY ROUTE (CONT.)")
            return 35
        return current_y
    
    # Note: _FONT_CACHE injection disabled — fpdf2 font subsetting 
    # breaks when sharing font objects between instances.
    
    pdf.add_page()
    
    # — PAGE BACKGROUND (white, same as manifest) —
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, 210, 297, 'F')
    
    # — HEADER (military style, same as manifest) —
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
    # Classification badge
    sec_upper = classification.upper()
    badge_text = "CLASSIFIED"
    badge_r, badge_g, badge_b = 180, 30, 30
    if sec_upper == "ALL" or not sec_upper:
        badge_text = "INACTIVE CHANNEL"
        badge_r, badge_g, badge_b = 30, 30, 30
    elif sec_upper == "CLASSIFIED":
        badge_text = "STARLIFTERS ONLY"
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
    
    # — METADATA ROWS (compact, fluid layout) —
    try: pdf.set_font("Roboto", "", 5)
    except Exception: pdf.set_font("Helvetica", "", 5)
    pdf.set_text_color(80, 90, 110)
    
    meta_x = badge_w + 16
    meta_y = 30.5
    line_h = 3.6
    current_meta_y = meta_y
    
    loading_type = self.loading_type_var.get() if hasattr(self, 'loading_type_var') else ''
    sec = str(classification or '').upper()
    is_pub = 'PUBLIC' in sec or 'OPEN' in sec
    
    # Row 1: VESSEL | STATION
    r1_parts = []
    if vessel:
        r1_parts.append(f"VESSEL: {'[REDACTED // CLASSIFIED]' if is_pub else vessel}")
    if location:
        ltype = f" ({loading_type})" if loading_type else ""
        r1_parts.append(f"STATION: {'[REDACTED // CLASSIFIED]' if is_pub else f'{location}{ltype}'}")
    if r1_parts:
        pdf.text(meta_x, current_meta_y, "  |  ".join(r1_parts))
        current_meta_y += line_h
    
    # Row 2: OFFICER | CAPTAIN | SEVERITY
    r2_parts = []
    if officer:
        r2_parts.append(f"OFFICER: {'[REDACTED]' if is_pub else officer}")
    if captain and captain.strip():
        r2_parts.append(f"CAPTAIN: {'[REDACTED]' if is_pub else captain}")
    if severity:
        r2_parts.append(f"SEVERITY: {severity}")
    if r2_parts:
        pdf.text(meta_x, current_meta_y, "  |  ".join(r2_parts))
        current_meta_y += line_h
    
    # Row 3: CREW | DATE | REQ | OP/NOTES
    r3_parts = []
    if crew and crew.strip().upper() not in ["NONE", "PENDING", ""]:
        r3_parts.append(f"CREW: {'[REDACTED]' if is_pub else crew}")
    if delivery:
        r3_parts.append(f"DELIVERY DATE: {'[REDACTED // CLASSIFIED]' if is_pub else delivery}")
    if req_id:
        r3_parts.append(f"REQ: {req_id}")
    if mission and mission.strip():
        r3_parts.append(f"OP/NOTES: {'[REDACTED // CLASSIFIED]' if is_pub else mission.strip()}")
    if r3_parts:
        pdf.text(meta_x, current_meta_y, "  |  ".join(r3_parts))
        current_meta_y += line_h

    # Ledger hash (positioned fluidly below metadata rows without overlap)
    import random as _sr_rng_mod
    _sr_rng = _sr_rng_mod.Random(hash(req_id) if req_id else 42)
    sr_hid = f"{_sr_rng.choice(['REQ','SEC','LOG','TAC','NAV'])}-{_sr_rng.choice(['44BG','UEE-9N','FLEET-44'])}-{_sr_rng.randint(10000,99999)}-{_sr_rng.choice(['ALPHA','BRAVO','X-RAY','OMEGA'])}"
    hash_y = max(42.5, current_meta_y + 1.5)
    try: pdf.set_font("Roboto", "B", 5)
    except Exception: pdf.set_font("Helvetica", "B", 5)
    pdf.set_text_color(100, 116, 139)
    pdf.text(10, hash_y, f"LEDGER HASH: {sr_hid}")
    
    # — PROCUREMENT ROUTE (rendered fluidly below metadata & ledger hash) —
    table_y = max(50.0, hash_y + 6.0)
    
    # Build procurement data: find where to buy each item
    # Determine loading location's system + planet for proximity sorting
    from sc_wiki_db import _guess_planet, _guess_system, get_best_buy_location
    raw_origin = (location or "").lower().strip()
    
    loading_system = _guess_system("", raw_origin)
    if loading_system == "pyro":
        loading_planet = "monox"
        origin = location if location else "Deep Space (Pyro)"
    elif loading_system == "nyx":
        loading_planet = "delamar"
        origin = location if location else "Deep Space (Nyx)"
    else:
        loading_planet = _guess_planet(raw_origin) or "microtech"
        origin = location if location else "Deep Space (Stanton)"
    
    # Realistic QT distances in minutes between planets/moons within Stanton
    _STANTON_QT_MINS = {
        ("hurston", "arccorp"): 6,
        ("hurston", "crusader"): 8,
        ("hurston", "microtech"): 14,
        ("arccorp", "crusader"): 5,
        ("arccorp", "microtech"): 11,
        ("crusader", "microtech"): 9,
    }
    _SYSTEM_JUMP_PENALTY = {
        ("stanton", "pyro"): 50,
        ("stanton", "nyx"): 80,
        ("pyro", "nyx"): 40,
    }
    
    def _get_terminal_info(terminal_name):
        """Get (system, planet) for a terminal name from locations DB.
        
        Gateway terminals are named after the DESTINATION system but physically
        located in the DEPARTURE system shown in parentheses:
          'Cargo Supplies Pyro Gateway (Stanton)' -> IN Stanton
          'Cargo Supplies Stanton Gateway (Pyro)' -> IN Pyro
          'Cargo Services Pyro Gateway (Nyx)'     -> IN Nyx
        """
        tn = terminal_name.lower()
        # 1. GATEWAY TERMINALS: resolve from parenthetical system tag FIRST
        #    The word "Pyro" in "Pyro Gateway (Stanton)" does NOT mean Pyro system!
        is_gateway = ("gateway" in tn or "gtwy" in tn)
        if is_gateway:
            if "(stanton)" in tn:
                return "stanton", "gateway"
            if "(pyro)" in tn:
                return "pyro", "gateway"
            if "(nyx)" in tn:
                return "nyx", "gateway"
            # No parenthetical tag: infer from gateway name
            if "stanton gateway" in tn or "stanton gtwy" in tn:
                return "pyro", "gateway"  # Stanton Gateway = IN Pyro
            if "pyro gateway" in tn or "pyro gtwy" in tn:
                return "stanton", "gateway"  # Pyro Gateway = IN Stanton
            if "nyx gateway" in tn or "nyx gtwy" in tn:
                return "stanton", "gateway"  # Nyx Gateway = IN Stanton
            return "stanton", "gateway"
        # 2. Non-gateway: Pyro system locations
        if "checkmate" in tn or "monox" in tn or "bloom" in tn or "orbituary" in tn or "ruin" in tn or "patchcity" in tn or "starlight" in tn or "gaslight" in tn or "megumi" in tn or "dudley" in tn:
            return "pyro", "monox"
        # 3. Nyx system locations
        if "levski" in tn or "delamar" in tn or "glaciem" in tn:
            return "nyx", "delamar"
        # 4. Stanton system locations
        if "stanton" in tn or "hurston" in tn or "crusader" in tn or "arccorp" in tn or "microtech" in tn or "everus" in tn or "babbage" in tn or "orison" in tn or "lorville" in tn or "tressler" in tn or "seraphim" in tn or "baijini" in tn or "orinth" in tn:
            return "stanton", _guess_planet(tn) or "microtech"
        for cat_locs in _uex_locations_db.values():
            if isinstance(cat_locs, dict):
                for loc_name, loc_info in cat_locs.items():
                    if loc_name.lower() in tn or tn in loc_name.lower():
                        sys = (loc_info.get("system") or "stanton").lower()
                        pla = (loc_info.get("planet") or "").lower()
                        return sys, pla
        return "stanton", ""
    
    def _is_surface_location(loc_name, ltype=""):
        n_low = (loc_name or "").lower().strip()
        t_low = (ltype or "").lower().strip()
        if any(k in t_low for k in ["planetary", "surface", "outpost", "ground"]):
            return True
        if any(k in t_low for k in ["eva", "orbit", "space station"]):
            return False

        orbital_keywords = [
            "tressler", "everus", "baijini", "seraphim", "olisar",
            "hur-l", "arc-l", "cru-l", "mic-l", "l1", "l2", "l3", "l4", "l5",
            "checkmate", "ruin station", "orbituary", "gateway", "gtwy",
            "space station", "orbital", "orbit", "float", "eva", "cargo deck",
            "refueling station"
        ]
        if any(k in n_low for k in orbital_keywords):
            return False
            
        surface_keywords = [
            "babbage", "lorville", "area18", "area 18", "orison", "levski",
            "outpost", "research", "mining", "facility", "site", "farm", "rayari",
            "shubin", "hdms", "arccorp mining", "brio", "orinth", "sunset mesa",
            "ostler", "jackson", "yang", "arid reach", "surface", "land"
        ]
        if any(k in n_low for k in surface_keywords):
            return True

        if "planetary" in t_low:
            return True
        return True

    def _qt_distance(terminal_name):
        t_sys, t_pla = _get_terminal_info(terminal_name)
        if t_sys != loading_system:
            pair = tuple(sorted([loading_system, t_sys]))
            penalty = _SYSTEM_JUMP_PENALTY.get(pair, 100)
            return penalty
        if not t_pla or not loading_planet:
            return 10
        if t_pla == loading_planet:
            is_load_surf = _is_surface_location(raw_origin, loading_type)
            is_term_surf = _is_surface_location(terminal_name)
            if is_load_surf and is_term_surf:
                return 1
            elif not is_load_surf and not is_term_surf:
                return 2
            else:
                return 3
        pair = tuple(sorted([loading_planet, t_pla]))
        return _STANTON_QT_MINS.get(pair, 12)
    
    from src.core.supply_manifest import enrich_location as _enrich_location
    
    procurement = []
    has_loose_items = total_loose_vol > 0.0001 if 'total_loose_vol' in dir() else False
    
    for item in items:
        iname = item['name']
        iname_low = iname.lower().strip()
        if 'stor' in iname_low and ('all' in iname_low or 'storage' in iname_low):
            has_loose_items = True
            continue
        from slang_helper import resolve_slang
        canonical_name = resolve_slang(iname)
    from sc_wiki_db import lookup_item, estimate_qt_minutes

    item_candidates = []
    crafted_directives = []
    unobtainable_directives = []

    for item in items:
        iname = item.get('name', '')
        qty = item.get('qty', 1)
        if not iname:
            continue
        iname_low = iname.lower().strip()
        if 'stor' in iname_low and ('all' in iname_low or 'storage' in iname_low):
            continue
        from slang_helper import resolve_slang
        canonical_name = resolve_slang(iname)

        cands = lookup_item(canonical_name, from_location=origin, from_system=loading_system or "stanton")
        if cands:
            item_candidates.append({
                "name": iname,
                "qty": qty,
                "cands": cands
            })
        else:
            # Unbuyable item: check if blueprint exists for crafting
            try:
                from src.core.crafting_helper import resolve_unbuyable_item
                craft_res = resolve_unbuyable_item(canonical_name, qty=qty)
            except Exception:
                craft_res = {"status": "UNOBTAINABLE_LOOT", "can_craft": False}

            if craft_res.get("can_craft"):
                crafted_directives.append({
                    "name": iname,
                    "qty": qty,
                    "blueprint": craft_res.get("blueprint"),
                    "materials": craft_res.get("materials", []),
                    "display": craft_res.get("display_directive")
                })
            else:
                unobtainable_directives.append({
                    "name": iname,
                    "qty": qty,
                    "display": "UNOBTAINABLE // NEEDS TO BE LOOTED (No vendor terminal & no blueprint available)"
                })

    def _get_candidate_hub(cand):
        t = cand.get("terminal", "")
        loc = cand.get("location", "")
        p = cand.get("parent", "")
        path = cand.get("full_buy_path", "")
        combined = f"{t} {loc} {p} {path}".lower()

        # 1. First check specific orbital stations and L-stations
        if "tressler" in combined: return "Port Tressler"
        elif "everus" in combined: return "Everus Harbor"
        elif "baijini" in combined: return "Baijini Point"
        elif "seraphim" in combined: return "Seraphim Station"
        elif "grimhex" in combined or "grim hex" in combined: return "Grim HEX"
        elif "checkmate" in combined: return "Checkmate Station"
        elif "ruin" in combined: return "Ruin Station"
        elif "brio" in combined: return "Brio's Breaker Yard (Daymar)"
        elif "samson" in combined: return "Samson & Son's (Wala)"
        elif "devlin" in combined: return "Devlin Scrap (Euterpe)"
        elif "orinth" in combined: return "Reclamation Orinth (Hurston)"

        # Check L-stations BEFORE planet names
        elif "hur-l" in combined:
            m = re.search(r'hur-l\d', combined)
            return m.group(0).upper() + " Station" if m else "HUR-L Station"
        elif "arc-l" in combined:
            m = re.search(r'arc-l\d', combined)
            return m.group(0).upper() + " Station" if m else "ARC-L Station"
        elif "cru-l" in combined:
            m = re.search(r'cru-l\d', combined)
            return m.group(0).upper() + " Station" if m else "CRU-L Station"
        elif "mic-l" in combined:
            m = re.search(r'mic-l\d', combined)
            return m.group(0).upper() + " Station" if m else "MIC-L Station"
        elif "nyx-l" in combined:
            m = re.search(r'nyx-l\d', combined)
            return m.group(0).upper() + " Station" if m else "NYX-L Station"

        # 2. Main Planetary Hubs / Cities
        elif any(k in combined for k in ["babbage", "new babbage", "the commons", "omega pro"]): return "New Babbage"
        elif any(k in combined for k in ["area18", "area 18", "arccorp", "cubby", "io tower", "astro armada", "dumper"]): return "Area 18"
        elif any(k in combined for k in ["orison", "providence", "august dunlow", "cousin crow", "covalex"]): return "Orison"
        elif any(k in combined for k in ["lorville", "tammany", "new deal", "m&v", "hdms"]): return "Lorville"
        elif any(k in combined for k in ["levski", "grand barter", "cordry", "teach's", "conscientious"]): return "Levski"
        elif "sunset mesa" in combined: return "Sunset Mesa (Monox)"
        elif "gaslight" in combined: return "Gaslight (Monox)"

        # Fallback to planet names
        elif "hurston" in combined: return "Lorville"
        elif "microtech" in combined: return "New Babbage"
        elif "arccorp" in combined: return "Area 18"
        elif "crusader" in combined: return "Orison"
        elif "delamar" in combined or "nyx" in combined: return "Levski"

        return loc if loc else (t if t else "Stanton Station")

    for it in item_candidates:
        for c in it["cands"]:
            c["base_hub"] = _get_candidate_hub(c)

    # 2. Select minimal set of hubs covering all items
    selected_hubs = []
    origin_hub = _get_candidate_hub({"location": origin, "terminal": origin})
    origin_matches = any(any(c["base_hub"] == origin_hub for c in it["cands"]) for it in item_candidates)
    if origin_matches:
        selected_hubs.append(origin_hub)

    assigned_purchases = [None] * len(item_candidates)
    for idx, it in enumerate(item_candidates):
        for c in it["cands"]:
            if c["base_hub"] in selected_hubs:
                assigned_purchases[idx] = c
                break

    while any(p is None for p in assigned_purchases):
        unassigned_indices = [i for i, p in enumerate(assigned_purchases) if p is None]
        hub_coverage = {}
        for idx in unassigned_indices:
            it = item_candidates[idx]
            seen_hubs = set()
            for c in it["cands"]:
                h = c["base_hub"]
                if h not in seen_hubs and h not in selected_hubs:
                    seen_hubs.add(h)
                    hub_coverage[h] = hub_coverage.get(h, 0) + 1

        if not hub_coverage:
            for idx in unassigned_indices:
                if item_candidates[idx]["cands"]:
                    assigned_purchases[idx] = item_candidates[idx]["cands"][0]
            break

        last_hub = selected_hubs[-1] if selected_hubs else origin_hub
        best_hub = sorted(hub_coverage.keys(), key=lambda h: (-hub_coverage[h], estimate_qt_minutes(last_hub, h)))[0]
        selected_hubs.append(best_hub)

    # Co-locate companion items (batteries, canisters, attachments) with parent tools
    tool_parent_map = {
        "cambio multi-tool battery": ["cambio srt", "cambio", "pyro multi-tool", "multi-tool"],
        "cambio srt canister": ["cambio srt", "cambio"],
        "cambio srt battery": ["cambio srt", "cambio"],
        "maxlift tractor beam battery": ["maxlift tractor beam", "maxlift", "tractor beam"],
        "truhold tractor beam attachment": ["pyro multi-tool", "multi-tool", "cambio srt"],
        "orebit mining attachment": ["pyro multi-tool", "multi-tool"],
        "lifeguard medical attachment": ["pyro multi-tool", "multi-tool"],
    }

    # Find where parent tools are assigned
    parent_loc_map = {}
    for it, cand in zip(item_candidates, assigned_purchases):
        if not cand: continue
        it_low = it["name"].lower().strip()
        for c_item, p_keys in tool_parent_map.items():
            if any(pk in it_low for pk in p_keys) and not any(comp in it_low for comp in ["battery", "canister", "attachment"]):
                parent_loc_map[c_item] = cand

    # Re-assign companion items to parent shop if available at that hub
    for idx, (it, cand) in enumerate(zip(item_candidates, assigned_purchases)):
        it_low = it["name"].lower().strip()
        for c_item, p_cand in parent_loc_map.items():
            if c_item in it_low and p_cand:
                # Find matching candidate at same terminal or base hub
                p_term = p_cand.get("terminal", "")
                p_hub = p_cand.get("base_hub", "")
                for c in it["cands"]:
                    if c.get("terminal") == p_term or c.get("base_hub") == p_hub:
                        assigned_purchases[idx] = c
                        break

    procurement = []
    for it, cand in zip(item_candidates, assigned_purchases):
        if not cand:
            continue
        best_loc = cand.get("terminal") or cand.get("location")
        best_price = cand.get("price", 0)
        full_path = cand.get("full_buy_path") or _enrich_location(best_loc)
        qt = cand.get("qt_min", 10)

        from slang_helper import resolve_slang
        procurement.append({
            'name': resolve_slang(it['name']),
            'qty': it['qty'],
            'loc': full_path,
            'price': best_price,
            'raw_loc': best_loc,
            'base_hub': cand.get('base_hub', ''),
            'qt_min': qt,
        })

    def _normalize_base_location(loc_str):
        if not loc_str: return "Stanton > Port Tressler"
        s = str(loc_str).strip()
        s_low = s.lower()
        if any(k in s_low for k in ["pyro", "monox", "bloom", "checkmate", "orbituary", "ruin", "starlight", "patchcity", "sunset mesa", "gaslight"]):
            sys_prefix = "Pyro"
        elif any(k in s_low for k in ["nyx", "levski", "glaciem", "delamar"]):
            sys_prefix = "Nyx"
        else:
            sys_prefix = "Stanton"

        if "tressler" in s_low: main_loc = "Port Tressler"
        elif "everus" in s_low: main_loc = "Everus Harbor"
        elif "baijini" in s_low: main_loc = "Baijini Point"
        elif "seraphim" in s_low: main_loc = "Seraphim Station"
        elif "grimhex" in s_low or "grim hex" in s_low: main_loc = "Grim HEX"
        elif "checkmate" in s_low: main_loc = "Checkmate Station"
        elif "ruin" in s_low: main_loc = "Ruin Station"
        elif "brio" in s_low: main_loc = "Brio's Breaker Yard (Daymar)"
        elif "samson" in s_low: main_loc = "Samson & Son's (Wala)"
        elif "gaslight" in s_low: main_loc = "Gaslight (Monox)"
        elif "mic-l" in s_low:
            match = re.search(r'mic-l\d', s_low)
            main_loc = match.group(0).upper() if match else "MIC-L Station"
        elif "hur-l" in s_low:
            match = re.search(r'hur-l\d', s_low)
            main_loc = match.group(0).upper() if match else "HUR-L Station"
        elif "arc-l" in s_low:
            match = re.search(r'arc-l\d', s_low)
            main_loc = match.group(0).upper() if match else "ARC-L Station"
        elif "cru-l" in s_low:
            match = re.search(r'cru-l\d', s_low)
            main_loc = match.group(0).upper() if match else "CRU-L Station"
        else:
            parts = [p.strip() for p in s.split(' > ')] if ' > ' in s else [s]
            clean_p = [p for p in parts if p.lower() not in ["stanton", "pyro", "nyx"]]
            main_loc = clean_p[0] if clean_p else "Stanton Station"

        return f"{sys_prefix} > {main_loc}"

    if procurement:
        py = table_y + 3


        loc_groups = {}  # base_loc -> list of (shop_name, p)
        for p in procurement:
            loc_str = p['loc']
            parts = [s.strip() for s in loc_str.split(' > ')]
            if len(parts) >= 3:
                raw_base = " > ".join(parts[:-1])
                shop_name = parts[-1]
            else:
                raw_base = loc_str
                shop_name = ""
            base_loc = _normalize_base_location(raw_base)
            if base_loc not in loc_groups:
                loc_groups[base_loc] = []
            loc_groups[base_loc].append((shop_name, p))


        # 1-way proximity route sorting starting from origin
        def _get_qt_min(from_l, to_l):
            try:
                from sc_wiki_db import estimate_qt_minutes
                return estimate_qt_minutes(from_l, to_l)
            except Exception:
                return 10

        curr_loc = origin
        unvisited_locs = list(loc_groups.items())
        sorted_locs = []

        while unvisited_locs:
            best_idx = 0
            best_dist = 999999
            for idx, (b_loc, _) in enumerate(unvisited_locs):
                d = _get_qt_min(curr_loc, b_loc)
                if d < best_dist:
                    best_dist = d
                    best_idx = idx
            best_b_loc, best_pairs = unvisited_locs.pop(best_idx)
            sorted_locs.append((best_b_loc, best_pairs))
            curr_loc = best_b_loc

        if py < 245 and len(sorted_locs) >= 1:
            # Stor-All purchase as first stop if needed
            stor_all_stop = None
            if has_loose_items:
                def _find_real_storall_vendor(orig_loc):
                    orig_low = (orig_loc or "").lower().strip()
                    if "levski" in orig_low or "delamar" in orig_low:
                        return "Nyx > Levski > Grand Barter Cargo Deck"

                    if any(s in orig_low for s in ["pyro", "monox", "bloom", "checkmate", "orbituary"]):
                        system = "pyro"
                    elif any(s in orig_low for s in ["nyx", "levski", "delamar", "glaciem"]):
                        system = "nyx"
                    else:
                        system = "stanton"

                    real_terminals = []
                    if _uex_items_trade_db_local:
                        for k, v in _uex_items_trade_db_local.items():
                            if ("stor" in k or "storage" in k) and ("container" in k or "box" in k or "all" in k):
                                if isinstance(v, dict) and "locations" in v:
                                    for loc in v["locations"]:
                                        if isinstance(loc, dict) and loc.get("buy", 0) > 0:
                                            tname = loc.get("terminal", "")
                                            if tname and tname not in real_terminals:
                                                real_terminals.append(tname)

                    system_matches = []
                    for t in real_terminals:
                        t_low = t.lower()
                        is_gateway = "gtwy" in t_low or "gateway" in t_low
                        if system == "pyro" and ("pyro" in t_low or "(pyro)" in t_low or "checkmate" in t_low or "orbituary" in t_low) and not is_gateway:
                            system_matches.append(t)
                        elif system == "nyx" and ("levski" in t_low or "delamar" in t_low) and not is_gateway:
                            system_matches.append(t)
                        elif system == "stanton" and not ("(pyro)" in t_low or "(nyx)" in t_low or "orbituary" in t_low or "checkmate" in t_low) and not is_gateway:
                            system_matches.append(t)

                    is_surf_orig = _is_surface_location(orig_low, loading_type)
                    for sm in system_matches:
                        sm_low = sm.lower()
                        if any(k in orig_low for k in ["hurston", "lorville", "everus", "magda", "ita", "arial"]):
                            pref = ["lorville", "everus"] if is_surf_orig else ["everus", "lorville"]
                            for p in pref:
                                if p in sm_low: return sm
                        if any(k in orig_low for k in ["new babbage", "microtech", "tressler", "euterpe", "calliope", "clio"]):
                            pref = ["babbage", "tressler"] if is_surf_orig else ["tressler", "babbage"]
                            for p in pref:
                                if p in sm_low: return sm
                        if any(k in orig_low for k in ["arccorp", "area18", "area 18", "baijini", "wala", "lyria"]):
                            pref = ["area18", "area 18", "baijini"] if is_surf_orig else ["baijini", "area18", "area 18"]
                            for p in pref:
                                if p in sm_low: return sm
                        if any(k in orig_low for k in ["crusader", "orison", "seraphim", "daymar", "yela", "cellin"]):
                            pref = ["orison", "seraphim"] if is_surf_orig else ["seraphim", "orison"]
                            for p in pref:
                                if p in sm_low: return sm
                        if any(k in orig_low for k in ["pyro", "monox", "bloom", "checkmate", "orbituary", "ruin", "patchcity", "starlight"]) and any(k in sm_low for k in ["checkmate", "orbituary", "ruin", "patchcity", "starlight", "pyro"]): return sm
                        if any(k in orig_low for k in ["nyx", "levski", "glaciem", "delamar"]) and any(k in sm_low for k in ["levski", "delamar"]): return sm

                    if system_matches:
                        system_matches.sort(key=lambda t: _qt_distance(t))
                        return system_matches[0]
                    if system == "nyx":
                        return "Nyx > Levski > Grand Barter Cargo Deck"
                    if system == "pyro":
                        return "Pyro > Checkmate Station > Cargo Deck"
                    return real_terminals[0] if real_terminals else "Stanton > Port Tressler > Cargo Deck"

                stor_loc = _find_real_storall_vendor(origin)
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
                stop_idx = 1
            else:
                stor_all_stop = None
                stop_idx = 0

            def _resolve_shop_by_item_category(item_name, loc_formatted):
                iname_low = str(item_name).lower()
                loc_low = str(loc_formatted).lower()

                # Outposts & Salvage Yards
                if "sunset mesa" in loc_low: return "Sunset Mesa > Arms & Supplies"
                if "gaslight" in loc_low: return "Gaslight > Outpost Trade Post"
                if "orinth" in loc_low: return "Reclamation Orinth > Disposal Terminal"
                if "brio" in loc_low: return "Brio's Breaker Yard > Black Market Terminal"
                if "samson" in loc_low: return "Samson & Son's > Salvage Kiosk"
                if "devlin" in loc_low: return "Devlin Scrap > Salvage Trade Kiosk"
                if "rappel" in loc_low: return "Rappel Outpost > Trade Kiosk"
                if "swap" in loc_low or "jackson" in loc_low: return "Jackson's Swap > Outpost Trading Post"
                if "yang" in loc_low: return "Yang's Place > Scrapper Post"
                if "ostler" in loc_low: return "Ostler's Claim > Mining Vendor"
                if "dudley" in loc_low: return "Dudley & Daughters > Gunsmith Vendor"
                if "megumi" in loc_low: return "Guns Megumi > Arms Dealer"
                if "rod" in loc_low and "fuel" in loc_low: return "Rod's Fuel > Refueling Service"
                if "shubin" in loc_low:
                    if any(k in iname_low for k in ["tractor", "multitool", "cambio", "battery", "canister", "tool", "aril", "pembroke", "novikov"]):
                        return "Shubin Mining > Tool & Consumables Kiosk"
                    return "Shubin Mining > Trade Terminal"
                if "hdms" in loc_low:
                    if any(k in iname_low for k in ["tractor", "multitool", "cambio", "battery", "tool", "armor", "helmet", "core"]):
                        return "HDMS Logistics > Equipment Depot"
                    return "HDMS Logistics > Trade Terminal"
                if "rayari" in loc_low:
                    if any(k in iname_low for k in ["medpen", "hemozal", "oxypen", "paramed", "medkit", "pen"]):
                        return "Rayari Research > Bio-Medical Kiosk"
                    return "Rayari Research > Trade Terminal"
                if "arccorp mining" in loc_low or "mining area" in loc_low:
                    if any(k in iname_low for k in ["tractor", "multitool", "cambio", "battery", "tool"]):
                        return "ArcCorp Mining > Equipment Kiosk"
                    return "ArcCorp Mining > Commodity Terminal"

                # Clothing
                if any(k in iname_low for k in ["jacket", "pants", "shoes", "shirt", "gloves", "clothing", "gown", "hat", "cap"]):
                    if "lorville" in loc_low: return "Tammany and Sons"
                    return "Casaba Outlet"

                # Armor & FPS Gear
                if any(k in iname_low for k in ["armor", "helmet", "undersuit", "backpack", "core", "arms", "legs", "suit", "orc-", "adp-", "aril", "morozov", "stitcher", "novikov", "pembroke"]):
                    if "lorville" in loc_low: return "HD Armor"
                    if "area18" in loc_low: return "Cubby Blast"
                    if "grimhex" in loc_low or "grim hex" in loc_low: return "Skutters"
                    if "checkmate" in loc_low: return "Gear Up"
                    if any(k in loc_low for k in ["everus", "tressler", "baijini", "seraphim", "hur-l", "arc-l", "cru-l", "mic-l", "nyx-l"]):
                        return "FPS Armor Shop"
                    return "Garrity Defense"

                # Weapons & Ammunition
                if any(k in iname_low for k in ["rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "magazine", "ammo", "grenade", "p4-ar", "fs-9", "s-38", "torpedo", "bomb", "missile"]):
                    if "ruin" in loc_low: return "Live Fire Weapons"
                    if "area18" in loc_low or "babbage" in loc_low: return "Center Mass"
                    if any(k in loc_low for k in ["everus", "tressler", "baijini", "seraphim", "hur-l", "arc-l", "cru-l", "mic-l", "nyx-l"]):
                        return "Live Fire Weapons"
                    return "Ship Weapons Shop"

                # Medical Supplies
                if any(k in iname_low for k in ["medpen", "hemozal", "oxypen", "adrenapen", "medkit", "paramed"]):
                    return "Pharmacy Clinic"

                # Cargo / Tools / Commodities
                return "Cargo Center Terminal"

            def _infer_fallback_shop(sample_items=None):
                if not sample_items:
                    return "Admin Center > Commodity & Freight Terminal"
                first_item = sample_items[0].get('name', '').lower() if isinstance(sample_items[0], dict) else str(sample_items[0]).lower()
                if any(k in first_item for k in ["fuel", "decoy", "noise"]):
                    return "Admin Center > Commodity & Freight Terminal"
                elif any(k in first_item for k in ["magazine", "mag", "rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "ammo", "ammunition"]):
                    return "Galleria Deck > Live Fire Weapons"
                elif any(k in first_item for k in ["rmc", "commodity", "titanium", "laranite", "quantanium", "scrap"]):
                    return "Admin Center > Commodity & Freight Terminal"
                elif any(k in first_item for k in ["stor-all", "storall", "storage container"]):
                    return "Cargo Deck > Stor-All Vendor"
                elif any(k in first_item for k in ["tractor", "maxlift", "cambio", "multitool", "battery", "canister", "srt"]):
                    return "Cargo Deck > Cargo Center Supplies"
                elif any(k in first_item for k in ["armor", "helmet", "core", "arms", "legs", "backpack", "undersuit", "orc-mkx", "adp-mk4", "recon", "tcs-4", "csp-68"]):
                    return "Galleria Deck > FPS Armor Shop"
                elif any(k in first_item for k in ["jacket", "shirt", "pants", "gloves", "shoes", "adiva", "lemarque", "deo", "prim", "ventra"]):
                    return "Galleria Deck > Casaba Outlet"
                elif any(k in first_item for k in ["shield", "generator", "power plant", "quantum drive", "cooler", "atlas", "crossfield", "ts-2", "fr-", "js-"]):
                    return "Cargo Deck > Platinum Bay"
                elif any(k in first_item for k in ["cannon", "repeater", "laser", "weapon", "m6a", "m7a", "m8a", "panther", "gatling", "missile", "torpedo"]):
                    return "Galleria Deck > Ship Weapons Shop"
                return "Admin Center > Commodity & Freight Terminal"

            def _clean_shop_name(s_in, sample_items=None):
                if not s_in:
                    return _infer_fallback_shop(sample_items)
                parts = [p.strip() for p in s_in.replace("->", ">").split(">") if p.strip()]
                if not parts:
                    return _infer_fallback_shop(sample_items)

                non_loc = [
                    p for p in parts if p.upper() not in [
                        "STANTON", "PYRO", "NYX", "HURSTON", "ARCCORP", "MICROTECH", "CRUSADER",
                        "EVERUS HARBOR", "PORT TRESSLER", "BAIJINI POINT", "SERAPHIM STATION",
                        "MIC-L1", "MIC-L2", "MIC-L3", "MIC-L4", "MIC-L5",
                        "HUR-L1", "HUR-L2", "HUR-L3", "HUR-L4", "HUR-L5",
                        "ARC-L1", "ARC-L2", "ARC-L3", "ARC-L4", "ARC-L5",
                        "CRU-L1", "CRU-L2", "CRU-L3", "CRU-L4", "CRU-L5",
                        "CHECKMATE STATION", "RUIN STATION", "GRIM HEX", "TERMINAL"
                    ]
                ]
                if not non_loc:
                    return _infer_fallback_shop(sample_items)

                last = non_loc[-1]
                l_low = last.lower()
                if "admin" in l_low or "commodity" in l_low or "freight" in l_low: return "Admin Center > Commodity Terminal"
                if "cubby" in l_low: return "Commercial District > Cubby Blast"
                if "center" in l_low and "mass" in l_low: return "Commercial District > Center Mass"
                if "tammany" in l_low: return "L19 District > Tammany and Sons"
                if "makau" in l_low: return "Cloudview Center > Makau Clothing"
                if "aparel" in l_low: return "Cloudview Center > Aparel Clothing"
                if "casaba" in l_low: return "Galleria Deck > Casaba Outlet"
                if "clothing" in l_low: return "Galleria Deck > Casaba Clothing"
                if "platinum bay" in l_low: return "Cargo Deck > Platinum Bay"
                if "platinum" in l_low: return "Admin Center > Commodity Terminal"
                if "omega" in l_low: return "The Commons > Omega Pro"
                if "cousin" in l_low: return "August Dunlow > Cousin Crow's"
                if "stor-all" in l_low or "storall" in l_low: return "Cargo Deck > Stor-All Vendor"
                if "fps armor" in l_low or "armor" in l_low: return "Galleria Deck > FPS Armor Shop"
                if "garrity" in l_low: return "Galleria Deck > Garrity Defense"
                if "skutters" in l_low or "skutter" in l_low: return "Concourse > Skutters"
                if "kc trending" in l_low or "trending" in l_low: return "Concourse > KC Trending"
                if "technotic" in l_low: return "Concourse > Technotic"
                if "old '38" in l_low or "old 38" in l_low: return "Concourse > Old '38 Bar"
                if "conscientious" in l_low: return "Grand Barter > Conscientious Objects"
                if "cordry" in l_low: return "Grand Barter > Cordry's Armor"
                if "teach" in l_low: return "Customs > Teach's Ship Shop"
                if "musain" in l_low: return "Grand Barter > Cafe Musain"
                if "grand barter" in l_low: return "Grand Barter > Marketplace Terminal"
                if "live fire" in l_low: return "Galleria Deck > Live Fire Weapons"
                if "gear up" in l_low: return "Galleria Deck > Gear Up"
                if "providence" in l_low: return "Providence Platform > Providence Surplus"
                if "dump" in l_low: return "Commercial District > Dumper's Depot"
                if "shubin" in l_low: return "The Commons > Shubin Interstellar"
                if "refueling" in l_low or "maintenance" in l_low: return "Admin Center > Commodity & Freight Terminal"
                if "ship weapons" in l_low: return "Galleria Deck > Ship Weapons Shop"
                if "cargo" in l_low or "supplies" in l_low: return "Cargo Deck > Cargo Center Supplies"
                if "kel-to" in l_low: return "NBIS Spaceport > Kel-To Pharmacy"
                if "ellroy" in l_low: return "The Commons > Ellroy's Drinks"

                # Infer deck & shop from item context if shop name is generic (e.g. 'Seraphim', 'Everus', etc.)
                if sample_items:
                    ctx_str = " ".join([str(x.get('name', '')).lower() for x in sample_items if isinstance(x, dict)])
                    if any(k in ctx_str for k in ['fuel', 'ammunition', 'ammo', 'countermeasure', 'decoy', 'noise', 'rmc', 'scrap', 'ore', 'copper', 'iron', 'quantainium', 'gold', 'titanium']):
                        return "Cargo Deck > Admin & Commodity Terminal"
                    if any(k in ctx_str for k in ['tractor beam', 'battery', 'cambio', 'maxlift', 'canister']):
                        return "Cargo Deck > Cargo Center Supplies"
                    if any(k in ctx_str for k in ['rifle', 'pistol', 'smg', 'lmg', 'sniper', 'shotgun', 'magazine']):
                        return "Galleria Deck > Live Fire Weapons"
                    if any(k in ctx_str for k in ['helmet', 'core', 'arms', 'legs', 'backpack', 'undersuit', 'armor']):
                        return "Galleria Deck > Garrity Defense"
                    if any(k in ctx_str for k in ['shield', 'cooler', 'power plant', 'quantum drive']):
                        return "Galleria Deck > Platinum Bay"

                return last.title() if last.isupper() else last

            def _split_location_details(raw_str, fallback_station="", shop_given=None, sample_items=None):
                target_str = str(fallback_station or raw_str or "Stanton > Port Tressler")
                sg = shop_given or ""
                clean_shop = _clean_shop_name(sg, sample_items) if sg and sg.upper() != "TERMINAL" else _clean_shop_name(raw_str, sample_items)
                
                t_low = target_str.lower()
                r_low = (raw_str or "").lower()
                combined_low = f"{t_low} {r_low}"

                if any(k in combined_low for k in ["pyro", "monox", "bloom", "checkmate", "orbituary", "ruin", "starlight", "patchcity", "sunset mesa", "gaslight"]):
                    sys_name = "Pyro"
                elif any(k in combined_low for k in ["nyx", "levski", "glaciem", "delamar", "porphyr", "vanguard", "gold horizon", "kepler", "nyx-l", "pssa", "pssd", "psst", "pssl", "pssk"]):
                    sys_name = "Nyx"
                else:
                    sys_name = "Stanton"

                loc_formatted = "Unknown Location"
                if "everus" in combined_low: loc_formatted = "Everus Harbor"
                elif "tressler" in combined_low: loc_formatted = "Port Tressler"
                elif "seraphim" in combined_low: loc_formatted = "Seraphim Station"
                elif "baijini" in combined_low: loc_formatted = "Baijini Point"
                elif "grimhex" in combined_low or "grim hex" in combined_low: loc_formatted = "Grim HEX"
                elif "checkmate" in combined_low: loc_formatted = "Checkmate Station"
                elif "ruin" in combined_low: loc_formatted = "Ruin Station"
                elif "patchcity" in combined_low: loc_formatted = "PatchCity Station"
                elif "starlight" in combined_low: loc_formatted = "Starlight Station"
                elif "brio" in combined_low: loc_formatted = "Brio's Breaker Yard (Daymar)"
                elif "samson" in combined_low: loc_formatted = "Samson & Son's (Wala)"
                elif "hur-l" in combined_low:
                    for num in ["1","2","3","4","5"]:
                        if f"hur-l{num}" in combined_low: loc_formatted = f"HUR-L{num} Station"; break
                elif "arc-l" in combined_low:
                    for num in ["1","2","3","4","5"]:
                        if f"arc-l{num}" in combined_low: loc_formatted = f"ARC-L{num} Station"; break
                elif "cru-l" in combined_low:
                    for num in ["1","2","3","4","5"]:
                        if f"cru-l{num}" in combined_low: loc_formatted = f"CRU-L{num} Station"; break
                elif "mic-l" in combined_low:
                    for num in ["1","2","3","4","5"]:
                        if f"mic-l{num}" in combined_low: loc_formatted = f"MIC-L{num} Station"; break
                elif any(k in combined_low for k in ["lorville", "tammany", "new deal", "m&v", "hurston"]): loc_formatted = "Hurston (Lorville)"
                elif any(k in combined_low for k in ["area18", "area 18", "arccorp", "cubby", "io tower", "astro armada", "dumper"]): loc_formatted = "ArcCorp (Area 18)"
                elif any(k in combined_low for k in ["babbage", "new babbage", "commons", "shubin", "omega", "microtech"]): loc_formatted = "microTech (New Babbage)"
                elif any(k in combined_low for k in ["orison", "providence", "crusader", "cousin", "covalex", "august"]): loc_formatted = "Crusader (Orison)"
                elif any(k in combined_low for k in ["levski", "delamar", "nyx"]): loc_formatted = "Delamar (Levski)"
                elif "sunset mesa" in combined_low: loc_formatted = "Monox (Sunset Mesa)"
                elif "gaslight" in combined_low: loc_formatted = "Monox (Gaslight)"
                else:
                    parts = [p.strip() for p in target_str.replace('->', '>').split('>')]
                    clean_p = [p for p in parts if p.lower() not in ["stanton", "pyro", "nyx", "galleria", "cargo deck"]]
                    loc_formatted = clean_p[-1] if clean_p else target_str

                return sys_name, loc_formatted, clean_shop

            # Render Table Header Bar
            def _render_route_table_header(current_y, is_cont=False):
                title_txt = f"OPTIMIZED ROUTE (CONT. FROM {origin.upper()}):" if is_cont else f"OPTIMIZED ROUTE ({origin.upper()}):"
                pdf.set_fill_color(25, 35, 56)
                pdf.rect(10, current_y, 190, 6, 'F')
                pdf.set_text_color(212, 175, 55)
                try: pdf.set_font("Roboto", "B", 6)
                except Exception: pdf.set_font("Helvetica", "B", 6)
                pdf.text(12, current_y + 4.2, title_txt)

                hdr_y = current_y + 6.5
                pdf.set_fill_color(35, 48, 72)
                pdf.rect(10, hdr_y, 190, 5.5, 'F')
                pdf.set_text_color(255, 255, 255)
                try: pdf.set_font("Roboto", "B", 5.5)
                except Exception: pdf.set_font("Helvetica", "B", 5.5)

                pdf.text(12, hdr_y + 3.8, "STOP #")
                pdf.text(28, hdr_y + 3.8, "SYSTEM")
                pdf.text(46, hdr_y + 3.8, "LOCATION / STATION")
                pdf.text(90, hdr_y + 3.8, "SHOP / TERMINAL")
                pdf.text(132, hdr_y + 3.8, "ITEMS TO PURCHASE")

                return hdr_y + 6.0

            redraw_y = _render_route_table_header(py, is_cont=False)
            row_idx = 0

            # Render STOP 0 (Stor-All containers) if loose items exist
            if stor_all_stop:
                stor_sys, stor_station, stor_shop = _split_location_details(stor_loc, stor_loc, "Cargo Deck > Stor-All Vendor", items)
                
                box_lines = []
                box_counts = {}
                for item in items:
                    ilow = item['name'].lower()
                    if 'stor' in ilow and ('all' in ilow or 'storage' in ilow):
                        box_counts[item['name']] = box_counts.get(item['name'], 0) + int(item['qty'])
                for b_name, b_count in box_counts.items():
                    box_lines.append(f"[ ] {b_count}x {b_name}")
                if not box_lines:
                    box_lines = ["[ ] 1x Stor-All Storage Container"]
                box_items_str = "\n".join(box_lines)
                h_box = len(box_lines) * 3.5
                h_loc0 = len(stor_station.split('\n')) * 3.2
                h_shop0 = len(stor_shop.split('\n')) * 3.2
                row_h0 = max(6.5, max(h_box, h_loc0, h_shop0) + 2.5)

                if redraw_y + row_h0 > 265:
                    pdf.add_page()
                    pdf.set_fill_color(255, 255, 255)
                    pdf.rect(0, 0, 210, 297, 'F')
                    redraw_y = _render_route_table_header(35, is_cont=True)

                bg_col = (248, 249, 250) if row_idx % 2 == 0 else (255, 255, 255)
                pdf.set_fill_color(*bg_col)
                pdf.set_draw_color(210, 218, 226)
                pdf.set_line_width(0.1)

                pdf.rect(10, redraw_y, 190, row_h0, 'DF')
                
                try: pdf.set_font("Roboto", "B", 5.5)
                except Exception: pdf.set_font("Helvetica", "B", 5.5)
                
                pdf.set_text_color(25, 35, 56)
                pdf.text(12, redraw_y + 4, "STOP 0")
                
                pdf.set_text_color(30, 50, 90)
                pdf.text(28, redraw_y + 4, stor_sys)

                pdf.set_text_color(20, 30, 50)
                pdf.set_xy(45, redraw_y + 1)
                pdf.multi_cell(43, 3.2, stor_station)

                pdf.set_text_color(15, 45, 80)
                pdf.set_xy(89, redraw_y + 1)
                pdf.multi_cell(41, 3.2, stor_shop)

                pdf.set_text_color(15, 20, 30)
                try: pdf.set_font("Roboto", "", 5.5)
                except Exception: pdf.set_font("Helvetica", "", 5.5)
                pdf.set_xy(131, redraw_y + 1)
                pdf.multi_cell(67, 3.2, box_items_str)
                redraw_y += row_h0
                row_idx += 1

            # Render Stops per Base Location with Multi-Page Continuous Item Flow
            stop_counter = stop_idx
            for b_loc, shop_pairs in sorted_locs:
                shop_normalized_map = {}
                sys_n = "Stanton"
                loc_n = "Stanton"

                for s_name, p in shop_pairs:
                    raw_l = p.get('raw_loc', b_loc)
                    sys_curr, loc_curr, shop_curr = _split_location_details(raw_l, b_loc, s_name, [p])
                    sys_n = sys_curr
                    loc_n = loc_curr
                    shop_normalized_map.setdefault(shop_curr, []).append(p)

                shop_names = list(shop_normalized_map.keys())
                items_lines = []

                for shop_n, s_items in shop_normalized_map.items():
                    items_lines.append(f"--- {shop_n.upper()} ---")
                    for it in s_items:
                        items_lines.append(f"   [ ] {it['qty']}x {it['name']}")

                if len(shop_names) > 1:
                    l_low = loc_n.lower()
                    if any(k in l_low for k in ["babbage", "area18", "lorville", "orison", "levski"]):
                        shop_n_combined = "City Outlets"
                    elif any(k in l_low for k in ["mesa", "gaslight", "swap", "claim", "reach", "brio", "samson", "hdms", "outpost", "facility"]):
                        shop_n_combined = "Outpost Outlets"
                    else:
                        shop_n_combined = "Station Decks"
                else:
                    shop_n_combined = shop_names[0] if shop_names else _infer_fallback_shop()

                # Dynamic multi-page line chunking so Page 1 is NEVER blank
                line_step = 3.5
                rem_lines = list(items_lines)
                is_first_chunk = True

                while rem_lines:
                    avail_h = 265 - redraw_y
                    if avail_h < 18.0:
                        # Page full, create new page
                        pdf.add_page()
                        pdf.set_fill_color(255, 255, 255)
                        pdf.rect(0, 0, 210, 297, 'F')
                        redraw_y = _render_route_table_header(35, is_cont=True)
                        avail_h = 265 - redraw_y

                    max_lines_fit = max(2, int((avail_h - 5.0) / line_step))
                    chunk_lines = rem_lines[:max_lines_fit]
                    rem_lines = rem_lines[max_lines_fit:]

                    chunk_str = "\n".join(chunk_lines)
                    chunk_h = max(6.5, (len(chunk_lines) * line_step) + 2.5)

                    bg_col = (248, 249, 250) if row_idx % 2 == 0 else (255, 255, 255)
                    pdf.set_fill_color(*bg_col)
                    pdf.set_draw_color(210, 218, 226)
                    pdf.set_line_width(0.1)
                    pdf.rect(10, redraw_y, 190, chunk_h, 'DF')

                    try: pdf.set_font("Roboto", "B", 5.5)
                    except Exception: pdf.set_font("Helvetica", "B", 5.5)
                    pdf.set_text_color(25, 35, 56)
                    stop_label = f"STOP {stop_counter}" if is_first_chunk else f"STOP {stop_counter} (CONT.)"
                    pdf.text(12, redraw_y + 4, stop_label)

                    pdf.set_text_color(30, 50, 90)
                    pdf.text(28, redraw_y + 4, sys_n)

                    pdf.set_text_color(20, 30, 50)
                    pdf.set_xy(45, redraw_y + 1)
                    pdf.multi_cell(43, 3.2, loc_n)

                    pdf.set_text_color(15, 45, 80)
                    pdf.set_xy(89, redraw_y + 1)
                    pdf.multi_cell(41, 3.2, shop_n_combined)

                    pdf.set_text_color(15, 20, 30)
                    try: pdf.set_font("Roboto", "", 5.5)
                    except Exception: pdf.set_font("Helvetica", "", 5.5)
                    pdf.set_xy(131, redraw_y + 1)
                    pdf.multi_cell(67, 3.2, chunk_str)

                    redraw_y += chunk_h
                    is_first_chunk = False

                stop_counter += 1
                row_idx += 1

            # Render Fabrication & Field Recovery Directives if present
            if crafted_directives:
                from src.core.crafting_helper import aggregate_required_materials, format_ore_volume
                craft_lines = []
                for cd in crafted_directives:
                    mats_summary = ", ".join(f"{m.get('vol_str', format_ore_volume(m['qty']))} {m['name']}" for m in cd.get("materials", []))
                    craft_lines.append(f"[FABRICATION] {cd['qty']}x {cd['name']} -> NEED TO BE CRAFTED (Blueprint: {cd.get('blueprint')}) | Mining Required: {mats_summary}")
                
                agg_mats = aggregate_required_materials(crafted_directives)
                if agg_mats:
                    agg_str = ", ".join(f"{m['vol_str']} {m['name']}" for m in agg_mats)
                    craft_lines.append(f"[MINING REQUISITION // TO BE MINED] Total Raw Ores: {agg_str} (Extraction via mining required; cannot be purchased).")

                h_craft = len(craft_lines) * 3.8 + 7.0
                if redraw_y + h_craft > 265:
                    pdf.add_page()
                    pdf.set_fill_color(255, 255, 255)
                    pdf.rect(0, 0, 210, 297, 'F')
                    redraw_y = 35

                pdf.set_fill_color(240, 248, 255)
                pdf.set_draw_color(70, 130, 180)
                pdf.set_line_width(0.15)
                pdf.rect(10, redraw_y, 190, h_craft, 'DF')

                try: pdf.set_font("Roboto", "B", 5.5)
                except Exception: pdf.set_font("Helvetica", "B", 5.5)
                pdf.set_text_color(20, 60, 120)
                pdf.text(12, redraw_y + 3.8, "DIRECTIVE // FABRICATION & MINING REQUISITION (RAW ORES MUST BE MINED - NOT BOUGHT):")

                try: pdf.set_font("Roboto", "", 5.0)
                except Exception: pdf.set_font("Helvetica", "", 5.0)
                pdf.set_text_color(30, 40, 60)
                pdf.set_xy(12, redraw_y + 4.8)
                pdf.multi_cell(186, 3.2, "\n".join(craft_lines))
                redraw_y += h_craft + 2.0

            if unobtainable_directives:
                unob_lines = []
                for ud in unobtainable_directives:
                    unob_lines.append(f"[FIELD RECOVERY] {ud['qty']}x {ud['name']} -> UNOBTAINABLE AT COMMERCIAL TERMINALS // NEEDS TO BE LOOTED")

                h_unob = len(unob_lines) * 3.5 + 6.0
                if redraw_y + h_unob > 265:
                    pdf.add_page()
                    pdf.set_fill_color(255, 255, 255)
                    pdf.rect(0, 0, 210, 297, 'F')
                    redraw_y = 35

                pdf.set_fill_color(255, 245, 245)
                pdf.set_draw_color(180, 70, 70)
                pdf.set_line_width(0.15)
                pdf.rect(10, redraw_y, 190, h_unob, 'DF')

                try: pdf.set_font("Roboto", "B", 5.5)
                except Exception: pdf.set_font("Helvetica", "B", 5.5)
                pdf.set_text_color(140, 30, 30)
                pdf.text(12, redraw_y + 3.8, "DIRECTIVE // UNOBTAINABLE ITEMS (Field scavenging / loot / recovery required):")

                try: pdf.set_font("Roboto", "", 5.0)
                except Exception: pdf.set_font("Helvetica", "", 5.0)
                pdf.set_text_color(60, 30, 30)
                pdf.set_xy(12, redraw_y + 4.8)
                pdf.multi_cell(186, 3.2, "\n".join(unob_lines))
                redraw_y += h_unob + 2.0

            table_y = redraw_y + 4
            if table_y > 230:
                pdf.add_page()
                table_y = 35
    
    # ── CARGO TABLE ──
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
    sec_check = str(classification_pre).upper()
    is_pub_mode = ("PUBLIC" in sec_check or "OPEN" in sec_check)

    crafted_names = {cd['name'].lower() for cd in (crafted_directives or [])}
    unobtainable_names = {ud['name'].lower() for ud in (unobtainable_directives or [])}

    table_rows_to_render = []
    if is_pub_mode:
        cat_items_map = {}
        for item in items:
            gcat = _to_general_category(item['name'])
            cat_items_map[gcat] = cat_items_map.get(gcat, 0) + 1
        table_rows_to_render = [
            {"name": gcat, "box_size": "Freight Container / Loose", "qty_str": "XXX", "price_str": "XXX aUEC", "total_str": "XXX", "is_courtesy": False}
            for gcat in sorted(cat_items_map.keys())
        ]
    else:
        for item in items:
            is_c = bool(item.get('is_courtesy'))
            iname_l = item['name'].lower().strip()
            if is_c:
                total = 0.0
                p_str = format_auec(0)
                t_str = format_auec(0)
            else:
                p_val = float(item['price']) if item.get('price') else 0.0
                if p_val > 0:
                    total = int(float(item['qty'])) * p_val
                    p_str = format_auec(p_val)
                    t_str = format_auec(total)
                elif any(cn in iname_l or iname_l in cn for cn in crafted_names):
                    total = 0.0
                    p_str = "NEED CRAFT"
                    t_str = "NEED CRAFT"
                elif any(un in iname_l or iname_l in un for un in unobtainable_names):
                    total = 0.0
                    p_str = "UNOBTAINABLE"
                    t_str = "LOOT ONLY"
                else:
                    total = 0.0
                    p_str = "CAN'T BUY"
                    t_str = "CAN'T BUY"
            
            grand_total += total
            table_rows_to_render.append({
                "name": item['name'][:40],
                "box_size": str(item['box_size']),
                "qty_str": str(item['qty']),
                "price_str": p_str,
                "total_str": t_str,
                "is_courtesy": is_c
            })

    for i, row in enumerate(table_rows_to_render):
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

            # Re-draw Table Header on continuation page
            hdr_y = 15
            pdf.set_fill_color(25, 32, 45)
            pdf.rect(10, hdr_y, 190, 7, 'F')
            pdf.set_text_color(200, 168, 78)
            try: pdf.set_font("Roboto", "B", 6.5)
            except Exception: pdf.set_font("Helvetica", "B", 6.5)
            for label, x in cols:
                pdf.text(x, hdr_y + 5, label)
            row_y = hdr_y + 8
        
        # Alternating row colors
        if i % 2 == 0: pdf.set_fill_color(235, 228, 210)
        else: pdf.set_fill_color(245, 238, 220)
        pdf.rect(10, row_y - 1, 190, 6, 'F')
        
        # Row line
        pdf.set_draw_color(200, 185, 140)
        pdf.set_line_width(0.1)
        pdf.line(10, row_y + 5, 200, row_y + 5)
        
        pdf.set_text_color(40, 35, 25)
        pdf.text(12, row_y + 3.5, row['name'][:40])
        pdf.text(82, row_y + 3.5, str(row['box_size']))
        pdf.text(105, row_y + 3.5, str(row['qty_str']))
        
        pdf.text(118, row_y + 3.5, str(row['price_str']))
        pdf.text(148, row_y + 3.5, str(row['total_str']))
        
        if row.get('is_courtesy') or row.get('courtesy'):
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
    if is_pub_mode:
        pdf.text(12, row_y + 5, "TOTAL ITEMS: XXX")
        pdf.text(130, row_y + 5, "REQUIRED PAYMENT (NET): XXX aUEC")
    else:
        pdf.text(12, row_y + 5, f"TOTAL ITEMS: {len(items)}")
        pdf.text(130, row_y + 5, f"REQUIRED PAYMENT (NET): {grand_total:,.0f} aUEC")
    
    # ── FLEET PLANNER RECOMMENDATION IN SUPPLY ROUTE PDF (SINGLE UNIFIED BLOCK) ──
    fleet_rec_y = row_y + 8
    try:
        from fleet_helper import _recommend_cargo_ship
        def _safe_qty_num(v):
            try: return int(float(str(v).strip()))
            except Exception: return 1
        total_route_scu = sum(
            _safe_qty_num(i.get("qty", 1)) * (
                8 if "8 scu" in str(i.get("box_size", "")).lower()
                else 4 if "4 scu" in str(i.get("box_size", "")).lower()
                else 2 if "2 scu" in str(i.get("box_size", "")).lower()
                else 1 if "1 scu" in str(i.get("box_size", "")).lower()
                else 0.05
            )
            for i in items
        )
        cargo_rec = _recommend_cargo_ship(total_route_scu)
        if cargo_rec and "note" in cargo_rec:
            note_str = cargo_rec['note']
            note_str = note_str.replace("Crusader M2 Hercules Starlifter", "M2 Hercules")
            note_str = note_str.replace("Crusader C2 Hercules Starlifter", "C2 Hercules")
            note_str = note_str.replace("Crusader A2 Hercules Starlifter", "A2 Hercules")
            note_str = note_str.replace("MISC Hull B", "Hull B")
            note_str = note_str.replace("MISC Hull A", "Hull A")
            note_str = note_str.replace("RSI Constellation Taurus", "Connie Taurus")
            single_sentence = f"FLEET PLANNER ADVISORY: {note_str}"

            msg_len = len(single_sentence)
            box_h = 9.0 if msg_len > 120 else 6.0

            pdf.set_fill_color(15, 30, 60)
            pdf.rect(10, fleet_rec_y, 190, box_h, 'F')
            pdf.set_text_color(200, 168, 78)
            try: pdf.set_font("Roboto", "B", 5.5)
            except Exception: pdf.set_font("Helvetica", "B", 5.5)
            pdf.set_xy(12, fleet_rec_y + 1.2)
            pdf.multi_cell(186, 3.0, single_sentence)
            fleet_rec_y = max(fleet_rec_y + box_h + 2, pdf.get_y() + 2)

    except Exception as e:
        print(f"[SupplyRoute FleetPlanner] {e}")


    # ── UEE PROCUREMENT INVOICE BREAKDOWN (CLASSIFIED / OFFICERS ONLY) ──
    try:
        sec_up = classification.upper()
        if "OFFICERS" in sec_up or "ENCRYPTED" in sec_up or "CLASSIFIED" in sec_up or "ALL" in sec_up:
            inv_y = draw_classified_invoice_breakdown(pdf, fleet_rec_y, items, req_id=req_id, delivery_date=delivery)
            fleet_rec_y = inv_y + 2
    except Exception as e:
        print(f"[DynamicPDF InvoiceBreakdown] {e}")

    # ── AUTO-BOXING PACKING MANIFEST IN SUPPLY ROUTE PDF (ALWAYS 100% UNCLASSIFIED / FULLY OPEN) ──
    try:
        if has_loose_items:
            # Always pass OFFICERS_ONLY_ENCRYPTED / CLASSIFIED so items are 100% visible and unclassified in Supply Route
            ab_y = draw_autoboxing_packing_manifest(pdf, fleet_rec_y, items, volume_map, sec_level="OFFICERS_ONLY_ENCRYPTED", vessel=vessel)
            fleet_rec_y = ab_y + 2
    except Exception as e:
        print(f"[SupplyRoute AutoBoxing] {e}")

    # ── SIGNATURE ──
    sig_y = fleet_rec_y + 12
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
    
    # ── SIGNATURE BOX (Loading Officer - Supply Route PDF) ──
    box_w = 110
    box_h = 22
    left_x = 10

    pdf.set_line_width(0.2)
    pdf.set_draw_color(180, 190, 200)
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(left_x, sig_y, box_w, box_h, 'DF')
    pdf.set_draw_color(15, 30, 60)
    pdf.line(left_x, sig_y + 5.5, left_x + box_w, sig_y + 5.5)

    pdf.set_text_color(15, 30, 60)
    try: pdf.set_font("Roboto", "B", 7)
    except Exception: pdf.set_font("Helvetica", "B", 7)
    pdf.text(left_x + 3, sig_y + 4, "LOADING OFFICER SIGNATURE")

    try: pdf.set_font("Roboto", "", 6)
    except Exception: pdf.set_font("Helvetica", "", 6)
    pdf.set_text_color(40, 50, 70)
    pdf.text(left_x + 3, sig_y + 10, f"Name: {officer_clean}")
    pdf.text(left_x + 3, sig_y + 14, f"Rank: {officer_rank}")

    pdf.set_draw_color(160, 170, 185)
    pdf.set_line_width(0.15)
    pdf.line(left_x + 38, sig_y + 18, left_x + box_w - 4, sig_y + 18)

    podpisy_dir = get_signatures_dir()
    sig_file = process_signature(podpisy_dir, officer, is_captain=False)
    if sig_file and os.path.exists(sig_file):
        pdf.image(sig_file, x=left_x + 42, y=sig_y + 8, w=36, h=9)

    # R1 Stamp (right margin overlay)
    stamp_file = process_r1_stamp(podpisy_dir)
    if stamp_file and os.path.exists(stamp_file):
        pdf.image(stamp_file, x=160, y=sig_y - 2, w=22, h=22)
    
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

    tot_scu_route = max(total_scu, 1.0)
    shuttle_info = _recommend_shuttle(vessel, tot_scu_route, loading_type=loading_type, location=location)
    rec_text_route = shuttle_info["note"] if (shuttle_info and shuttle_info.get("note")) else ""

    if rec_text_route:
        pdf.set_fill_color(25, 35, 56)
        pdf.rect(10, notice_y + 6, 190, 14, 'F')
        pdf.set_draw_color(200, 168, 78)
        pdf.set_line_width(0.3)
        pdf.rect(10, notice_y + 6, 190, 14, 'D')

        try: pdf.set_font("Roboto", "B", 6)
        except Exception: pdf.set_font("Helvetica", "B", 6)
        pdf.set_text_color(212, 175, 55)
        pdf.text(13, notice_y + 10, "LOGISTICS DIRECTIVE & FLEET RECOMMENDATION")

        try: pdf.set_font("Roboto", "", 5.5)
        except Exception: pdf.set_font("Helvetica", "", 5.5)
        pdf.set_text_color(220, 230, 245)
        pdf.set_xy(12, notice_y + 11.5)
        pdf.multi_cell(186, 3.0, rec_text_route.replace('\n', ' ').strip())
    

    
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
    hash_y = max(sig_y + 38, notice_y + 16, pdf.get_y() + 4)
    pdf.text(82, hash_y, f"LEDGER HASH: {hash_id}")
    
    # Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬ SAVE Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬Ä‚ËĂ˘â‚¬ĹĄĂ˘â€šÂ¬
    try:
        pdf.output(save_path)
    except PermissionError as e:
        if hasattr(self, 'winfo_exists') and self.winfo_exists():
            messagebox.showerror("Error", f"Cannot save PDF (file in use?): {e}", parent=self)
        else:
            print(f"[PDF] PermissionError: {e}")
        return
    except Exception as e:
        # fpdf2 font subsetting may raise warnings about glyph names
        # but the PDF is usually still written. Check if file exists.
        if os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
            print(f"[PDF] Font subsetting warning (PDF saved OK): {e}")
        else:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                messagebox.showerror("Error", f"Failed to generate PDF: {e}", parent=self)
            else:
                print(f"[PDF] Failed to generate PDF: {e}")
            return

    # Only show success for single generation (not batch)
    _pdf_elapsed_ms = (_time.perf_counter() - _pdf_start_time) * 1000
    print(f"[PDF BENCHMARK] Total PDF Generation Time: {_pdf_elapsed_ms:.1f} ms")
    _is_batch = hasattr(self, '_gen3_running') and self._gen3_running
    _has_tk = hasattr(self, 'winfo_exists') and self.winfo_exists()
    if not _is_batch and _has_tk:
        messagebox.showinfo("Success", f"Supply Route PDF saved to:\n{save_path}\n\n[Benchmark: {_pdf_elapsed_ms:.0f} ms]", parent=self)
    elif not _is_batch:
        print(f"[PDF] Success: saved to {save_path} ({_pdf_elapsed_ms:.0f} ms)")



def _patched_generate_supply_route_pdf(self):
    """Direct PDF generation Ä‚ËĂ˘â€šÂ¬Ă˘â‚¬ĹĄ no main.pyc, instant."""
    generate_pdf_direct(self)



