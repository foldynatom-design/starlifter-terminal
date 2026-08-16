import tkinter as tk
import customtkinter as ctk
from src.agents.data_validator import get_verified_buy_locations
from src.agents.cargo_packer import pack_items

def audit_cargo_table(app):
    """
    Consolidates the cargo table, merges duplicate rows by item name,
    autofills zero/missing prices, auto-boxes loose gear into Stor-All containers,
    and updates grand total.
    """
    if not hasattr(app, 'cargo_rows') or not app.cargo_rows:
        return

    app._in_table_audit = True
    try:
        # Group items by canonical/normalized name
        consolidated = {}
        from slang_helper import resolve_slang
        for row in app.cargo_rows:
            raw_name = row['name_var'].get().strip()
            qty_str = row['qty_var'].get().strip()
            if not raw_name:
                continue
            name = resolve_slang(raw_name)
            if hasattr(row['name_var'], 'set') and name != raw_name:
                try:
                    row['name_var'].set(name)
                except Exception:
                    pass
            # Preserve items with empty/zero qty (user may not have filled it in yet)
            try:
                qty = int(float(qty_str)) if qty_str and qty_str != '?' else 0
                if qty < 0: qty = 0
            except (ValueError, TypeError):
                qty = 0

            bv = row.get('box_size_var')
            box = bv.get().strip() if (bv and hasattr(bv, 'get')) else '1 SCU'
            if not box: box = '1 SCU'

            pv = row.get('price_var')
            price_raw = pv.get() if (pv and hasattr(pv, 'get')) else '0'
            try:
                price = float(str(price_raw).replace(',', '').replace(' ', ''))
            except (ValueError, TypeError):
                price = 0.0

            try:
                courtesy = bool(row.get('courtesy_var').get()) if ('courtesy_var' in row and hasattr(row['courtesy_var'], 'get')) else False
            except Exception:
                courtesy = False

            # Differentiate between Free Supply (courtesy) and Purchased items so they never merge into a single row
            key = (name.lower().strip(), courtesy)
            if key in consolidated:
                consolidated[key]['qty'] += qty
                if price > 0 and consolidated[key]['price'] == 0 and not courtesy:
                    consolidated[key]['price'] = price
                if box != 'Loose' and consolidated[key]['box_size'] == 'Loose':
                    consolidated[key]['box_size'] = box
            else:
                consolidated[key] = {
                    'name': name,
                    'qty': qty,
                    'box_size': box,
                    'price': price if not courtesy else 0.0,
                    'status': row['status_var'].get() if ('status_var' in row and hasattr(row['status_var'], 'get')) else 'LOOSE',
                    'courtesy': courtesy
                }

        # Enforce exact companion ratios on refresh / consolidation
        _COMPANION_RULES = []
        try:
            import json as _cr_json
            from path_config import PATHS as _cr_PATHS
            with open(_cr_PATHS.config, 'r', encoding='utf-8') as _cr_f:
                _cr_cfg = _cr_json.load(_cr_f)
            for rule in _cr_cfg.get('autoloader_rules', []):
                trigger = rule.get('trigger', '').lower().strip()
                adds = rule.get('adds', [])
                if trigger and adds:
                    for add in adds:
                        c_name = add.get('name', '').strip()
                        if c_name:
                            _COMPANION_RULES.append({
                                "trigger": trigger,
                                "companion": c_name,
                                "ratio": int(add.get('qty_multiplier', 1)),
                                "box_size": "Loose",
                                "price": float(add.get('price', 0))
                            })
        except Exception:
            pass

        if not _COMPANION_RULES:
            _COMPANION_RULES = [
                {"trigger": "cambio srt", "companion": "Cambio SRT Canister", "ratio": 10, "box_size": "Loose", "price": 275},
                {"trigger": "cambio srt", "companion": "Cambio Multi-tool Battery", "ratio": 1, "box_size": "Loose", "price": 63},
                {"trigger": "maxlift tractor beam", "companion": "Maxlift Tractor Beam Battery", "ratio": 1, "box_size": "Loose", "price": 175},
                {"trigger": "paramed", "companion": "ParaMed Refill", "ratio": 4, "box_size": "Loose", "price": 50},
                {"trigger": "lifeguard", "companion": "LifeGuard Refill", "ratio": 4, "box_size": "Loose", "price": 50},
                {"trigger": "p4-ar", "companion": "P4-AR Magazine", "ratio": 40, "box_size": "Loose", "price": 20},
                {"trigger": "p8-sc", "companion": "P8-SC Magazine", "ratio": 40, "box_size": "Loose", "price": 20},
                {"trigger": "fs-9", "companion": "FS-9 Magazine", "ratio": 40, "box_size": "Loose", "price": 25},
                {"trigger": "p6-lr", "companion": "P6-LR Magazine", "ratio": 40, "box_size": "Loose", "price": 30},
                {"trigger": "a03", "companion": "A03 Magazine", "ratio": 40, "box_size": "Loose", "price": 30},
                {"trigger": "s-38", "companion": "S-38 Magazine", "ratio": 20, "box_size": "Loose", "price": 15},
                {"trigger": "arclight", "companion": "Arclight Magazine", "ratio": 20, "box_size": "Loose", "price": 15},
                {"trigger": "lh86", "companion": "LH86 Magazine", "ratio": 20, "box_size": "Loose", "price": 15},
            ]

        def _is_trigger_match(trig, p_key):
            t_low = trig.lower().strip()
            p_low = p_key.lower().strip()
            if any(suffix in p_low for suffix in ["canister", "battery", "magazine", "mag", "refill"]):
                return False
            return p_low == t_low or (p_low.startswith(t_low) and not any(s in p_low for s in ["canister", "battery", "magazine", "refill"]))

        for parent_key, parent_data in list(consolidated.items()):
            item_name_str = parent_key[0] if isinstance(parent_key, tuple) else str(parent_key)
            for rule in _COMPANION_RULES:
                if _is_trigger_match(rule["trigger"], item_name_str):
                    comp_name = rule["companion"]
                    comp_key = (comp_name.lower().strip(), False)
                    req_qty = parent_data["qty"] * rule["ratio"]
                    if comp_key in consolidated:
                        if consolidated[comp_key]["qty"] < req_qty:
                            consolidated[comp_key]["qty"] = req_qty
                    else:
                        consolidated[comp_key] = {
                            "name": comp_name,
                            "qty": req_qty,
                            "box_size": rule["box_size"],
                            "price": rule.get("price", 0.0),
                            "status": "LOOSE",
                            "courtesy": False
                        }

        # Autofill zero prices via UEX trade DB or _get_base_unit_price
        try:
            from slang_helper import resolve_slang
            from uex_sync import uex_items_trade_db
            trade_db = uex_items_trade_db() if callable(uex_items_trade_db) else uex_items_trade_db
            for data in consolidated.values():
                if data.get('courtesy', False):
                    data['price'] = 0.0
                    continue
                canonical = resolve_slang(data['name'])
                key_low = canonical.lower().strip()
                if key_low in trade_db:
                    locs = trade_db[key_low].get('locations', [])
                    buys = [loc['buy'] for loc in locs if isinstance(loc, dict) and loc.get('buy', 0) > 0]
                    if buys and data['price'] == 0:
                        data['price'] = min(buys)
                elif data['price'] == 0:
                    try:
                        from ui_panel import _get_base_unit_price
                        fetched_price = _get_base_unit_price(app, data['name'])
                        if fetched_price > 0:
                            data['price'] = fetched_price
                    except Exception: pass
        except Exception as e:
            print(f"[AUDIT_PRICE_AUTOFILL] {e}")

        # Clear existing UI table rows
        app.clear_all_rows()

        # Repopulate table with consolidated items
        for data in consolidated.values():
            name = data['name']
            qty = data['qty']
            box_size = data['box_size']
            price = data['price']
            if price == int(price):
                price = int(price)
            courtesy = data['courtesy']

            # Re-add row with autoloader bypassed
            app.add_cargo_row_to_ui(
                name=name,
                qty=str(qty),
                box_size=box_size,
                price=price,
                courtesy=courtesy,
                _skip_autoloader=True
            )

            if app.cargo_rows:
                last_row = app.cargo_rows[-1]
                if 'courtesy_var' in last_row:
                    last_row['courtesy_var'].set(courtesy)

        # Update UI totals
        if hasattr(app, 'update_grand_total'):
            app.update_grand_total()
    finally:
        app._in_table_audit = False

