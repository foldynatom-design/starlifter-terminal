import re
f = open('source/pdf_engine.py', 'r', encoding='utf-8').read()
lines = f.split('\n')
symbols = {'\u26a0': '[!]', '\u25c9': '(*)', '\u2192': '->', '\u25cf': '*', '\u25cb': 'o', '\u25a0': '#', '\u25a1': '[]', '\u2588': '#', '\u2014': '--', '\u2013': '-', '\u2022': '*'}
for i, l in enumerate(lines):
    if i >= 1100:
        for sym in symbols:
            if sym in l:
                with open('resources/unicode_hits.txt', 'a', encoding='utf-8') as out:
                    out.write(f"L{i+1}: {sym!r} -> {symbols[sym]!r} | {l.rstrip()[:120]}\n")
print("Done - check resources/unicode_hits.txt")
