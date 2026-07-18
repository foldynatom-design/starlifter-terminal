# -*- coding: utf-8 -*-
"""
signature_helper.py - Image processing for signatures, barcodes, R1 stamp.

Handles:
  - Signature extraction from sheet images
  - Barcode processing
  - R1 stamp generation
  - Signature alpha flatten + caching

Usage:
    from signature_helper import *
"""

import os
import sys
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def extract_signature_from_sheet(img):
    bbox = img.getbbox()
    if not bbox:
        return img
    ink_img = img.crop(bbox)
    w, h = ink_img.size
    col_ink = [0] * w
    for x in range(w):
        for y in range(h):
            pixel = ink_img.getpixel((x, y))
            if pixel[3] > 0:
                col_ink[x] += 1
    gaps = []
    in_gap = False
    gap_start = 0
    for x in range(w):
        is_empty = col_ink[x] <= 2
        if is_empty and not in_gap:
            in_gap = True
            gap_start = x
        elif not is_empty and in_gap:
            in_gap = False
            gaps.append((gap_start, x))
    if in_gap:
        gaps.append((gap_start, w))
    wide_gaps = [g for g in gaps if (g[1] - g[0]) >= 15]
    if wide_gaps:
        sub_images = []
        prev_end = 0
        for gap in wide_gaps:
            if gap[0] > prev_end:
                sub_images.append(ink_img.crop((prev_end, 0, gap[0], h)))
            prev_end = gap[1]
        if prev_end < w:
            sub_images.append(ink_img.crop((prev_end, 0, w, h)))
        sub_images = [sim for sim in sub_images if sim.getbbox()]
        if sub_images:
            return random.choice(sub_images)
    return ink_img

def get_signatures_dir():
    try:
        from path_config import PATHS
        app_dir = PATHS.app_root
    except Exception:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p0 = os.path.join(app_dir, 'resources', 'Podpisy')
    if os.path.exists(p0):
        return p0
    p1 = os.path.join(app_dir, 'Podpisy')
    if os.path.exists(p1):
        return p1
    # Check user's Downloads folder (portable fallback)
    p2 = os.path.join(os.path.expanduser("~"), "Downloads", "Podpisy")
    if os.path.exists(p2):
        return p2
    p3 = os.path.join(os.getcwd(), 'Podpisy')
    if not os.path.exists(p3):
        os.makedirs(p3, exist_ok=True)
    return p3

# Cache processed images - pre-processed PNGs don't need runtime processing
_SIG_CACHE = {}

def get_processed_barcode_path(podpisy_dir):
    """Return path to a random barcode PNG. Pre-processed = instant."""
    if 'barcode_paths' in _SIG_CACHE:
        cached = _SIG_CACHE['barcode_paths']
        return random.choice(cached) if cached else None
    
    processed = []
    for barcode_num in range(1, 5):
        # Try pre-processed PNG first, then JPEG fallback
        for ext in ['.png', '.jpeg', '.jpg']:
            p = os.path.join(podpisy_dir, f"B{barcode_num}{ext}")
            if os.path.exists(p):
                if ext == '.png':
                    # Pre-processed, use directly
                    processed.append(p)
                else:
                    # Runtime processing needed (fallback for old installs)
                    try:
                        from PIL import Image
                        img = Image.open(p).convert("RGBA")
                        if img.width > 600:
                            ratio = 600 / img.width
                            img = img.resize((600, int(img.height * ratio)), Image.LANCZOS)
                        datas = list(img.getdata())
                        newData = [(255,255,255,0) if px[0]>210 and px[1]>210 and px[2]>210 else px for px in datas]
                        img.putdata(newData)
                        bbox = img.getbbox()
                        if bbox: img = img.crop(bbox)
                        tmp = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", f"temp_barcode_{barcode_num}.png")
                        img.save(tmp, "PNG")
                        processed.append(tmp)
                    except Exception:
                        processed.append(p)
                break
    
    _SIG_CACHE['barcode_paths'] = processed
    return random.choice(processed) if processed else None

def process_signature(podpisy_dir, name_key, is_captain=False):
    """Return path to ONE random signature PNG. Picks one file, extracts one sig."""
    possible_files = []
    if is_captain:
        for i in range(1, 9):
            possible_files.append(f"{i}")
    else:
        name_key_lower = name_key.lower()
        if "thomas wolf" in name_key_lower:
            possible_files = ["Lt. Thomas Wolf 1", "Signature_of_Lt._Thomas_Wolf_2", "Signature_of_Lt._Thomas_Wolf_3"]
        elif "rebot1401" in name_key_lower:
            possible_files = ["Signature_Lstr_Rebot1401_1", "Signature_Lstr_Rebot1401_2", "Signature_Lstr_Rebot1401_3"]
        elif "cinnebar" in name_key_lower:
            possible_files = ["Signature_of_Rstr._Cinnebar_1", "Signature_of_Rstr._Cinnebar_2", "Signature_of_Rstr._Cinnebar_3"]
        elif "odin borr" in name_key_lower:
            possible_files = ["Signature_Str._Odin_Borr_1", "Signature_Str._Odin_Borr_2", "Signature_Str._Odin_Borr_3"]
    if not possible_files:
        return None
    
    cache_key = f"sig_{name_key}_{is_captain}"
    if cache_key in _SIG_CACHE:
        cached = _SIG_CACHE[cache_key]
        return cached if cached else None
    
    # Pick ONE random file — don't process all variants
    random.shuffle(possible_files)
    
    for chosen_base in possible_files:
        sig_path = None
        # Try PNG first (pre-processed), then JPEG
        for ext in [".png", ".jpeg", ".jpg"]:
            p = os.path.join(podpisy_dir, chosen_base + ext)
            if os.path.exists(p):
                sig_path = p
                break
        if not sig_path:
            # Fuzzy search
            try:
                for f in os.listdir(podpisy_dir):
                    f_base = os.path.splitext(f)[0]
                    if f_base.lower().strip() == chosen_base.lower().strip():
                        sig_path = os.path.join(podpisy_dir, f)
                        break
            except Exception:
                pass
        if not sig_path or not os.path.exists(sig_path):
            continue
        
        # Found a valid file — process THIS ONE only
        result_path = _process_single_signature(sig_path, chosen_base)
        if result_path:
            _SIG_CACHE[cache_key] = result_path
            return result_path
    
    _SIG_CACHE[cache_key] = None
    return None


def _process_single_signature(sig_path, chosen_base):
    """Process a single signature image file. Extract one sig from multi-sig sheets."""
    if sig_path.lower().endswith('.png'):
        try:
            from PIL import Image
            img = Image.open(sig_path).convert("RGBA")
            # Keep only ink pixels (blue signatures + dark stamp), remove everything else
            datas = list(img.getdata())
            newData = []
            for px in datas:
                r, g, b, a = px
                # Keep dark pixels (stamp ink, dark lines)
                if r < 80 and g < 80 and b < 80:
                    newData.append(px)
                # Keep blue-ish pixels (signature ink: blue > red and blue > green)
                elif b > 100 and b > r * 1.2 and b > g * 1.1:
                    newData.append(px)
                # Keep very dark blue/navy
                elif r < 120 and g < 120 and b < 180 and (b > r or b > g):
                    newData.append(px)
                else:
                    # Everything else → transparent
                    newData.append((255, 255, 255, 0))
            img.putdata(newData)
            # Extract single signature from multi-sig sheets
            img = extract_signature_from_sheet(img)
            # Crop to ink bounds
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            # Flatten alpha onto page background color
            bg = Image.new("RGBA", img.size, (245, 247, 250, 255))
            bg.paste(img, mask=img.split()[3])
            flat_path = os.path.join(
                os.path.expanduser("~"), "AppData", "Local", "Temp",
                f"temp_sig_{chosen_base.replace(' ', '_')}_flat.png")
            bg.convert("RGB").save(flat_path)
            return flat_path
        except Exception:
            return sig_path
    else:
        # Runtime processing fallback for JPEG
        try:
            from PIL import Image
            img = Image.open(sig_path).convert("RGBA")
            if img.width > 800:
                ratio = 800 / img.width
                img = img.resize((800, int(img.height * ratio)), Image.LANCZOS)
            datas = list(img.getdata())
            newData = [(255,255,255,0) if px[0]>200 and px[1]>200 and px[2]>200 else px for px in datas]
            img.putdata(newData)
            img = extract_signature_from_sheet(img)
            bbox = img.getbbox()
            if bbox: img = img.crop(bbox)
            tmp = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", f"temp_sig_{chosen_base.replace(' ', '_')}.png")
            img.save(tmp, "PNG")
            return tmp
        except Exception:
            return sig_path

def process_r1_stamp(podpisy_dir):
    r1_path = None
    extensions = [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"]
    for ext in extensions:
        p = os.path.join(podpisy_dir, "R1" + ext)
        if os.path.exists(p):
            r1_path = p
            break
    if not r1_path:
        try:
            for f in os.listdir(podpisy_dir):
                f_base, f_ext = os.path.splitext(f)
                if f_base.lower() == "r1":
                    r1_path = os.path.join(podpisy_dir, f)
                    break
        except Exception:
            pass
    if not r1_path:
        return None
    
    # Check cache
    if 'r1_stamp' in _SIG_CACHE:
        return _SIG_CACHE['r1_stamp']
    
    # If PNG, remove background and flatten
    if r1_path.lower().endswith('.png'):
        try:
            from PIL import Image
            img = Image.open(r1_path).convert("RGBA")
            if img.width > 300:
                ratio = 300 / img.width
                img = img.resize((300, int(img.height * ratio)), Image.LANCZOS)
            datas = list(img.getdata())
            newData = [(255,255,255,0) if px[0]>210 and px[1]>210 and px[2]>210 else px for px in datas]
            img.putdata(newData)
            rotated_img = img.rotate(15, expand=True, resample=Image.BICUBIC)
            r_datas = list(rotated_img.getdata())
            r_newData = [(px[0], px[1], px[2], 100) if px[3] > 0 else px for px in r_datas]
            rotated_img.putdata(r_newData)
            bbox = rotated_img.getbbox()
            if bbox: rotated_img = rotated_img.crop(bbox)
            tmp = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "temp_r1_stamp_png.png")
            rotated_img.save(tmp, "PNG")
            _SIG_CACHE['r1_stamp'] = tmp
            return tmp
        except Exception:
            _SIG_CACHE['r1_stamp'] = r1_path
            return r1_path
    
    # Runtime processing fallback for JPEG
    try:
        from PIL import Image
        img = Image.open(r1_path).convert("RGBA")
        if img.width > 300:
            ratio = 300 / img.width
            img = img.resize((300, int(img.height * ratio)), Image.LANCZOS)
        datas = list(img.getdata())
        newData = [(255,255,255,0) if px[0]>210 and px[1]>210 and px[2]>210 else px for px in datas]
        img.putdata(newData)
        rotated_img = img.rotate(15, expand=True, resample=Image.BICUBIC)
        r_datas = list(rotated_img.getdata())
        r_newData = [(px[0], px[1], px[2], 100) if px[3] > 0 else px for px in r_datas]
        rotated_img.putdata(r_newData)
        bbox = rotated_img.getbbox()
        if bbox: rotated_img = rotated_img.crop(bbox)
        tmp = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "temp_r1_stamp.png")
        rotated_img.save(tmp, "PNG")
        _SIG_CACHE['r1_stamp'] = tmp
        return tmp
    except Exception as e:
        print(f"Error processing R1 stamp: {e}")
        return r1_path

