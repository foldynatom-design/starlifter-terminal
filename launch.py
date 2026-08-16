import os
import sys

# Ensure correct base path
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

from src.core.app import StarlifterApp

if __name__ == '__main__':
    app = StarlifterApp()
    app.mainloop()
