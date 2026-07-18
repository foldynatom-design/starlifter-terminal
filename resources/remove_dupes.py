# -*- coding: utf-8 -*-
"""Remove duplicate functions from entry.py (now imported from helper modules)."""
import ast

with open('source/entry.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

source = ''.join(lines)
tree = ast.parse(source)

# Functions to remove
REMOVE_FUNCS = {
    'extract_rank', 'get_signatures_dir', 'process_signature',
    'process_r1_stamp', 'get_telemetry', '_recommend_shuttle', '_pick_box_size',
    'get_processed_barcode_path', 'extract_signature_from_sheet',
}

# Collect line ranges to delete (1-indexed)
delete_ranges = []

# Find functions
for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.FunctionDef) and node.name in REMOVE_FUNCS:
        delete_ranges.append((node.lineno, node.end_lineno, node.name))

# Find BG44_RANKS dict
for i, line in enumerate(lines, 1):
    if line.strip().startswith('BG44_RANKS = {'):
        for j in range(i, min(i + 30, len(lines) + 1)):
            if lines[j-1].strip() == '}':
                delete_ranges.append((i, j, 'BG44_RANKS'))
                break
    if line.strip().startswith('_SIG_CACHE = '):
        delete_ranges.append((i, i, '_SIG_CACHE'))

# Sort by start line descending (delete from bottom up to preserve line numbers)
delete_ranges.sort(key=lambda x: x[0], reverse=True)

total_deleted = 0
for start, end, name in delete_ranges:
    # Replace with a comment marker
    comment = f"# ── {name}() moved to helper module ──\n"
    lines[start-1:end] = [comment]
    deleted = end - start + 1 - 1  # +1 comment line
    total_deleted += deleted
    print(f"  Deleted L{start}-L{end} ({end-start+1} lines): {name} -> 1 comment line")

with open('source/entry.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\nTotal lines deleted: {total_deleted}")
print(f"entry.py now: {len(lines)} lines")
