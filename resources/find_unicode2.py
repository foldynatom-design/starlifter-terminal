with open('source/pdf_engine.py', 'r', encoding='utf-8') as f:
    for i, l in enumerate(f, 1):
        if i >= 1100:
            if '\u25c9' in l or '\u26a0' in l or '\u2192' in l:
                safe = l.rstrip().replace('\u25c9','<CIRCLE>').replace('\u26a0','<WARN>').replace('\u2192','<ARROW>')
                with open('resources/unicode_hits2.txt', 'a', encoding='ascii', errors='replace') as o:
                    o.write(f"L{i}: {safe[:120]}\n")
print("Done")
