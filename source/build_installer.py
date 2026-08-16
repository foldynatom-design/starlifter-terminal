"""
Build script for Starlifter Setup.exe installer.
Steps:
1. Build main app (PyInstaller)
2. Copy resources into dist
3. Build Uninstall.exe
4. Create app_files.zip from dist
5. Build Setup.exe (installer) with app_files.zip + Uninstall.exe + logo bundled inside
"""
import subprocess, os, sys, shutil, zipfile, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist", "Starlifter Requisition Terminal")
PY = sys.executable

def run(cmd, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    r = subprocess.run(cmd, shell=True, cwd=ROOT)
    if r.returncode != 0:
        print(f"FAILED: {label}")
        sys.exit(1)
    print(f"OK: {label}")

def cp(src, dst):
    os.makedirs(os.path.dirname(dst) if not os.path.isdir(dst) else dst, exist_ok=True)
    if os.path.isdir(src):
        if os.path.exists(dst) and os.path.isdir(dst):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

# Step 1: Build main app
run(f'"{PY}" -m PyInstaller -y --clean --onedir --noconsole '
    f'--name "Starlifter Requisition Terminal" --paths "." '
    f'--collect-all fontTools --collect-all fpdf --collect-all customtkinter '
    f'--hidden-import "fontTools.misc.bezierTools" '
    f'--hidden-import "cv2" '
    f'--icon "app_icon.ico" entry.py',
    "Build main app")

# Step 1b: Post-build repair
run(f'"{PY}" post_build.py', "Post-build verification")

# Step 2: Copy resources
print("\n" + "="*60)
print("  Copying resources into dist")
print("="*60)

# Root level files and directories
for f in ["config.json", "main.pyc", "logo.png", "logo_uee44.png", "cvbg44_logo.png",
          "watermark_secured.png", "watermark_classified.png", "watermark_public.png", "app_icon.ico",
          "ui_panel.py", "slang_helper.py", "vessel_templates.json", "packages.json",
          "cstone_fetcher.py", "data_validator.py", "fleet_helper.py", "lore_helper.py",
          "path_config.py", "pdf_block_extract.py", "pdf_engine.py", "sc_wiki_db.py",
          "sc_wiki_fetcher.py", "signature_helper.py", "storall_packer.py",
          "cargo_grid_renderer.py", "uex_sync.py", "src"]:
    src = os.path.join(ROOT, f)
    if os.path.exists(src):
        cp(src, os.path.join(DIST, f))

# Resources - copy ALL json, png, mp4, wav, subfolders (Podpisy, sounds, etc.)
res_dst = os.path.join(DIST, "resources")
os.makedirs(res_dst, exist_ok=True)
res_src = os.path.join(ROOT, "resources")
if os.path.exists(res_src):
    for root, dirs, files in os.walk(res_src):
        rel_dir = os.path.relpath(root, res_src)
        target_dir = os.path.join(res_dst, rel_dir) if rel_dir != "." else res_dst
        os.makedirs(target_dir, exist_ok=True)
        for fn in files:
            src_f = os.path.join(root, fn)
            dst_f = os.path.join(target_dir, fn)
            shutil.copy2(src_f, dst_f)

# Fonts - copy .ttf ONLY, NEVER .pkl!
fnt_dst = os.path.join(DIST, "fonts")
os.makedirs(fnt_dst, exist_ok=True)
fnt_src = os.path.join(ROOT, "fonts")
if os.path.exists(fnt_src):
    for f in glob.glob(os.path.join(fnt_src, "*.ttf")):
        cp(f, os.path.join(fnt_dst, os.path.basename(f)))
    if os.path.exists(os.path.join(fnt_src, "intro_sound.wav")):
        cp(os.path.join(fnt_src, "intro_sound.wav"), os.path.join(fnt_dst, "intro_sound.wav"))

print("OK: Resources copied")

# Step 3: Build Uninstall.exe
run(f'"{PY}" -m PyInstaller -y --onefile --noconsole '
    f'--name "Uninstall" --icon "app_icon.ico" uninstaller_src.py',
    "Build Uninstall.exe")

# Step 4: Create app_files.zip
print("\n" + "="*60)
print("  Creating app_files.zip")
print("="*60)
zip_path = os.path.join(ROOT, "app_files.zip")
if os.path.exists(zip_path):
    os.remove(zip_path)

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for dirpath, dirnames, filenames in os.walk(DIST):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            arcname = os.path.relpath(full, DIST)
            zf.write(full, arcname)

zip_mb = os.path.getsize(zip_path) / (1024*1024)
print(f"OK: app_files.zip = {zip_mb:.1f} MB")

# Step 5: Build Setup.exe (installer)
# Bundle: app_files.zip, Uninstall.exe, logo_uee44.png
uninst_path = os.path.join(ROOT, "dist", "Uninstall.exe")

run(f'"{PY}" -m PyInstaller -y --onefile --noconsole '
    f'--name "Starlifter_Setup" --icon "app_icon.ico" '
    f'--add-data "app_files.zip;." '
    f'--add-data "{uninst_path};." '
    f'--add-data "logo_uee44.png;." '
    f'--collect-all customtkinter '
    f'installer_src.py',
    "Build Setup.exe")

setup_path = os.path.join(ROOT, "dist", "Starlifter_Setup.exe")
if os.path.exists(setup_path):
    size_mb = os.path.getsize(setup_path) / (1024*1024)
    print(f"\n{'='*60}")
    print(f"  SUCCESS! Setup.exe ready: {size_mb:.1f} MB")
    print(f"  Path: {setup_path}")
    print(f"{'='*60}")
else:
    print("ERROR: Setup.exe not created!")
    sys.exit(1)
