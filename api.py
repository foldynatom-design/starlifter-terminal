"""
Starlifter Terminal API — Headless PDF generation functions.
No GUI dependencies. Ready for Discord bot integration.

Usage:
    from api import generate_manifest, generate_supply_route, build_event_data
"""

import os
import json
import random
import time

# SC year offset
SC_YEAR_OFFSET = 930

def _get_sc_date():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    sc_year = now.year + SC_YEAR_OFFSET
    return f"{sc_year}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d} SET"

def _get_sc_date_only():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    sc_year = now.year + SC_YEAR_OFFSET
    return f"{sc_year}-{now.month:02d}-{now.day:02d}"

def _load_config():
    """Load config.json from project root."""
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def parse_cargo_text(text):
    """Parse cargo text like '20x Scorch Plasma Grenade, 16x S9 Torpedo' -> list of dicts.
    
    Returns: [{"name": "Scorch Plasma Grenade", "qty": 20}, ...]
    """
    import re
    items = []
    for part in re.split(r'[,;\n]', text):
        part = part.strip()
        if not part:
            continue
        # Match patterns: "20x ItemName", "20 x ItemName", "ItemName x20", "ItemName 20"
        m = re.match(r'(\d+)\s*[xX×]\s*(.+)', part)
        if not m:
            m = re.match(r'(.+?)\s*[xX×]\s*(\d+)', part)
            if m:
                items.append({"name": m.group(1).strip(), "qty": int(m.group(2))})
                continue
        if m:
            items.append({"name": m.group(2).strip(), "qty": int(m.group(1))})
        else:
            items.append({"name": part, "qty": 1})
    return items


def build_event_data(ship, items_text, classification="CLASSIFIED",
                     officer="", captain="", mission="", date_utc=None):
    """Build event data structure for OrgNexus / Discord integration.
    
    Args:
        ship: Ship name (e.g. "C2 Hercules")
        items_text: Cargo items as text (e.g. "20x Scorch, 16x S9 Torpedo")
        classification: PUBLIC / SECURED / CLASSIFIED
        officer: Loading officer name
        captain: Ship captain name
        mission: Mission description
        date_utc: Date/time in SC format, auto-generated if None
    
    Returns: dict with all event data
    """
    items = parse_cargo_text(items_text) if isinstance(items_text, str) else items_text
    cargo_summary = ", ".join(f"{i['qty']}x {i['name']}" for i in items[:5])
    if len(items) > 5:
        cargo_summary += f" +{len(items)-5} more"
    
    return {
        "title": f"Logistics Op: {mission}" if mission else f"Logistics Op: {ship} Resupply",
        "date_utc": date_utc or _get_sc_date(),
        "date_short": date_utc[:10] if date_utc else _get_sc_date_only(),
        "ship": ship,
        "captain": captain,
        "officer": officer,
        "mission": mission,
        "classification": classification,
        "cargo_items": items,
        "cargo_summary": cargo_summary,
        "total_items": sum(i["qty"] for i in items),
        "rp_text": _generate_rp_text(ship, officer, captain, items, mission),
    }


def _generate_rp_text(ship, officer, captain, items, mission=""):
    """Generate RP loadout text for Discord channel posting."""
    cargo_lines = "\n".join(f"  • {i['qty']}x {i['name']}" for i in items)
    date_str = _get_sc_date()
    
    text = f"""═══════════════════════════════════════
  44th BATTLE GROUP — LOGISTICS DIVISION
  29th Starlifter Squadron [SLS29]
═══════════════════════════════════════

▸ VESSEL: {ship}
▸ CAPTAIN: {captain or 'TBD'}
▸ LOADING OFFICER: {officer or 'TBD'}
▸ DATE: {date_str}
▸ MISSION: {mission or 'Standard Resupply'}

─── CARGO MANIFEST ───
{cargo_lines}

▸ TOTAL ITEMS: {sum(i['qty'] for i in items)}
═══════════════════════════════════════
  // TRANSMITTED VIA STARLIFTER TERMINAL v0.6
  // {date_str}
═══════════════════════════════════════"""
    return text


# Bot config template
BOT_CONFIG_TEMPLATE = {
    "discord_token": "",
    "orgnexus_oauth2": {
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "",
        "note": "OrgNexus uses Discord OAuth2 - LOGIN WITH DISCORD button"
    },
    "org_id": "",
    "event_channel_id": "",
    "log_channel_id": "",
}


def ensure_bot_config():
    """Ensure bot_config section exists in config.json."""
    cfg = _load_config()
    if "bot_config" not in cfg:
        cfg["bot_config"] = BOT_CONFIG_TEMPLATE
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    return cfg.get("bot_config", {})
