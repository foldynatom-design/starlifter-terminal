# 🚀 Starlifter Requisition Terminal

**UEE Logistics Center — Tactical Requisition Manifest Utility**  
*29th Starlifters Squadron · 44th Battle Group · Star Citizen RP Tool*

---

## 📦 Latest Release: v0.6.1

Download the latest installer from [GitHub Releases](https://github.com/foldynatom-design/starlifter-terminal/releases/tag/v0.6.1):
- **Installer**: [`Starlifter_Setup.exe`](https://github.com/foldynatom-design/starlifter-terminal/releases/download/v0.6.1/Starlifter_Setup.exe)

### What's New in v0.6.1:
- Fixed application startup runtime dependencies and packaging (`main.pyc`, `rp_stories.py`, `api.py`).
- Fixed Supply Route PDF generation and shuttle recommendation calculations.
- Purged checkerboard artifacts from all signature assets for crisp alpha transparency.
- Full uninstaller and Start Menu / Desktop shortcut registration.

---

## 📋 Features

### Requisition Manifest (PDF)
- Generate military-style requisition PDFs with cargo tables, totals, and commander signatures.
- Classification levels: **PUBLIC / SECURED / CLASSIFIED** with matching watermarks and security headers.
- Automatic ledger hash ID tracking.
- Digital signature fields with pre-loaded squadron signatures.

### Supply Route PDF
- Cargo load planning with box sizes, quantities, and aUEC pricing.
- Auto-boxing system (Stor-All containers calculated automatically).
- Courtesy item tagging.
- Single and batch export options.

### Cargo Management & Stor-All Packing
- Physical Stor-All grid volumes enforced (1, 2, 4, 8 SCU).
- Quick-Add with category filtering from trade databases.
- Custom cargo lines for non-database items.
- Per-item pricing and total aUEC calculations.
- Clipboard copy/paste import and export.

### Shuttle & Hangar Recommendation Engine
- Recommends best cargo shuttle / mothership based on cargo volume and pad sizing.
- Pure-cargo filtering for freight transport routes.

### Trade Route Assistant
- Integrated trade database with commodity prices and buy/sell locations.

---

## 💾 Installation

### Requirements
- Windows 10 / 11 (64-bit)
- ~500 MB free disk space

### Steps
1. Download **`Starlifter_Setup.exe`** from [Releases](https://github.com/foldynatom-design/starlifter-terminal/releases).
2. Right-click the file → **Properties** → check **"Unblock"** (if Windows SmartScreen appears).
3. Run `Starlifter_Setup.exe` and click **BEGIN INSTALLATION**.
4. The terminal will be installed to `%LOCALAPPDATA%\Starlifter_Terminal\` with Desktop and Start Menu shortcuts.

---

## 🗑️ Uninstall

- **Windows Settings:** Apps → Installed Apps → "Starlifter Requisition Terminal v0.6.1" → **Uninstall**
- **Direct:** Run `Uninstall.exe` in `%LOCALAPPDATA%\Starlifter_Terminal\`

---

## 🏗️ Building from Source

```bash
# Install dependencies
pip install pyinstaller customtkinter opencv-python pillow fpdf fontTools

# Build executable and installer
python build_installer.py

# Output: dist/Starlifter_Setup.exe
```

---

## 🌐 Data Sources

- **UEX Corp** ([uexcorp.space](https://uexcorp.space/)) — Commodity & trade prices, ship specs.
- **Star Citizen Wiki** ([api.star-citizen.wiki](https://api.star-citizen.wiki/)) — Vehicle data, item details.
- **SC-Cargo.space** ([sc-cargo.space](https://sc-cargo.space/)) — Ship cargo grid dimensions.

---

## 📜 License

Fan-made tool for Star Citizen roleplay logistics.  
**29th Starlifters Squadron / 44th Battle Group**  
*Not for commercial use.*
