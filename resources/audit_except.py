# Audit bare except: and except Exception: patterns
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

files = [f'source/{m}.py' for m in [
    'entry', 'pdf_engine', 'uex_sync', 'cargo_grid_renderer',
    'path_config', 'storall_packer', 'fleet_helper',
    'signature_helper', 'lore_helper', 'slang_helper'
]]

total = 0
for f in files:
    if not os.path.exists(f):
        continue
    lines = open(f, 'r', encoding='utf-8').readlines()
    hits = []
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith('except:') or s == 'except Exception:':
            hits.append((i+1, s))
    if hits:
        print(f"\n{f} ({len(hits)} bare excepts):")
        for ln, txt in hits:
            # Show what follows
            next_line = lines[ln].strip() if ln < len(lines) else ''
            print(f"  L{ln}: {txt:30s} -> {next_line[:50]}")
        total += len(hits)

print(f"\nTOTAL: {total} bare except patterns")
