import sys, os
sys.path.insert(0, 'source')
from path_config import PATHS

print("=== Tvoje data (toto se NEMAŽE) ===")
print(f"  Zdrojový kód:  {PATHS.app_root}")
print(f"  Resources:     {PATHS.resources}")
print(f"  Config:        {PATHS.config}")
print(f"  Config exists: {os.path.exists(PATHS.config)}")
print(f"  Temp/cache:    {PATHS.temp_dir}")

print()
print("=== Hledám nainstalovanou verzi ===")
check_paths = [
    r'C:\Program Files\Starlifter',
    r'C:\Program Files (x86)\Starlifter',
    os.path.expanduser(r'~\Desktop\Starlifter_Terminal'),
    r'C:\Users\tomfo\AppData\Local\Starlifter_Terminal\dist',
    r'C:\Users\tomfo\AppData\Local\Programs\Starlifter',
]
for p in check_paths:
    exists = os.path.exists(p)
    if exists:
        files = os.listdir(p)[:10]
        print(f"  [FOUND] {p}")
        print(f"          files: {files}")
    else:
        print(f"  [  -  ] {p}")

# Check for EXE in common places
print()
print("=== Hledám .exe soubory ===")
for root_dir in [PATHS.app_root, r'C:\Users\tomfo\Desktop']:
    if os.path.isdir(root_dir):
        for f in os.listdir(root_dir):
            if f.endswith('.exe') and 'starlifter' in f.lower():
                print(f"  [EXE] {os.path.join(root_dir, f)}")

# Check Add/Remove Programs registry
print()
print("=== Kontrola registru (Add/Remove Programs) ===")
import winreg
for hive_name, hive in [("HKCU", winreg.HKEY_CURRENT_USER), ("HKLM", winreg.HKEY_LOCAL_MACHINE)]:
    try:
        key = winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        i = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)
                try:
                    name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                    if 'starlifter' in name.lower() or 'requisition' in name.lower():
                        install_loc = ""
                        try:
                            install_loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                        except Exception:
                            pass
                        uninstall = ""
                        try:
                            uninstall = winreg.QueryValueEx(subkey, "UninstallString")[0]
                        except Exception:
                            pass
                        print(f"  [{hive_name}] {name}")
                        print(f"         Install: {install_loc}")
                        print(f"         Uninstall: {uninstall}")
                except Exception:
                    pass
                subkey.Close()
                i += 1
            except OSError:
                break
        key.Close()
    except Exception:
        pass
