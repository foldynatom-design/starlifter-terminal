# -*- coding: utf-8 -*-
"""
cargo_grid_renderer.py — Isometric 3D cargo grid visualization for PDF.

Loads ship grid data from ship_grids_db.json (SC-Cargo.space sourced),
performs fuzzy ship name matching, and renders isometric 3D cargo grids
with discrete cargo blocks (CMD/SUP/ORD/FREE) on the PDF.

Usage:
    from cargo_grid_renderer import load_ship_grid, render_full_grid_page
    from cargo_grid_renderer import render_grid_preview, render_cargo_directive

Data format (ship_grids_db.json):
    Each ship has groups (cargo bays), each group has grids (sub-volumes).
    Grid dimensions: width (x-axis), height (y-axis, stacking), length (z-axis).
    1 slot = 1 SCU.
"""

from path_config import PATHS

import os
import sys
import json
import math

# ── Lazy-loaded ship grid database ──
_grid_db_cache = None

# ── Ship manufacturer prefixes for name cleaning ──
_MANUFACTURER_PREFIXES = [
    "Aegis", "Anvil", "Drake", "RSI", "Crusader", "MISC", "Origin",
    "Consolidated Outland", "Argo", "Mirai", "Gatac", "Esperia",
    "Aopoa", "Banu", "Tumbril", "Greycat", "Musashi",
]

# ── Category colors (R, G, B) for cargo types ──
COLORS = {
    "CMD":  (76, 175, 80),    # green — commodities
    "SUP":  (66, 133, 244),   # blue  — supply (Stor-All)
    "ORD":  (211, 47, 47),    # red   — ordnance
    "FREE": (158, 158, 158),  # grey  — empty space
}

# Darker shades for isometric right face
COLORS_DARK = {
    "CMD":  (56, 142, 60),
    "SUP":  (48, 100, 200),
    "ORD":  (183, 28, 28),
    "FREE": (117, 117, 117),
}

# Even darker for front face
COLORS_FRONT = {
    "CMD":  (46, 125, 50),
    "SUP":  (40, 85, 170),
    "ORD":  (160, 20, 20),
    "FREE": (97, 97, 97),
}

# ── Ordnance grid shapes: maps missile size class to WxHxL grid footprint ──
_ORDNANCE_GRID_SHAPES = {
    "S1":  {"w": 1, "h": 1, "l": 1, "scu": 0.125},
    "S2":  {"w": 1, "h": 1, "l": 1, "scu": 1.0},
    "S3":  {"w": 2, "h": 2, "l": 2, "scu": 8.0},
    "S4":  {"w": 2, "h": 2, "l": 2, "scu": 8.0},
    "S5":  {"w": 2, "h": 2, "l": 4, "scu": 16.0},
    "S7":  {"w": 2, "h": 2, "l": 4, "scu": 16.0},
    "S9":  {"w": 2, "h": 2, "l": 6, "scu": 24.0},
    "S10": {"w": 2, "h": 2, "l": 8, "scu": 32.0},
    "S12": {"w": 2, "h": 2, "l": 8, "scu": 32.0},
}

# Regex patterns to detect missile size class from item name
import re as _re
_SIZE_RE = _re.compile(
    r'(?:S|size\s*)(\d+)|'
    r'\b([IVX]+)\b.*?(?:missile|torpedo)',
    _re.IGNORECASE
)
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
          "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
          "XI": 11, "XII": 12}


def _get_ordnance_shape(name):
    """Detect missile/torpedo size class from name and return grid shape.

    Returns dict {w, h, l, scu} or None if not ordnance.
    """
    nm = name.upper().strip()

    # Direct Roman numeral patterns: "Seeker IX Torpedo", "Vanquisher X-CS Torpedo"
    # Match: " IX ", " IX-", " XII-", end of string
    for roman, arabic in sorted(_ROMAN.items(), key=lambda x: -x[1]):
        # Pad with spaces for boundary detection
        padded = f" {nm} "
        # Check " IX " or " IX-" or ending with " IX"
        if (f" {roman} " in padded or
                f" {roman}-" in padded or
                nm.endswith(f" {roman}")):
            key = f"S{arabic}"
            if key in _ORDNANCE_GRID_SHAPES:
                return _ORDNANCE_GRID_SHAPES[key]

    # Bomb detection
    if "BOMB" in nm:
        if "COLOSSUS" in nm:
            return _ORDNANCE_GRID_SHAPES["S10"]
        return _ORDNANCE_GRID_SHAPES["S3"]  # Default bomb size

    return None



def _load_grid_db():
    """Lazy-load ship grid database from ship_grids_db.json."""
    global _grid_db_cache
    if _grid_db_cache is not None:
        return _grid_db_cache

    db_path = PATHS.resource("ship_grids_db.json")
    if os.path.isfile(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                _grid_db_cache = json.load(f)
            return _grid_db_cache
        except (json.JSONDecodeError, OSError):
            pass

    _grid_db_cache = {}
    return _grid_db_cache


def _clean_vessel_name(vessel_name):
    """Strip manufacturer prefix from vessel name.

    'Aegis Idris' -> 'Idris', 'Drake Caterpillar' -> 'Caterpillar'
    """
    clean = vessel_name.strip()
    for prefix in _MANUFACTURER_PREFIXES:
        if clean.lower().startswith(prefix.lower()):
            rest = clean[len(prefix):].strip()
            if rest:
                return rest
    return clean


def load_ship_grid(vessel_name):
    """Load ship grid data by fuzzy-matching vessel name.

    Returns dict with 'capacity', 'groups' etc., or None if not found.
    Uses 3-tier matching: exact → partial → word-based.
    """
    db = _load_grid_db()
    if not db:
        return None

    vessel_low = vessel_name.lower().strip()
    vessel_clean_low = _clean_vessel_name(vessel_name).lower().strip()

    # Strategy 1: Exact match
    for key, val in db.items():
        kl = key.lower()
        if kl == vessel_low or kl == vessel_clean_low:
            return val

    # Strategy 2: Partial match (contains)
    for key, val in db.items():
        kl = key.lower()
        if (vessel_clean_low in kl or kl in vessel_clean_low or
                vessel_low in kl or kl in vessel_low):
            return val

    # Strategy 3: Word match (any significant word)
    vessel_words = [w for w in vessel_low.split() if len(w) > 2]
    for key, val in db.items():
        kl = key.lower()
        if any(w in kl for w in vessel_words):
            return val

    return None


def _compute_grid_dimensions(ship_grid):
    """Compute total bounding box and per-group stats from grid data.

    Returns dict with:
        total_width, total_height, total_length,
        groups: [{grids, width, height, length, slots, offset_x, offset_z}]
    """
    groups_info = []
    for g in ship_grid.get("groups", []):
        gx = int(g.get("x", 0))
        gz = int(g.get("z", 0))
        grids = g.get("grids", [])

        # Compute bounding box for this group
        max_x = 0
        max_y = 0
        max_z = 0
        total_slots = 0
        for gr in grids:
            x = int(gr.get("x", 0))
            y = int(gr.get("y", 0))
            z = int(gr.get("z", 0))
            w = int(gr.get("width", 1))
            h = int(gr.get("height", 1))
            l = int(gr.get("length", 1))
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)
            max_z = max(max_z, z + l)
            total_slots += w * h * l

        groups_info.append({
            "grids": grids,
            "width": max_x,
            "height": max_y,
            "length": max_z,
            "slots": total_slots,
            "offset_x": gx,
            "offset_z": gz,
        })

    return groups_info


def _build_slot_map(group_info):
    """Build 3D occupancy map for a group.

    Returns dict {(x,y,z): True} for all valid slots.
    """
    slot_map = {}
    for gr in group_info["grids"]:
        ox = int(gr.get("x", 0))
        oy = int(gr.get("y", 0))
        oz = int(gr.get("z", 0))
        for x in range(int(gr.get("width", 1))):
            for y in range(int(gr.get("height", 1))):
                for z in range(int(gr.get("length", 1))):
                    slot_map[(ox + x, oy + y, oz + z)] = True
    return slot_map


def _assign_blocks_to_slots(groups_info, breakdown):
    """Assign cargo blocks to grid slots using greedy bin-packing.

    Returns list of block assignments per group:
    [{slots: [(x,y,z)...], label, category, scu}]
    """
    # Collect all blocks to place
    blocks = []

    # Category priority: ORD first (cluster together), then CMD, then SUP
    _CAT_PRIORITY = {"ORD": 0, "CMD": 1, "SUP": 2}

    # Ordnance: each unit is a separate block with proper grid shape
    for item in breakdown.get("ordnance_items", []):
        scu = item.get("scu_per_unit", 1)
        name = item.get("name", "ORDNANCE")
        shape = _get_ordnance_shape(name)
        for i in range(item.get("qty", 1)):
            blk = {
                "label": f"{name.upper()} #{i+1}",
                "category": "ORD",
                "scu": max(scu, 1),  # at least 1 slot on grid
            }
            if shape:
                blk["shape"] = shape  # {w, h, l} for 3D rendering
            blocks.append(blk)

    # Commodities: grouped
    for item in breakdown.get("commodity_items", []):
        scu = item.get("total_scu", item.get("qty", 1))
        name = item.get("name", "COMMODITY")
        blocks.append({
            "label": f"{name.upper()} x{item.get('qty', 1)}",
            "category": "CMD",
            "scu": max(scu, 1),  # at least 1 slot
        })

    # Stor-All boxes
    for box in breakdown.get("stor_all_boxes", []):
        blocks.append({
            "label": box.get("label", "STOR-ALL"),
            "category": "SUP",
            "scu": max(box.get("scu", 1), 1),  # at least 1 slot
        })

    # Sort by category priority (ORD first = cluster together), then SCU descending
    blocks.sort(key=lambda b: (_CAT_PRIORITY.get(b["category"], 9), -b["scu"]))

    # Assign blocks to groups
    all_assignments = []
    remaining_blocks = list(blocks)

    for gi, ginfo in enumerate(groups_info):
        slot_map = _build_slot_map(ginfo)
        occupied = set()
        group_assignments = []

        for block in remaining_blocks[:]:
            needed = int(block["scu"])
            if needed <= 0:
                needed = 1

            shape = block.get("shape")
            placed_slots = []

            if shape:
                # Shape-aware placement for ordnance (WxHxL contiguous box)
                sw, sh, sl = shape["w"], shape["h"], shape["l"]
                placed = False
                for sy in range(ginfo["height"] - sh + 1):
                    for sz in range(ginfo["length"] - sl + 1):
                        for sx in range(ginfo["width"] - sw + 1):
                            # Check if all slots in WxHxL box are free
                            candidates = []
                            valid = True
                            for dy in range(sh):
                                for dz in range(sl):
                                    for dx in range(sw):
                                        pos = (sx + dx, sy + dy, sz + dz)
                                        if pos not in slot_map or pos in occupied:
                                            valid = False
                                            break
                                        candidates.append(pos)
                                    if not valid:
                                        break
                                if not valid:
                                    break
                            if valid and len(candidates) >= needed:
                                placed_slots = candidates[:needed]
                                placed = True
                                break
                        if placed:
                            break
                    if placed:
                        break

            if not placed_slots:
                # Fallback: greedy slot grab
                # SUP items prefer upper Y (upper storage), others bottom-up
                if block["category"] == "SUP":
                    y_range = range(ginfo["height"] - 1, -1, -1)  # top-down
                else:
                    y_range = range(ginfo["height"])  # bottom-up
                for y in y_range:
                    for z in range(ginfo["length"]):
                        for x in range(ginfo["width"]):
                            pos = (x, y, z)
                            if pos in slot_map and pos not in occupied:
                                placed_slots.append(pos)
                                if len(placed_slots) >= needed:
                                    break
                        if len(placed_slots) >= needed:
                            break
                    if len(placed_slots) >= needed:
                        break

            if len(placed_slots) >= needed:
                for s in placed_slots[:needed]:
                    occupied.add(s)
                group_assignments.append({
                    "slots": placed_slots[:needed],
                    "label": block["label"],
                    "category": block["category"],
                    "scu": block["scu"],
                })
                remaining_blocks.remove(block)

        # FREE slots: remaining unoccupied slots → pack as largest possible blocks
        free_slots = [s for s in slot_map if s not in occupied]
        free_scu = len(free_slots)
        if free_scu > 0:
            # Greedy: break into largest possible blocks
            free_remaining = free_scu
            for box_size in [32, 16, 8, 4, 2, 1]:
                while free_remaining >= box_size:
                    # Grab slots
                    take = min(box_size, len(free_slots))
                    if take > 0:
                        group_assignments.append({
                            "slots": free_slots[:take],
                            "label": f"FREE {take} SCU",
                            "category": "FREE",
                            "scu": take,
                        })
                        free_slots = free_slots[take:]
                        free_remaining -= take

        all_assignments.append(group_assignments)

    return all_assignments


# ── Isometric projection helpers ──

def _iso_x(x, z, cell_w):
    """Convert grid (x, z) to isometric screen X."""
    return (x - z) * cell_w * 0.5

def _iso_y(x, z, y, cell_w, cell_h):
    """Convert grid (x, z, y) to isometric screen Y."""
    return (x + z) * cell_w * 0.25 - y * cell_h


def render_grid_preview(pdf, ship_grid, area_x, area_y, area_w, area_h, security_level="CLASSIFIED"):
    """Render mini cargo grid preview box on Page 1 of PDF.

    Shows capacity, section count, and 'SEE PAGE 3' reference.
    For PUBLIC security, shows [REDACTED].
    """
    sec = security_level.upper()

    # Draw preview box
    pdf.set_line_width(0.15)
    pdf.set_draw_color(180, 190, 200)
    pdf.set_fill_color(235, 238, 242)
    pdf.rect(area_x, area_y, area_w, area_h, 'DF')

    if "PUBLIC" in sec or "OPEN" in sec:
        pdf.set_font("Roboto", "B", 6)
        pdf.set_text_color(140, 100, 30)
        pdf.text(area_x + 2, area_y + 4, "CARGO [REDACTED]")
    elif ship_grid and "groups" in ship_grid:
        cap = ship_grid.get("capacity", "?")
        grps = len(ship_grid.get("groups", []))
        pdf.set_font("Roboto", "B", 6)
        pdf.set_text_color(140, 100, 30)
        pdf.text(area_x + 2, area_y + 4, "CARGO GRID")
        pdf.set_font("Roboto", "", 5.5)
        pdf.set_text_color(60, 70, 90)
        sfx = "s" if grps > 1 else ""
        pdf.text(area_x + 4, area_y + 10, f"{cap} SCU / {grps} section{sfx}")
        pdf.set_font("Roboto", "I", 5)
        pdf.set_text_color(100, 110, 140)
        pdf.text(area_x + 4, area_y + 16, "SEE PAGE 3")
        pdf.text(area_x + 4, area_y + 20, "FULL SCHEMATIC")
    else:
        pdf.set_font("Roboto", "I", 6.5)
        pdf.set_text_color(80, 90, 110)
        pdf.text(area_x + 4, area_y + 12, "NO GRID DATA")


def render_cargo_directive(ship_grid, vessel_name, location="", loading_type=""):
    """Generate cargo directive text string.

    Returns formatted directive like:
    'CARGO DIRECTIVE: 5 hold sections (576 SCU). Stack: 4h, 24 SCU max. ...'
    """
    loc_sfx = f" Staging: {location}." if location else ""
    type_sfx = f" Method: {loading_type}." if loading_type else ""

    if ship_grid and "groups" in ship_grid:
        cap = ship_grid.get("capacity", 0)
        groups = ship_grid.get("groups", [])
        grp_count = len(groups)
        max_height = 1
        max_floor = 1
        for g in groups:
            for gr in g.get("grids", []):
                max_height = max(max_height, gr.get("height", 1))
                w = gr.get("width", 1)
                l = gr.get("length", 1)
                max_floor = max(max_floor, w * l)
        max_crate = min(32, max_floor)
        holds = f"{grp_count} hold section{'s' if grp_count > 1 else ''}"
        return f"CARGO DIRECTIVE: {holds} ({cap} SCU). Stack: {max_height}h, {max_crate} SCU max.{loc_sfx}{type_sfx} Clamps locked."
    else:
        return f"CARGO DIRECTIVE: Standard bay. Grid-lock all.{loc_sfx}{type_sfx} Verify clamp power."


def render_full_grid_page(pdf, ship_grid, breakdown, vessel_name,
                          security_level="CLASSIFIED", page_width=210, page_height=297):
    """Render full cargo grid visualization as a new LANDSCAPE PDF page."""
    sec = security_level.upper()

    # Add LANDSCAPE page (A4: 297mm wide x 210mm tall)
    pdf.add_page(orientation="L")
    lw = 297  # landscape width
    lh = 210  # landscape height
    # main.pyc header occupies ~45mm at top of every page
    header_h = 48

    if "PUBLIC" in sec or "OPEN" in sec:
        pdf.set_font("Roboto", "B", 16)
        pdf.set_text_color(180, 140, 40)
        pdf.text(80, 100, "[CARGO DATA REDACTED -- PUBLIC CHANNEL]")
        return

    if not ship_grid or "groups" not in ship_grid:
        pdf.set_font("Roboto", "I", 12)
        pdf.set_text_color(120, 130, 150)
        pdf.text(80, 80, "NO GRID DATA AVAILABLE FOR THIS VESSEL")
        return

    groups_info = _compute_grid_dimensions(ship_grid)

    # ── Overflow check: if cargo exceeds ship capacity, show empty grid + warning ──
    ship_cap = ship_grid.get("capacity", 0)
    total_cargo_scu = (
        breakdown.get("commodity_vol", 0) +
        breakdown.get("supply_vol", 0) +
        breakdown.get("ordnance_vol", 0)
    )
    # Count from blocks if vol totals are zero
    if total_cargo_scu < 0.01:
        for b in breakdown.get("blocks", []):
            total_cargo_scu += b.get("vol", 0)

    is_overflow = ship_cap > 0 and total_cargo_scu > ship_cap

    if is_overflow:
        # ── OVERFLOW: render empty grid + warning + cargo list ──
        # Render empty grid (all FREE)
        empty_breakdown = {
            "commodity_vol": 0, "supply_vol": 0, "ordnance_vol": 0,
            "total_vol": 0, "blocks": [], "ordnance_items": [],
            "commodity_items": [], "supply_items": [], "stor_all_boxes": [],
        }
        assignments = _assign_blocks_to_slots(groups_info, empty_breakdown)

        import tempfile
        import os
        img_path = _render_iso_image(groups_info, assignments, ship_grid, vessel_name)

        legend_y = lh - 22
        if img_path and os.path.exists(img_path):
            try:
                from PIL import Image as PILImage
                img = PILImage.open(img_path)
                iw, ih = img.size
                # Show grid on LEFT side (half page)
                avail_w = (lw - 16) * 0.5
                avail_h = lh - header_h - 28
                dpi = 150
                img_w_mm = iw / dpi * 25.4
                img_h_mm = ih / dpi * 25.4
                scale = min(avail_w / img_w_mm, avail_h / img_h_mm)
                img_w_mm *= scale
                img_h_mm *= scale
                img_x = 8
                img_y = header_h + (avail_h - img_h_mm) / 2
                pdf.image(img_path, x=img_x, y=img_y, w=img_w_mm, h=img_h_mm)
            except Exception as e:
                print(f"[GridPage] Image error: {e}")
            try:
                os.remove(img_path)
            except Exception:
                pass

        # ── WARNING text on RIGHT side ──
        warn_x = lw * 0.52
        warn_y = header_h + 5
        ovr_pct = int((total_cargo_scu / ship_cap - 1) * 100) if ship_cap > 0 else 0

        # Red warning box
        pdf.set_fill_color(255, 230, 230)
        pdf.set_draw_color(200, 40, 30)
        pdf.set_line_width(0.4)
        pdf.rect(warn_x - 2, warn_y - 3, lw - warn_x - 4, 12, 'DF')
        try: pdf.set_font("Roboto", "B", 8)
        except Exception: pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(180, 30, 20)
        pdf.text(warn_x, warn_y + 2,
                 f"CARGO EXCEEDS VESSEL CAPACITY")
        try: pdf.set_font("Roboto", "B", 6)
        except Exception: pdf.set_font("Helvetica", "B", 6)
        pdf.text(warn_x, warn_y + 7,
                 f"{total_cargo_scu:.0f} SCU vs {ship_cap} SCU MAX (+{ovr_pct}%)")

        # Instruction
        warn_y += 16
        try: pdf.set_font("Roboto", "B", 7)
        except Exception: pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(180, 30, 20)
        pdf.text(warn_x, warn_y,
                 "RECONSIDER LARGER SHIP OR REDUCE CARGO")
        try: pdf.set_font("Roboto", "I", 5.5)
        except Exception: pdf.set_font("Helvetica", "I", 5.5)
        pdf.set_text_color(120, 80, 60)
        pdf.text(warn_x, warn_y + 5,
                 "Cannot fit all items on cargo grid. Cargo bay shown empty.")

        # List all items that should have been loaded
        warn_y += 14
        try: pdf.set_font("Roboto", "B", 6)
        except Exception: pdf.set_font("Helvetica", "B", 6)
        pdf.set_text_color(40, 50, 70)
        pdf.text(warn_x, warn_y, "ITEMS REQUIRING TRANSPORT:")
        warn_y += 5
        try: pdf.set_font("Roboto", "", 5)
        except Exception: pdf.set_font("Helvetica", "", 5)
        pdf.set_text_color(60, 70, 90)

        all_items = (
            breakdown.get("commodity_items", []) +
            breakdown.get("supply_items", []) +
            breakdown.get("ordnance_items", [])
        )
        for item in all_items[:25]:  # max 25 items
            name = item.get("name", "?")
            qty = item.get("qty", 1)
            scu = item.get("total_scu", item.get("scu_per_unit", 0) * qty)
            pdf.text(warn_x + 2, warn_y, f"• {name} x{qty}  ({scu:.1f} SCU)")
            warn_y += 3.5
            if warn_y > lh - 25:
                pdf.text(warn_x + 2, warn_y, "... and more items")
                break

        # Legend at bottom
        _draw_legend(pdf, breakdown, ship_grid, vessel_name, lh - 22)
        return

    assignments = _assign_blocks_to_slots(groups_info, breakdown)

    # ── Render isometric image with PIL ──
    import tempfile
    import os
    img_path = _render_iso_image(groups_info, assignments, ship_grid, vessel_name)

    legend_y = lh - 22  # default legend position
    if img_path and os.path.exists(img_path):
        try:
            from PIL import Image as PILImage
            img = PILImage.open(img_path)
            iw, ih = img.size
            # Available area: below header, above legend
            avail_w = lw - 16  # 281mm
            avail_h = lh - header_h - 28  # ~134mm
            # Convert px to mm at 150 DPI
            dpi = 150
            img_w_mm = iw / dpi * 25.4
            img_h_mm = ih / dpi * 25.4
            # Scale to fill available area
            scale = min(avail_w / img_w_mm, avail_h / img_h_mm)
            img_w_mm *= scale
            img_h_mm *= scale
            # Center in available area (below header)
            img_x = (lw - img_w_mm) / 2
            img_y = header_h + (avail_h - img_h_mm) / 2
            pdf.image(img_path, x=img_x, y=img_y, w=img_w_mm, h=img_h_mm)
            legend_y = lh - 22
        except Exception as e:
            print(f"[GridPage] Image error: {e}")
        try:
            os.remove(img_path)
        except Exception:
            pass

    # ── Legend + stats at bottom ──
    _draw_legend(pdf, breakdown, ship_grid, vessel_name, legend_y)


def _render_iso_image(groups_info, assignments, ship_grid, vessel_name):
    """Render isometric cargo grid as a PIL image matching sc-cargo.space style.

    Each SCU slot is rendered as an individual cube.  Grid paper extends
    beyond the cargo bays to give spatial context.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    # ── Build per-slot category + scu map ──
    # Maps (group_idx, x, y, z) -> (category, scu)
    slot_categories = {}
    for gi, (ginfo, gassgn) in enumerate(zip(groups_info, assignments)):
        for block in gassgn:
            cat = block["category"]
            scu = block.get("scu", 1)
            for sx, sy, sz in block["slots"]:
                slot_categories[(gi, sx, sy, sz)] = (cat, scu)

    # ── Compute bounding box across all groups ──
    all_max_x = 0
    all_max_z = 0
    all_max_y = 0
    for ginfo in groups_info:
        ox = ginfo.get("offset_x", 0)
        oz = ginfo.get("offset_z", 0)
        all_max_x = max(all_max_x, ox + ginfo["width"])
        all_max_z = max(all_max_z, oz + ginfo["length"])
        all_max_y = max(all_max_y, ginfo["height"])

    # Grid paper padding — tight around cargo to maximize cube size
    grid_pad = 1
    grid_w = all_max_x + grid_pad * 2
    grid_l = all_max_z + grid_pad * 2

    # Cell size — make cubes look cubic in isometric
    # For small grids (< 20 cells), use bigger cells for better visibility
    total_cells = grid_w + grid_l
    if total_cells <= 12:
        cell_px = max(48, min(64, 3200 // max(total_cells, 1)))
    elif total_cells <= 24:
        cell_px = max(32, min(48, 2800 // max(total_cells, 1)))
    else:
        cell_px = max(20, min(40, 2400 // max(total_cells, 1)))
    cell_h_px = cell_px // 2  # cubic proportions in iso

    # Image dimensions
    iso_w = (grid_w + grid_l) * cell_px
    iso_h = (grid_w + grid_l) * cell_px // 2 + all_max_y * cell_h_px + 60
    img_w = iso_w + 80
    img_h = iso_h + 80

    # White background (matches PDF page)
    img = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Origin: top-center of isometric space
    ox_px = img_w // 2
    oy_px = 30 + all_max_y * cell_h_px

    def iso_x(x, z):
        return ox_px + (x - z) * cell_px // 2

    def iso_y(x, z, y=0):
        return oy_px + (x + z) * cell_px // 4 - y * cell_h_px

    # ── 1) GRID PAPER — checkered isometric floor ──
    grid_line = (210, 214, 222, 255)
    for gz in range(grid_l):
        for gx in range(grid_w):
            if (gx + gz) % 2 == 0:
                fill = (232, 234, 240, 255)
            else:
                fill = (226, 228, 234, 255)
            _draw_iso_diamond(draw, iso_x(gx, gz), iso_y(gx, gz),
                              cell_px, fill, grid_line)

    # ── 2) BAY FLOOR HIGHLIGHT ──
    for gi, ginfo in enumerate(groups_info):
        gox = ginfo.get("offset_x", 0) + grid_pad
        goz = ginfo.get("offset_z", 0) + grid_pad
        slot_map = _build_slot_map(ginfo)
        for (sx, sy, sz), _ in slot_map.items():
            if sy != 0:
                continue
            ax, az = sx + gox, sz + goz
            if (ax + az) % 2 == 0:
                fill = (210, 230, 215, 255)
            else:
                fill = (200, 222, 208, 255)
            _draw_iso_diamond(draw, iso_x(ax, az), iso_y(ax, az),
                              cell_px, fill, (180, 200, 185, 255))

    # ── 3) RENDER INDIVIDUAL CUBES — back to front ──
    # Collect all renderable slots
    all_cubes = []
    for gi, ginfo in enumerate(groups_info):
        gox = ginfo.get("offset_x", 0) + grid_pad
        goz = ginfo.get("offset_z", 0) + grid_pad
        slot_map = _build_slot_map(ginfo)
        for (sx, sy, sz), _ in slot_map.items():
            cat_info = slot_categories.get((gi, sx, sy, sz), ("FREE", 0))
            cat = cat_info[0] if isinstance(cat_info, tuple) else cat_info
            scu = cat_info[1] if isinstance(cat_info, tuple) else 0
            all_cubes.append((sx + gox, sy, sz + goz, cat, scu))

    # Sort: back-to-front for painter's algorithm
    # In our iso: small (x+z) = back/top of screen, large = front/bottom
    # Within same depth: left (small x) before right (large x)
    # Within same position: bottom (small y) before top (large y)
    all_cubes.sort(key=lambda c: (c[0] + c[2], c[0] - c[2], c[1]))

    for wx, wy, wz, cat, scu in all_cubes:
        _draw_cube_pil(draw, iso_x, iso_y, wx, wy, wz, cell_px, cell_h_px, cat)
        # Overlay ordnance PNG icon on front face of ORD cubes
        if cat == "ORD":
            fcx = (iso_x(wx, wz) + iso_x(wx + 1, wz)) // 2
            fcy = (iso_y(wx, wz, wy) + iso_y(wx, wz, wy + 1)) // 2
            _overlay_ordnance_icon(img, fcx, fcy, cell_px, scu)

    # ── 4) BAY LABELS ──
    try:
        font = ImageFont.truetype("arial.ttf", max(11, cell_px))
    except Exception:
        font = ImageFont.load_default()
    try:
        font_small = ImageFont.truetype("arial.ttf", max(9, cell_px - 2))
    except Exception:
        font_small = font

    num_groups = len(groups_info)
    for gi, ginfo in enumerate(groups_info):
        gox = ginfo.get("offset_x", 0) + grid_pad
        goz = ginfo.get("offset_z", 0) + grid_pad
        gl = ginfo["length"]
        gw_val = ginfo["width"]

        # Label at bottom-left of bay
        lx = iso_x(gox + gw_val // 2, goz + gl)
        ly = iso_y(gox + gw_val // 2, goz + gl) + 8
        bay_name = ginfo.get("name", f"Bay {gi + 1}" if num_groups > 1 else "Main Cargo Bay")
        # Ship name
        draw.text((lx - 30, ly), vessel_name, fill=(50, 60, 80, 255), font=font)
        # Bay name + capacity
        cap_text = f"({ginfo['slots']} SCU)"
        draw.text((lx - 30, ly + cell_px + 2), bay_name, fill=(90, 100, 120, 255), font=font_small)
        draw.text((lx - 30, ly + cell_px * 2), cap_text, fill=(130, 140, 155, 255), font=font_small)

    # ── Auto-crop whitespace ──
    bbox = img.getbbox()
    if bbox:
        img = img.crop((max(0, bbox[0] - 20), max(0, bbox[1] - 20),
                         min(img_w, bbox[2] + 20), min(img_h, bbox[3] + 20)))

    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.convert("RGB").save(tmp.name, "PNG")
    tmp.close()
    return tmp.name


def _draw_iso_diamond(draw, cx, cy, cell_px, fill, outline):
    hw, hh = cell_px // 2, cell_px // 4
    draw.polygon([(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)], fill=fill, outline=outline)


# ── Cube colors matching sc-cargo.space ──
_CUBE_COLORS = {
    "CMD":  {"top": (120, 200, 140), "left": (90, 175, 110), "right": (70, 155, 90)},
    "SUP":  {"top": (100, 170, 220), "left": (70, 145, 195), "right": (50, 125, 175)},
    "ORD":  {"top": (230, 130, 140), "left": (205, 105, 115), "right": (185, 85, 95)},
    "FREE": {"top": (195, 205, 195), "left": (175, 185, 175), "right": (160, 170, 160)},
}


def _draw_cube_pil(draw, iso_x_fn, iso_y_fn, wx, wy, wz, cell_px, cell_h_px, category):
    """Draw a single 1x1x1 SCU cube at world position (wx, wy, wz).

    Renders 3 visible faces (top, left, right) with category-specific colors.
    Leaves a 1px gap between cubes to show grid structure.
    """
    colors = _CUBE_COLORS.get(category, _CUBE_COLORS["FREE"])
    gap = 1  # pixel gap between cubes

    # Half-cell dimensions
    hw = cell_px // 2
    hh = cell_px // 4

    # Screen coords for the 4 key points of a unit cube
    # Top of cube (y+1)
    top_cx = iso_x_fn(wx, wz)
    top_cy = iso_y_fn(wx, wz, wy + 1)
    # Bottom of cube (y)
    bot_cx = iso_x_fn(wx, wz)
    bot_cy = iso_y_fn(wx, wz, wy)

    # Top face diamond (at y+1 level)
    t_top = (top_cx, top_cy - hh + gap)
    t_right = (top_cx + hw - gap, top_cy)
    t_bottom = (top_cx, top_cy + hh - gap)
    t_left = (top_cx - hw + gap, top_cy)

    # Bottom corners (at y level)
    b_bottom = (bot_cx, bot_cy + hh - gap)
    b_right = (bot_cx + hw - gap, bot_cy)
    b_left = (bot_cx - hw + gap, bot_cy)

    alpha = 255
    edge = (60, 70, 80, 255) if category != "FREE" else (150, 160, 170, 255)

    # Top face
    top_poly = [t_top, t_right, t_bottom, t_left]
    draw.polygon(top_poly, fill=(*colors["top"], alpha), outline=edge)

    # Left face (front-left visible side)
    left_poly = [t_left, t_bottom, b_bottom, b_left]
    draw.polygon(left_poly, fill=(*colors["left"], alpha), outline=edge)

    # Right face (front-right visible side)
    right_poly = [t_right, t_bottom, b_bottom, b_right]
    draw.polygon(right_poly, fill=(*colors["right"], alpha), outline=edge)


def _draw_iso_box_pil(draw, iso_x_fn, iso_y_fn, bx, by, bz, bw, bh, bl,
                       cell_px, cell_h_px, color_top, color_right, color_front,
                       category, scu):
    """Draw a filled isometric 3D box with PIL. Includes ordnance markings."""
    b_fl = (iso_x_fn(bx, bz), iso_y_fn(bx, bz, by))
    b_fr = (iso_x_fn(bx, bz + bl), iso_y_fn(bx, bz + bl, by))
    b_bl = (iso_x_fn(bx + bw, bz), iso_y_fn(bx + bw, bz, by))
    t_fl = (iso_x_fn(bx, bz), iso_y_fn(bx, bz, by + bh))
    t_fr = (iso_x_fn(bx, bz + bl), iso_y_fn(bx, bz + bl, by + bh))
    t_bl = (iso_x_fn(bx + bw, bz), iso_y_fn(bx + bw, bz, by + bh))
    t_br = (iso_x_fn(bx + bw, bz + bl), iso_y_fn(bx + bw, bz + bl, by + bh))

    edge = (50, 55, 65, 255)

    if category == "FREE":
        # Dotted outline only (no fill)
        dot_color = (170, 175, 185, 200)
        for poly in [[t_fl, t_bl, t_br, t_fr], [t_fl, t_bl, b_bl, b_fl], [t_fl, t_fr, b_fr, b_fl]]:
            draw.polygon(poly, fill=(240, 242, 248, 120), outline=dot_color)
    else:
        # Solid filled faces
        draw.polygon([t_fl, t_bl, t_br, t_fr], fill=(*color_top, 255), outline=edge)
        draw.polygon([t_fl, t_bl, b_bl, b_fl], fill=(*color_front, 255), outline=edge)
        draw.polygon([t_fl, t_fr, b_fr, b_fl], fill=(*color_right, 255), outline=edge)

    # Ordnance: cage cross on top face + hazard marking
    if category == "ORD":
        cage_color = (255, 200, 200, 200)
        draw.line([t_fl, t_br], fill=cage_color, width=1)
        draw.line([t_bl, t_fr], fill=cage_color, width=1)
        # Hazard border on front face
        draw.line([t_fl, b_fl], fill=(255, 100, 100, 200), width=2)
        draw.line([t_bl, b_bl], fill=(255, 100, 100, 200), width=2)

        # Weapon symbol on front face
        fcx = (t_fl[0] + t_bl[0]) // 2
        fcy = (t_fl[1] + b_fl[1]) // 2
        s = max(3, min(cell_px // 3, 8))
        _draw_ordnance_symbol_pil(draw, fcx, fcy, s, scu)

    # SCU label
    fcx = (t_fl[0] + t_bl[0] + b_bl[0] + b_fl[0]) // 4
    fcy = (t_fl[1] + t_bl[1] + b_bl[1] + b_fl[1]) // 4
    scu_text = str(int(scu))
    txt_color = (255, 255, 255, 255) if category not in ("FREE",) else (130, 140, 160, 255)
    draw.text((fcx - 2, fcy - 4), scu_text, fill=txt_color)


def _draw_ordnance_symbol_pil(draw, cx, cy, s, scu):
    """Draw missile/torpedo/bomb silhouette on a cargo box face.

    Uses PNG icon overlays from resources/ when available,
    falls back to simple line drawings.
    """
    sym_color = (255, 230, 230, 255)
    if scu >= 30:
        # Bomb: fat oval + tail fins
        draw.ellipse((cx - s, cy - s, cx + s, cy + s // 2), outline=sym_color, width=1)
        draw.line((cx - s // 2, cy + s // 2, cx, cy + s), fill=sym_color, width=1)
        draw.line((cx + s // 2, cy + s // 2, cx, cy + s), fill=sym_color, width=1)
    elif scu >= 10:
        # Torpedo: long body + cone
        draw.line((cx, cy - s, cx, cy + s // 2), fill=sym_color, width=2)
        draw.line((cx - s // 3, cy + s // 2, cx + s // 3, cy + s // 2), fill=sym_color, width=1)
        draw.polygon([(cx, cy - s), (cx - s // 4, cy - s + s // 2), (cx + s // 4, cy - s + s // 2)], fill=sym_color)
    else:
        # Missile: thin body + fins
        draw.line((cx, cy - s, cx, cy + s // 2), fill=sym_color, width=1)
        draw.line((cx - s // 3, cy + s // 4, cx, cy - s // 4), fill=sym_color, width=1)
        draw.line((cx + s // 3, cy + s // 4, cx, cy - s // 4), fill=sym_color, width=1)


# ── Ordnance icon cache ──
_ORD_ICON_CACHE = {}

def _load_ordnance_icon(scu, target_size):
    """Load and cache ordnance PNG icon, resized to target_size.

    Returns PIL Image (RGBA) or None.
    """
    if scu >= 30:
        icon_name = "ordnance_bomb.png"
    elif scu >= 10:
        icon_name = "ordnance_torpedo.png"
    else:
        icon_name = "ordnance_missile.png"

    cache_key = f"{icon_name}_{target_size}"
    if cache_key in _ORD_ICON_CACHE:
        return _ORD_ICON_CACHE[cache_key]

    try:
        from PIL import Image
        icon_path = PATHS.resource(icon_name)
        if os.path.isfile(icon_path):
            icon = Image.open(icon_path).convert("RGBA")
            icon = icon.resize((target_size, target_size), Image.LANCZOS)
            _ORD_ICON_CACHE[cache_key] = icon
            return icon
    except Exception:
        pass

    _ORD_ICON_CACHE[cache_key] = None
    return None


def _overlay_ordnance_icon(img, cx, cy, cell_px, scu):
    """Paste ordnance PNG icon onto the cargo grid image at (cx, cy).

    Centers the icon on the front face of the cube.
    """
    icon_size = max(12, cell_px // 2)
    icon = _load_ordnance_icon(scu, icon_size)
    if icon is None:
        return

    try:
        paste_x = cx - icon_size // 2
        paste_y = cy - icon_size // 2
        # Ensure within image bounds
        if paste_x >= 0 and paste_y >= 0:
            img.paste(icon, (paste_x, paste_y), icon)
    except Exception:
        pass


def _draw_legend(pdf, breakdown, ship_grid, vessel_name, y_pos):
    """Draw stats line and color legend at bottom of grid page."""
    cap = ship_grid.get("capacity", "?") if ship_grid else "?"
    used = breakdown.get("total_vol", 0)
    free = cap - used if isinstance(cap, (int, float)) else "?"
    cmd = breakdown.get("commodity_vol", 0)
    sup = breakdown.get("supply_vol", 0)
    ordn = breakdown.get("ordnance_vol", 0)
    groups = len(ship_grid.get("groups", [])) if ship_grid else 0

    y = min(y_pos, 195)  # Must fit on landscape page (210mm tall)

    # Stats line
    pdf.set_font("Roboto", "", 6.5)
    pdf.set_text_color(60, 70, 90)
    stats = f"Vessel: {vessel_name}  |  Capacity: {cap} SCU  |  Sections: {groups}"
    pdf.text(14, y, stats)
    stats2 = f"Used: {used:.0f} SCU  |  Free: {free:.0f} SCU  |  Commodity: {cmd:.0f}  |  Supply: {sup:.0f}  |  Ordnance: {ordn:.0f}"
    pdf.text(14, y + 5, stats2)

    # Color legend
    legend_y = y + 12
    legend_items = [
        ("CMD", "Commodity", COLORS["CMD"]),
        ("SUP", "Supply (Stor-All)", COLORS["SUP"]),
        ("ORD", "Ordnance", COLORS["ORD"]),
        ("FREE", "Free", COLORS["FREE"]),
    ]
    x = 14
    for code, label, color in legend_items:
        pdf.set_fill_color(*color)
        pdf.set_draw_color(80, 80, 80)
        pdf.set_line_width(0.1)
        pdf.rect(x, legend_y - 2.5, 3, 3, 'DF')
        pdf.set_font("Roboto", "", 5.5)
        pdf.set_text_color(60, 70, 90)
        pdf.text(x + 4, legend_y, f"{code} — {label}")
        x += pdf.get_string_width(f"{code} — {label}") + 8
