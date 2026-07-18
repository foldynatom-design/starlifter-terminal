@echo off
echo ===================================================
echo Building Starlifter Requisition Terminal v0.6
echo ===================================================
pip install pyinstaller customtkinter opencv-python pillow fpdf fontTools

:: 1. Compile in Directory Mode
pyinstaller --clean --onedir --noconsole --name "Starlifter Requisition Terminal" --paths "." --collect-all fontTools --collect-all fpdf --hidden-import "fontTools.misc.bezierTools" --icon "app_icon.ico" entry.py

:: 2. Verify and repair C-extensions, Tcl/Tk DLLs and data directories
python post_build.py

:: 3. Create the resources folder structure next to the executable
set TARGET_DIR=dist\Starlifter Requisition Terminal
mkdir "%TARGET_DIR%\resources" 2>nul
mkdir "%TARGET_DIR%\resources\sounds" 2>nul
mkdir "%TARGET_DIR%\fonts" 2>nul

:: 4. Copy config
copy config.json "%TARGET_DIR%\"

:: 5. Copy main.pyc (compiled app core)
copy main.pyc "%TARGET_DIR%\"

:: 5b. Copy runtime Python patches (slang resolution, UI overrides)
copy ui_panel.py "%TARGET_DIR%\"
copy slang_helper.py "%TARGET_DIR%\"

:: 6. Copy logos + watermarks (root level — entry.py looks here first)
copy logo.png "%TARGET_DIR%\"
copy logo_uee44.png "%TARGET_DIR%\"
copy cvbg44_logo.png "%TARGET_DIR%\"
copy watermark_secured.png "%TARGET_DIR%\"
copy watermark_classified.png "%TARGET_DIR%\"
copy watermark_public.png "%TARGET_DIR%\"

:: 7. Copy resources (logos, DBs, video, ship grids)
copy resources\logo.png "%TARGET_DIR%\resources\"
copy resources\logo_dark.png "%TARGET_DIR%\resources\"
copy resources\logo_white.png "%TARGET_DIR%\resources\"
copy resources\logo_uee44.png "%TARGET_DIR%\resources\"
copy resources\logo_uee44_dark.png "%TARGET_DIR%\resources\"
copy resources\logo_uee44_white.png "%TARGET_DIR%\resources\"
copy resources\cvbg44_logo.png "%TARGET_DIR%\resources\"
copy resources\cvbg44_logo_dark.png "%TARGET_DIR%\resources\"
copy resources\cvbg44_logo_white.png "%TARGET_DIR%\resources\"
copy resources\sls29_logo.png "%TARGET_DIR%\resources\"
copy resources\ship_grids_db.json "%TARGET_DIR%\resources\"
copy resources\uex_trade_db.json "%TARGET_DIR%\resources\"
copy resources\uex_items_trade_db.json "%TARGET_DIR%\resources\"
copy resources\uex_locations_db.json "%TARGET_DIR%\resources\"
copy resources\uex_ships_db.json "%TARGET_DIR%\resources\"
if exist "resources\intro_video.mp4" copy "resources\intro_video.mp4" "%TARGET_DIR%\resources\"

:: 8. Copy sounds
copy resources\sounds\*.wav "%TARGET_DIR%\resources\sounds\"

:: 9. Copy fonts (.ttf only — NEVER copy .pkl files!)
:: .pkl files contain absolute paths from the BUILD machine (e.g. C:\Users\tomas.foldyna\...)
:: and will cause "No such file or directory" errors on any other machine.
:: fpdf 1.7.2 auto-generates .pkl on first run with correct local paths.
copy fonts\*.ttf "%TARGET_DIR%\fonts\"
if exist "fonts\intro_sound.wav" copy "fonts\intro_sound.wav" "%TARGET_DIR%\fonts\"

:: 10. Copy Signatures folder if exists
if exist "resources\Podpisy" xcopy /E /I "resources\Podpisy" "%TARGET_DIR%\resources\Podpisy"

echo ===================================================
echo Build complete! v0.6
echo The folder is available in: dist\Starlifter Requisition Terminal\
echo Double-click "Starlifter Requisition Terminal.exe" inside that folder.
echo ===================================================
pause
