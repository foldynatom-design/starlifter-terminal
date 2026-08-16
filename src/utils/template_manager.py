# -*- coding: utf-8 -*-
"""
template_manager.py - Persistent Tree & Storage Manager for Saved Ship Loadouts and Item Packages.
Provides 100% reliable load/save API for future templates and package definitions.
"""
import os
import json
from datetime import datetime
from path_config import PATHS

class TemplateManager:
    @staticmethod
    def _get_vessel_file_path():
        return os.path.join(PATHS.config_dir, "vessel_templates.json")

    @staticmethod
    def load_vessels():
        """Retrieve all saved vessel loadout templates from vessel_templates.json (with config.json fallback/migration)."""
        v_path = TemplateManager._get_vessel_file_path()
        if os.path.exists(v_path):
            try:
                with open(v_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("vessels", data)
            except Exception as e:
                print(f"[TemplateManager] Error reading vessel_templates.json: {e}")

        # Fallback & Migration from config.json if vessel_templates.json is missing
        cfg_path = os.path.join(PATHS.config_dir, "config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    vessels = data.get("vessels", {})
                    if vessels:
                        # Auto-migrate vessels to dedicated vessel_templates.json
                        TemplateManager.save_all_vessels(vessels)
                        return vessels
            except Exception as e:
                print(f"[TemplateManager] Error reading config.json for vessel migration: {e}")
        return {}

    @staticmethod
    def save_all_vessels(vessels_dict):
        """Save complete dictionary of vessel loadouts to vessel_templates.json."""
        v_path = TemplateManager._get_vessel_file_path()
        try:
            with open(v_path, "w", encoding="utf-8") as f:
                json.dump({"vessels": vessels_dict}, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[TemplateManager] Failed to write vessel_templates.json: {e}")
            return False

    @staticmethod
    def save_vessel(vessel_name, loadout_items):
        """Save or update a vessel template in vessel_templates.json."""
        if not vessel_name:
            return False
        vessels = TemplateManager.load_vessels()
        vessels[vessel_name] = loadout_items
        res = TemplateManager.save_all_vessels(vessels)
        if res:
            print(f"[TemplateManager] Saved vessel loadout '{vessel_name}' ({len(loadout_items)} items) to vessel_templates.json.")
        return res

    @staticmethod
    def delete_vessel(vessel_name):
        """Delete a vessel template from vessel_templates.json."""
        vessels = TemplateManager.load_vessels()
        if vessel_name in vessels:
            del vessels[vessel_name]
            return TemplateManager.save_all_vessels(vessels)
        return False

    @staticmethod
    def export_vessels_to_json(filepath):
        """Export all vessel loadouts, custom fleet vessels, and packages to external JSON file for sharing."""
        try:
            vessels = TemplateManager.load_vessels()
            packages = TemplateManager.load_packages()
            
            # Also get custom_vessels from config.json
            custom_vessels = {}
            cfg_path = os.path.join(PATHS.config_dir, "config.json")
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        custom_vessels = cfg.get("custom_vessels", {})
                except Exception: pass

            payload = {
                "format": "starlifter_fleet_export",
                "version": "1.0",
                "vessels": vessels,
                "custom_vessels": custom_vessels,
                "packages": packages
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            print(f"[TemplateManager] Exported {len(vessels)} vessel loadouts, {len(custom_vessels)} fleet vessels, and {len(packages)} packages to {filepath}")
            return True, len(vessels) + len(custom_vessels)
        except Exception as e:
            print(f"[TemplateManager] Export error: {e}")
            return False, str(e)

    @staticmethod
    def import_vessels_from_json(filepath):
        """Import vessel loadouts, custom fleet vessels, and packages from external JSON file."""
        if not os.path.exists(filepath):
            return False, "File does not exist"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            imported_count = 0
            # 1. Import vessels
            incoming_vessels = data.get("vessels", {})
            if isinstance(incoming_vessels, dict) and incoming_vessels:
                current_vessels = TemplateManager.load_vessels()
                current_vessels.update(incoming_vessels)
                TemplateManager.save_all_vessels(current_vessels)
                imported_count += len(incoming_vessels)

            # 2. Import custom vessels
            incoming_custom = data.get("custom_vessels", {})
            if isinstance(incoming_custom, dict) and incoming_custom:
                cfg_path = os.path.join(PATHS.config_dir, "config.json")
                cfg = {}
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                    except Exception: pass
                
                curr_custom = cfg.get("custom_vessels", {})
                curr_custom.update(incoming_custom)
                cfg["custom_vessels"] = curr_custom
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)
                imported_count += len(incoming_custom)

            # 3. Import packages if present
            incoming_pkgs = data.get("packages", {})
            if isinstance(incoming_pkgs, dict) and incoming_pkgs:
                curr_pkgs = TemplateManager.load_packages()
                curr_pkgs.update(incoming_pkgs)
                pkg_path = os.path.join(PATHS.config_dir, "packages.json")
                with open(pkg_path, "w", encoding="utf-8") as f:
                    json.dump(curr_pkgs, f, indent=2, ensure_ascii=False)

            print(f"[TemplateManager] Imported {imported_count} fleet loadouts/vessels from {filepath}")
            return True, imported_count
        except Exception as e:
            print(f"[TemplateManager] Import error: {e}")
            return False, str(e)

    @staticmethod
    def export_packages_to_json(filepath):
        """Export all custom item packages to a portable JSON file."""
        try:
            packages = TemplateManager.load_packages()
            export_payload = {
                "schema": "starlifter_package_export",
                "version": 1,
                "exported_at": datetime.now().isoformat(),
                "packages": packages
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_payload, f, indent=2, ensure_ascii=False)
            return True, len(packages)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def import_packages_from_json(filepath):
        """Import item packages from a JSON file and auto-register new items."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            incoming_pkgs = data.get("packages", {}) if isinstance(data, dict) and "packages" in data else data
            if not isinstance(incoming_pkgs, dict) or not incoming_pkgs:
                return False, "No valid package definitions found in JSON file."
            
            curr_pkgs = TemplateManager.load_packages()
            curr_pkgs.update(incoming_pkgs)
            pkg_path = os.path.join(PATHS.config_dir, "packages.json")
            with open(pkg_path, "w", encoding="utf-8") as f:
                json.dump(curr_pkgs, f, indent=2, ensure_ascii=False)
            
            # Auto-register items
            all_imported_items = []
            for p_name, p_items in incoming_pkgs.items():
                if isinstance(p_items, list):
                    all_imported_items.extend(p_items)
            TemplateManager.register_discovered_items(all_imported_items)
            
            return True, len(incoming_pkgs)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def load_packages():
        """Retrieve custom item packages from packages.json."""
        pkg_path = os.path.join(PATHS.config_dir, "packages.json")
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[TemplateManager] Error reading packages.json: {e}")
        return {}


    @staticmethod
    def register_discovered_items(items_list):
        """Enrich frequent_items.json with newly discovered items from custom packages or loadouts."""
        if not items_list:
            return
        try:
            freq_path = os.path.join(PATHS.resources, "frequent_items.json")
            if not os.path.exists(freq_path):
                return
            with open(freq_path, "r", encoding="utf-8") as f:
                freq = json.load(f)
            
            existing_names = {str(it.get("name", "")).lower().strip() for it in freq}
            added = False
            for raw_it in items_list:
                name = str(raw_it.get("name", "") if isinstance(raw_it, dict) else raw_it).strip()
                if not name or name.lower() in existing_names:
                    continue
                
                p_val = raw_it.get("price", 0) if isinstance(raw_it, dict) else 0
                cat_val = raw_it.get("category", "Equipment") if isinstance(raw_it, dict) else "Equipment"
                freq.append({
                    "name": name,
                    "category": cat_val,
                    "price": p_val if isinstance(p_val, (int, float)) else 0,
                    "volume": 0.01,
                    "unit": "unit",
                    "description": f"{name} (User Package Item)"
                })
                existing_names.add(name.lower())
                added = True
            
            if added:
                with open(freq_path, "w", encoding="utf-8") as f:
                    json.dump(freq, f, indent=2, ensure_ascii=False)
                print(f"[TemplateManager] Auto-learned and persisted newly discovered items into frequent_items.json.")
        except Exception as e:
            print(f"[TemplateManager] Auto-learn items notice: {e}")

    @staticmethod
    def save_package(package_name, items):
        """Save a new or modified custom package to packages.json and register items."""
        if not package_name:
            return False
        pkg_path = os.path.join(PATHS.config_dir, "packages.json")
        pkgs = TemplateManager.load_packages()
        pkgs[package_name] = items
        try:
            with open(pkg_path, "w", encoding="utf-8") as f:
                json.dump(pkgs, f, indent=2, ensure_ascii=False)
            TemplateManager.register_discovered_items(items)
            print(f"[TemplateManager] Saved custom package '{package_name}' ({len(items)} items) to packages.json.")
            return True
        except Exception as e:
            print(f"[TemplateManager] Failed to save package: {e}")
            return False

    @staticmethod
    def delete_package(package_name):
        """Remove a custom package from packages.json."""
        pkg_path = os.path.join(PATHS.config_dir, "packages.json")
        pkgs = TemplateManager.load_packages()
        if package_name in pkgs:
            del pkgs[package_name]
            try:
                with open(pkg_path, "w", encoding="utf-8") as f:
                    json.dump(pkgs, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"[TemplateManager] Failed to delete package: {e}")
        return False

