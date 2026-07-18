import os
for fname in os.listdir('source'):
    if fname.endswith('.py'):
        fp = os.path.join('source', fname)
        with open(fp, 'r', encoding='utf-8') as f:
            for i, l in enumerate(f, 1):
                if '\u25c9' in l:
                    safe = l.rstrip().replace('\u25c9','<CIRCLE>')
                    with open('resources/circle_hits.txt', 'a', encoding='ascii', errors='replace') as o:
                        o.write(f"{fname} L{i}: {safe[:120]}\n")
print("Done")
