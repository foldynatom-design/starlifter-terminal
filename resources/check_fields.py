f = open('source/pdf_engine.py', 'r', encoding='utf-8').read()
lines = f.split('\n')
for i, l in enumerate(lines):
    if i >= 1100:
        if "e.get('b'" in l or "e['t']" in l or "e['b']" in l:
            print(f"L{i+1}: {l.rstrip()[:100]}")
print("Done")
