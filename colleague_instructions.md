# Pokyny pro AI Asistenta (Antigravity Agent Handoff)

Tento soubor slouží jako předávací dokumentace pro další relaci Antigravity agenta na druhém počítači uživatele.

## Stav Projektu
1. **100% Úspěšnost Synchronizace**:
   Metoda `run_sync` v `entry.py` stahuje všechny kategorie z UEX Corp API, aktualizuje ceník v `config.json` a generuje `wiki_locations.json` se všemi nákupními terminály.
2. **Speciální Mapování**:
   - `Cambio Multi-tool Battery` kopíruje lokace od `Cambio SRT` (cena 63).
   - `Maxlift Tractor Beam Battery` kopíruje lokace od `MaxLift Tractor Beam` (cena 175).
   - `Quantainium Water Bottle` se automaticky přemapovává na nákup `CRUZ Lux` (cena 7).
   - `Omni-AFS Saphire Slate` se přemapovává na nákup `Tailwind Flight Suit` (cena 1450).
   - `Cambio SRT Canister` se stahuje z UEX (kategorie 17).

## Úkol pro dalšího agenta (Oprava na druhém počítači)
Při spuštění na druhém počítači uživatele zkontroluj a oprav následující chybějící části:

1. **Uvítací Video a Zvuk**:
   - Původní kód v `main.pyc` měl natvrdo zadanou absolutní cestu k videu na disku kolegu: `C:\\Users\\tomfo\\Downloads\\má_to_být_animace_při_spoušte.mp4`.
   - V souboru `entry.py` jsme to přepsali tak, aby aplikace hledala video relativně pod názvem `intro_video.mp4` nebo `má_to_být_animace_při_spoušte.mp4` v kořenovém adresáři.
   - Uživatel má video a zvuk uloženy ve svém projektu Google Flow na adrese: `https://labs.google/fx/cs/tools/flow/project/4f60c83e-2487-4d7d-9e16-4664869dc92e`.
   - **Tvoje akce**: Stáhni nebo pomoz uživateli stáhnout neřezané video a zvuk šumu z této Google Flow stránky. Umísti video jako `intro_video.mp4` do kořenové složky a zvuk jako `fonts/intro_sound.wav`. Zkontroluj, že se při startu správně přehrají.

2. **Jiný vzhled aplikace (Custom Appearance / Theme)**:
   - Uživatel zmínil, že na druhém počítači je jiný (lepší) vzhled aplikace.
   - **Tvoje akce**: Vyhledej na druhém počítači starší verzi projektu nebo záložní soubory a podívej se, zda nepoužívaly jiný barevný motiv (např. tmavý/světlý režim CustomTkinter, custom `.json` motiv, nebo jiné nastavení barev typu `color_panel_bg`). Pokud motiv najdeš, integruj ho do `entry.py` (např. přes nastavení `customtkinter.set_default_color_theme(...)`).

3. **Sestavení finální verze pro GitHub**:
   - Po ověření videa, zvuku a vzhledu sestav aplikaci pomocí přiloženého `build.bat` a připrav ji k nahrání na uživatelův GitHub.
