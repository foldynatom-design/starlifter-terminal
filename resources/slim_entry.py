# Build slimmed-down entry.py
# Keep L1-120 (header + imports + bootstrap), add ui_panel import + __main__

with open('source/entry.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Keep header block (lines 1-120, 0-indexed: 0-119)
header = lines[:120]

# Build new entry.py
tail = '''
# ── UI Panel: all UI patches + interactions ──
from ui_panel import apply_all_patches
apply_all_patches(main)


# ══════════════════════════════════════════════════════════════════════════
# SECTION: Entry Point
# ══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    try:
        import customtkinter
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("dark-blue")
        app = main.RequisitionApp()
        app.mainloop()
    except Exception as e:
        import traceback
        import tkinter as tk
        from tkinter import messagebox
        
        crash_log = os.path.join(PATHS.app_root, 'crash_log.txt')
        
        try:
            with open(crash_log, 'w', encoding='utf-8') as f:
                f.write("A critical error occurred while starting the application:\\n\\n")
                traceback.print_exc(file=f)
                f.write("\\n\\nPlease send this crash_log.txt to the developer.")
        except Exception:
            pass
            
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error",
                f"Application crashed on startup.\\nSee {crash_log} for details.\\n\\nError: {str(e)}")
            root.destroy()
        except Exception:
            pass
'''

with open('source/entry.py', 'w', encoding='utf-8') as f:
    f.writelines(header)
    f.write(tail)

new_count = sum(1 for _ in open('source/entry.py', 'r', encoding='utf-8'))
print(f"entry.py trimmed: {len(lines)} -> {new_count} lines (-{len(lines)-new_count})")
