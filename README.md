# 🚀 Starlifter Requisition Terminal

**UEE Logistics Center — Tactical Requisition Manifest Utility**  
*29th Starlifters Squadron · 44th Battle Group · Star Citizen RP Tool*

---

## 📋 Features

### Requisition Manifest (PDF)
- Generate classified **military-style requisition PDFs** with cargo tables, totals, and commander signatures
- Classification levels: **PUBLIC / SECURED / CLASSIFIED** — each with matching watermark and security header
- Automatic **ledger hash ID** for document tracking
- Digital signature fields with pre-loaded squadron signatures

### Supply Route PDF
- Full **cargo load planning** with box sizes, quantities, and aUEC pricing
- Auto-boxing system (Stor-All 1 SCU containers calculated automatically)
- Courtesy item tagging
- Batch export — generate multiple PDFs at once with one click
- **`>> TRANSMITTING UPLINK...`** animation on generate

### Cargo Management
- Quick-Add from live **UEX trade database** with category filter
- Custom cargo lines for non-database items
- Per-item pricing with **total aUEC** calculation
- Copy draft / copy final with prices to clipboard

### Shuttle & Hangar Recommendation Engine
- Recommends the best **mothership** (Idris, Kraken, Polaris, Javelin...) based on cargo and pad size
- Verified in-game hangar fit data for each ship class

### Trade Route Assistant
- Live **Star Citizen UEX** trade route database
- Commodity prices, buy/sell locations
- Route optimizer based on cargo capacity

### Terminal Aesthetics
- Full **military terminal UI** — dark amber theme, monospace typography
- Intro video + sound on launch
- Sound effects on PDF generation and key actions
- Communication channel selector (OPEN_PUBLIC / RESTRICTED / ENCRYPTED)

---

## 💾 Installation

### Requirements
- Windows 10 / 11 (64-bit)
- ~500 MB free disk space

### Steps

1. Download **`Starlifter_Setup.exe`** from [Releases](https://github.com/foldynatom-design/starlifter-terminal/releases)
2. **Unblock the file** before running *(see section below)*
3. Run `Starlifter_Setup.exe`
4. Click **BEGIN INSTALLATION**
5. The installer will:
   - Extract all application files to `%LOCALAPPDATA%\Starlifter_Terminal\`
   - Create a **Desktop shortcut**
   - Register in **Start Menu**
   - Add to **Windows Add/Remove Programs**

---

## 🔓 How to Unblock the Installer (Windows SmartScreen)

Because this app is **not commercially code-signed**, Windows will show a SmartScreen warning. This is normal for independent tools. Follow these steps:

### Option A — Right-click Unblock (Recommended)
1. Right-click `Starlifter_Setup.exe`
2. Select **Properties**
3. At the bottom of the **General** tab, check ✅ **"Unblock"**
4. Click **OK**
5. Run the installer normally

### Option B — SmartScreen "More info"
1. Double-click the installer
2. When SmartScreen appears, click **"More info"**
3. Click **"Run anyway"**

### Option C — Windows Defender / Antivirus
If your antivirus quarantines the file:
1. Open **Windows Security** → **Virus & threat protection**
2. Go to **Protection history**
3. Find the quarantined file → click **Restore** or **Allow**

> ℹ️ **Why does this happen?**  
> Windows flags executables that don't have a paid Microsoft code-signing certificate. The source code for this tool is fully open — you can review it in this repository before running.

---

## 🗑️ Uninstall

**Option A — Windows Settings:**
Settings → Apps → "Starlifter Requisition Terminal v0.6" → Uninstall

**Option B — Direct:**
Run `Uninstall.exe` in `%LOCALAPPDATA%\Starlifter_Terminal\`

The uninstaller removes:
- All application files from AppData
- Desktop shortcut
- Start Menu entry
- Windows Programs registry entry

---

## 🏗️ Building from Source

Requirements: Python 3.11+, PyInstaller

```bash
# Install dependencies
pip install pyinstaller customtkinter opencv-python pillow fpdf2 fontTools

# Full build (app + installer)
python build_installer.py

# Output: dist/Starlifter_Setup.exe
```

> **Note:** Never commit `.pkl` font cache files — they contain absolute paths from the build machine and will cause PDF errors on other PCs. The `.gitignore` already excludes them.

---

## 📁 File Structure

```
Starlifter_Terminal/          ← Install location (%LOCALAPPDATA%)
├── Starlifter Requisition Terminal.exe
├── main.pyc                  ← Core application logic
├── config.json               ← Settings
├── app_icon.ico
├── logo.png / logo_uee44.png
├── watermark_*.png
├── fonts/
│   ├── Roboto-Regular.ttf
│   └── Roboto-Bold.ttf
├── resources/
│   ├── ship_grids_db.json
│   ├── trade_db.json
│   ├── sounds/
│   └── Podpisy/              ← Commander signature images
└── _internal/                ← Python runtime (PyInstaller)
```

---

## ⚠️ Known Issues

- **Category filter autofill** — The category filter for writing/search/delete can be a bit janky. It works with patience when trying to autofill entries.

---

## 🌐 Data Sources

This tool pulls live data from the following community APIs:

| Source | URL | Data Provided |
|--------|-----|---------------|
| **UEX Corp** | [uexcorp.space](https://uexcorp.space/) | Commodity & item trade prices, buy/sell locations, ship specs (SCU, pad size) |
| **Star Citizen Wiki** | [api.star-citizen.wiki](https://api.star-citizen.wiki/) | Vehicle dimensions, item volumes/weights, production status, manufacturer data |
| **SC-Cargo.space** | [sc-cargo.space](https://sc-cargo.space/) | Ship cargo grid layouts — exact bay dimensions (width × height × length per group) |

All data is fetched on-demand via the **⟳ Verify All Data** button and cached locally for offline use.

> 🙏 Huge thanks to the maintainers of these community projects for making their data freely available.

---

## 📌 Known Limitations

- Requires an active internet connection for **live trade data and verification** (offline mode uses cached DB)
- Intro video may not play on systems without media codecs (app continues normally)
- Not affiliated with Cloud Imperium Games — this is a fan-made RP tool

---

## 📜 License

Fan-made tool for Star Citizen roleplay logistics.  
**29th Starlifters Squadron / 44th Battle Group**  
*Not for commercial use.*
