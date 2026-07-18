# -*- coding: utf-8 -*-
"""Find exact line ranges of duplicate functions in entry.py for removal."""
import ast, sys

with open('source/entry.py', 'r', encoding='utf-8') as f:
    source = f.read()
    lines = source.split('\n')

# Parse AST to find function boundaries
try:
    tree = ast.parse(source)
except SyntaxError as e:
    print(f"Parse error: {e}")
    sys.exit(1)

# Functions to remove (now imported from helpers)
REMOVE = {
    'extract_rank', 'get_signatures_dir', 'process_signature',
    'process_r1_stamp', 'get_telemetry', '_recommend_shuttle', '_pick_box_size',
    'get_processed_barcode_path', 'extract_signature_from_sheet',
}

# Find all top-level function defs
ranges = []
all_funcs = []
for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.FunctionDef):
        all_funcs.append((node.name, node.lineno, node.end_lineno))

for name, start, end in all_funcs:
    if name in REMOVE:
        ranges.append((name, start, end))
        print(f"  REMOVE: L{start:4d}-L{end:4d} ({end-start+1:3d} lines): {name}")

# Also find BG44_RANKS dict and _SIG_CACHE (now imported)
for i, line in enumerate(lines, 1):
    if line.strip().startswith('BG44_RANKS = {'):
        # Find closing brace
        for j in range(i, min(i+30, len(lines)+1)):
            if lines[j-1].strip() == '}':
                ranges.append(('BG44_RANKS', i, j))
                print(f"  REMOVE: L{i:4d}-L{j:4d} ({j-i+1:3d} lines): BG44_RANKS dict")
                break
    if line.strip().startswith('_SIG_CACHE = '):
        ranges.append(('_SIG_CACHE', i, i))
        print(f"  REMOVE: L{i:4d}-L{i:4d} (  1 lines): _SIG_CACHE dict")

ranges.sort(key=lambda x: x[1])
total_removable = sum(end - start + 1 for _, start, end in ranges)
print(f"\n  Total removable: {total_removable} lines")
print(f"  entry.py after: ~{len(lines) - total_removable} lines")
