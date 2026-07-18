# Batch replace bare 'except:' with 'except Exception:' in source files
# This is the safe minimum fix - catches everything except SystemExit/KeyboardInterrupt
import re, os, sys

files = [
    'source/entry.py',
    'source/pdf_engine.py',
    'source/uex_sync.py',
    'source/cargo_grid_renderer.py',
    'source/signature_helper.py',
]

# Patterns to fix:
# "except:" -> "except Exception:"  (but NOT "except Exception:" which is already OK)
# "except: pass" -> "except Exception:\n    pass"  (inline)

total_fixed = 0
for fpath in files:
    if not os.path.exists(fpath):
        continue
    
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace bare "except:" that is NOT already "except Exception:" or "except SomeError:"
    # Match "except:" but not "except SomeName:" 
    # Pattern: "except:" at word boundary, not followed by a class name
    content = re.sub(
        r'\bexcept\s*:',
        'except Exception:',
        content
    )
    
    # But don't double up "except Exception Exception:"
    content = content.replace('except Exception Exception:', 'except Exception:')
    
    if content != original:
        count = content.count('except Exception:') - original.count('except Exception:')
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  {fpath}: fixed {count} bare excepts")
        total_fixed += count
    else:
        print(f"  {fpath}: no changes needed")

print(f"\nTotal fixed: {total_fixed}")
