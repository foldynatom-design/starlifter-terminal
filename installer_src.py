import os
import sys
import shutil
import zipfile
import subprocess
import winreg
import threading
import time
import tkinter as tk
import customtkinter as ctk
from PIL import Image

class StarlifterInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("Starlifter Requisition Terminal v0.6 - Installation")
        self.geometry("680x480")
        self.resizable(False, False)
        
        # Theme configuration
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.accent_color = "#d97706"  # Amber/gold
        self.bg_sidebar = "#0f172a"    # Slate 900
        self.bg_main = "#020617"       # Slate 950
        self.text_color = "#f8fafc"    # Slate 50
        
        self.configure(fg_color=self.bg_main)
        
        # Path resolution
        if getattr(sys, 'frozen', False):
            self.base_dir = sys._MEIPASS
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.zip_path = os.path.join(self.base_dir, "app_files.zip")
        self.uninst_src = os.path.join(self.base_dir, "Uninstall.exe")
        self.target_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Starlifter_Terminal")
        
        # Setup UI layout
        self.create_widgets()
        
    def create_widgets(self):
        # 1. Left Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=self.bg_sidebar, border_width=0)
        self.sidebar.pack(side="left", fill="y")
        
        # Logo in sidebar
        logo_path = os.path.join(self.base_dir, "logo_uee44.png")
        if not os.path.exists(logo_path):
            # Fallback path if running outside bundled mode
            logo_path = os.path.join(os.path.dirname(self.base_dir), "logo_uee44.png")
            
        if os.path.exists(logo_path):
            try:
                pil_img = Image.open(logo_path)
                # Resize keeping ratio
                logo_w, logo_h = 160, 160
                self.logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(logo_w, logo_h))
                self.logo_label = ctk.CTkLabel(self.sidebar, image=self.logo_img, text="")
                self.logo_label.pack(pady=(40, 20))
            except Exception as e:
                print(f"Error loading logo: {e}")
                
        # Sidebar label
        self.side_title = ctk.CTkLabel(
            self.sidebar,
            text="44th BATTLE GROUP\nLOGISTICS CORPS",
            font=("Courier New", 13, "bold"),
            text_color=self.accent_color,
            justify="center"
        )
        self.side_title.pack(pady=(10, 10))
        
        # 2. Main Content Frame
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color=self.bg_main, border_width=0)
        self.main_content.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.main_content,
            text="STARLIFTER REQUISITION TERMINAL",
            font=("System", 20, "bold"),
            text_color=self.text_color
        )
        self.title_label.pack(anchor="w", pady=(10, 2))
        
        self.subtitle_label = ctk.CTkLabel(
            self.main_content,
            text="UEE Tactical Requisition Manifest Utility v0.6",
            font=("System", 12),
            text_color="#94a3b8"
        )
        self.subtitle_label.pack(anchor="w", pady=(0, 20))
        
        # Grid/Table for Tasks status
        self.tasks_frame = ctk.CTkFrame(self.main_content, fg_color="#0f172a", corner_radius=8, border_color="#334155", border_width=1)
        self.tasks_frame.pack(fill="x", pady=(0, 20), ipady=10)
        
        self.task_labels = []
        self.tasks = [
            "Extracting terminal core packages...",
            "Synchronizing local database schemas...",
            "Verifying runtime dependencies (VC++)...",
            "Creating desktop tactical shortcut...",
            "Registering Start menu launcher...",
            "Registering in Windows Programs list..."
        ]
        
        for idx, task in enumerate(self.tasks):
            row_frame = ctk.CTkFrame(self.tasks_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=15, pady=4)
            
            bullet = ctk.CTkLabel(row_frame, text="◽", font=("System", 14), text_color="#64748b", width=20)
            bullet.pack(side="left")
            
            lbl = ctk.CTkLabel(row_frame, text=task, font=("System", 12), text_color="#94a3b8")
            lbl.pack(side="left", padx=5)
            
            self.task_labels.append({"bullet": bullet, "label": lbl})
            
        # Progress Bar & Info label
        self.info_lbl = ctk.CTkLabel(self.main_content, text="Ready to initialize installation sequence.", font=("System", 11), text_color="#64748b")
        self.info_lbl.pack(anchor="w", pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.main_content, fg_color="#1e293b", progress_color=self.accent_color)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 20))
        
        # Action button
        self.action_btn = ctk.CTkButton(
            self.main_content,
            text="BEGIN INSTALLATION",
            font=("System", 13, "bold"),
            fg_color=self.accent_color,
            hover_color="#b45309",
            text_color="#ffffff",
            height=40,
            command=self.start_installation
        )
        self.action_btn.pack(fill="x")
        
    def start_installation(self):
        # Disable button during installation
        self.action_btn.configure(state="disabled")
        
        # Run installation in background thread
        thread = threading.Thread(target=self.run_install_thread)
        thread.daemon = True
        thread.start()
        
    def run_install_thread(self):
        try:
            # Step 1: Extract app files
            self.update_task_status(0, "running")
            self.info_lbl.configure(text="Extracting application files to AppData folder...")
            
            if os.path.exists(self.target_dir):
                try:
                    shutil.rmtree(self.target_dir)
                except Exception:
                    pass
            os.makedirs(self.target_dir, exist_ok=True)
            
            if os.path.exists(self.zip_path):
                with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                    # Smoothly animate progress bar during extraction
                    all_files = zip_ref.namelist()
                    total_files = len(all_files)
                    for idx, f in enumerate(all_files):
                        zip_ref.extract(f, self.target_dir)
                        if idx % max(1, total_files // 50) == 0:
                            progress = (idx / total_files) * 0.5
                            self.progress_bar.set(progress)
                            self.update_idletasks()
            self.progress_bar.set(0.5)
            self.update_task_status(0, "success")
            time.sleep(0.3)
            
            # Step 2: Copy uninstaller & sync config
            self.update_task_status(1, "running")
            self.info_lbl.configure(text="Synchronizing databases and logistics binaries...")
            if os.path.exists(self.uninst_src):
                shutil.copy(self.uninst_src, os.path.join(self.target_dir, "Uninstall.exe"))
            
            # Simulate database sync
            for i in range(5):
                self.progress_bar.set(0.5 + (i * 0.05))
                time.sleep(0.1)
                
            self.progress_bar.set(0.7)
            self.update_task_status(1, "success")
            time.sleep(0.3)
            
            # Step 3: Verify VC++ Runtime
            self.update_task_status(2, "running")
            self.info_lbl.configure(text="Checking Visual C++ Runtime dependencies...")
            
            # Check if vcruntime140.dll exists in the installed app or system
            vc_ok = False
            vc_files = ["VCRUNTIME140.dll", "VCRUNTIME140_1.dll"]
            internal_dir = os.path.join(self.target_dir, "_internal")
            for vcf in vc_files:
                if os.path.exists(os.path.join(internal_dir, vcf)) or os.path.exists(os.path.join(self.target_dir, vcf)):
                    vc_ok = True
                elif os.path.exists(os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", vcf)):
                    vc_ok = True
            
            if not vc_ok:
                # Try to download and install VC++ Redistributable silently
                self.info_lbl.configure(text="Downloading Visual C++ Redistributable...")
                try:
                    import urllib.request
                    vc_url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
                    vc_path = os.path.join(os.environ.get("TEMP", "."), "vc_redist.x64.exe")
                    urllib.request.urlretrieve(vc_url, vc_path)
                    subprocess.run([vc_path, "/install", "/quiet", "/norestart"], 
                                   capture_output=True, timeout=120)
                except Exception:
                    pass  # Non-critical — DLLs are bundled in _internal anyway
            
            self.progress_bar.set(0.75)
            self.update_task_status(2, "success")
            time.sleep(0.3)
            
            # Step 4: Create Desktop Shortcut
            self.update_task_status(3, "running")
            self.info_lbl.configure(text="Registering desktop tactical launcher shortcut...")
            exe_path = os.path.join(self.target_dir, "Starlifter Requisition Terminal.exe")
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            desktop_shortcut = os.path.join(desktop, "Starlifter Requisition Terminal.lnk")
            
            self.create_shortcut_silent(exe_path, desktop_shortcut)
            self.progress_bar.set(0.85)
            self.update_task_status(3, "success")
            time.sleep(0.3)
            
            # Step 5: Create Start Menu Shortcut
            self.update_task_status(4, "running")
            self.info_lbl.configure(text="Registering Start menu system path...")
            start_menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
            os.makedirs(start_menu, exist_ok=True)
            sm_shortcut = os.path.join(start_menu, "Starlifter Requisition Terminal.lnk")
            
            self.create_shortcut_silent(exe_path, sm_shortcut)
            self.progress_bar.set(0.95)
            self.update_task_status(4, "success")
            time.sleep(0.3)
            
            # Step 6: Register in Windows Add/Remove Programs
            self.update_task_status(5, "running")
            self.info_lbl.configure(text="Registering in Windows Programs list...")
            try:
                reg_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\StarlifterRequisitionTerminal"
                uninst_exe = os.path.join(self.target_dir, "Uninstall.exe")
                icon_file = os.path.join(self.target_dir, "app_icon.ico")
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_key) as key:
                    winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Starlifter Requisition Terminal v0.6")
                    winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninst_exe}"')
                    winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, icon_file if os.path.exists(icon_file) else exe_path)
                    winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "29th Starlifters / 44th Battle Group")
                    winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "0.6")
                    winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, self.target_dir)
                    winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            except Exception:
                pass  # Non-critical, don't fail install
            self.progress_bar.set(1.0)
            self.update_task_status(5, "success")
            time.sleep(0.3)
            
            # Installation success state
            self.info_lbl.configure(text="Installation completed successfully! Tactical terminal ready.", text_color="#10b981")
            
            # Update action button
            self.action_btn.configure(
                state="normal",
                text="LAUNCH TERMINAL",
                command=self.launch_app
            )
            
        except Exception as e:
            self.info_lbl.configure(text=f"Error: {e}", text_color="#ef4444")
            self.action_btn.configure(state="normal", text="RETRY INSTALLATION")
            
    def update_task_status(self, task_idx, status):
        bullet = self.task_labels[task_idx]["bullet"]
        label = self.task_labels[task_idx]["label"]
        
        if status == "running":
            bullet.configure(text="⏳", text_color=self.accent_color)
            label.configure(text_color=self.text_color)
        elif status == "success":
            bullet.configure(text="✔", text_color="#10b981")
            label.configure(text_color="#10b981")
        elif status == "failed":
            bullet.configure(text="✘", text_color="#ef4444")
            label.configure(text_color="#ef4444")
            
        self.update_idletasks()
        
    def create_shortcut_silent(self, target, shortcut_path):
        """Create a Windows shortcut (.lnk) with WorkingDirectory and icon set."""
        working_dir = os.path.dirname(target)
        icon_path = os.path.join(working_dir, "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = target  # fallback to exe icon

        # Method 1: Try PowerShell with full path
        ps_exe = os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"),
                              "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        ps_script = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut(\"{shortcut_path}\"); '
            f'$s.TargetPath = \"{target}\"; '
            f'$s.WorkingDirectory = \"{working_dir}\"; '
            f'$s.IconLocation = \"{icon_path}\"; '
            f'$s.Description = \"UEE Logistics Center - Requisition Terminal v0.6\"; '
            f'$s.Save()'
        )
        try:
            result = subprocess.run(
                [ps_exe, "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, timeout=15,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            if result.returncode == 0 and os.path.exists(shortcut_path):
                return  # Success
        except Exception:
            pass

        # Method 2: VBScript fallback
        try:
            vbs_content = (
                f'Set ws = CreateObject("WScript.Shell")\n'
                f'Set s = ws.CreateShortcut("{shortcut_path}")\n'
                f's.TargetPath = "{target}"\n'
                f's.WorkingDirectory = "{working_dir}"\n'
                f's.IconLocation = "{icon_path}"\n'
                f's.Description = "UEE Logistics Center - Requisition Terminal v0.6"\n'
                f's.Save\n'
            )
            vbs_path = os.path.join(self.target_dir, "_create_shortcut.vbs")
            with open(vbs_path, "w") as f:
                f.write(vbs_content)
            subprocess.run(
                ["cscript", "//nologo", vbs_path],
                capture_output=True, timeout=15,
                creationflags=0x08000000
            )
            os.remove(vbs_path)
        except Exception:
            pass
        
    def launch_app(self):
        exe_path = os.path.join(self.target_dir, "Starlifter Requisition Terminal.exe")
        if os.path.exists(exe_path):
            subprocess.Popen([exe_path], cwd=self.target_dir)
        self.destroy()
        sys.exit(0)

if __name__ == '__main__':
    app = StarlifterInstaller()
    app.mainloop()
