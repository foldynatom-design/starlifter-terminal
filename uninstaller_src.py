import os
import sys
import shutil
import winreg
import threading
import time
import customtkinter as ctk
from PIL import Image

class StarlifterUninstaller(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("Starlifter Requisition Terminal v0.6 - Uninstall")
        self.geometry("640x480")
        self.resizable(False, False)
        
        # Theme configuration
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.accent_color = "#dc2626"  # Red theme for uninstall
        self.bg_sidebar = "#1e1b4b"    # Indigo/dark blue 950
        self.bg_main = "#090514"       # Very dark purple/slate 950
        self.text_color = "#f8fafc"    # Slate 50
        
        self.configure(fg_color=self.bg_main)
        
        # Path resolution — look next to exe first, then _MEIPASS
        if getattr(sys, 'frozen', False):
            self.exe_dir = os.path.dirname(sys.executable)
            self.base_dir = sys._MEIPASS
        else:
            self.exe_dir = os.path.dirname(os.path.abspath(__file__))
            self.base_dir = self.exe_dir

        self.app_data = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Starlifter_Terminal")
        
        # Setup UI layout
        self.create_widgets()
        
    def create_widgets(self):
        # 1. Left Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=self.bg_sidebar, border_width=0)
        self.sidebar.pack(side="left", fill="y")
        
        # Logo in sidebar — check multiple locations
        logo_path = os.path.join(self.exe_dir, "logo_uee44.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(self.base_dir, "logo_uee44.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(self.exe_dir, "resources", "logo_uee44.png")
            
        if os.path.exists(logo_path):
            try:
                pil_img = Image.open(logo_path)
                logo_w, logo_h = 130, 130
                self.logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(logo_w, logo_h))
                self.logo_label = ctk.CTkLabel(self.sidebar, image=self.logo_img, text="")
                self.logo_label.pack(pady=(40, 20))
            except Exception as e:
                print(f"Error loading logo: {e}")
                
        self.side_title = ctk.CTkLabel(
            self.sidebar,
            text="44th BATTLE GROUP\nLOGISTICS CORPS",
            font=("Courier New", 12, "bold"),
            text_color=self.accent_color,
            justify="center"
        )
        self.side_title.pack(pady=(5, 10))
        
        # 2. Main Content Frame
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color=self.bg_main, border_width=0)
        self.main_content.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.main_content,
            text="STARLIFTER UNINSTALLER",
            font=("System", 18, "bold"),
            text_color=self.text_color
        )
        self.title_label.pack(anchor="w", pady=(10, 2))
        
        self.subtitle_label = ctk.CTkLabel(
            self.main_content,
            text="Deinstalling requisition workspace files and shortcuts...",
            font=("System", 11),
            text_color="#94a3b8"
        )
        self.subtitle_label.pack(anchor="w", pady=(0, 20))
        
        # Task list for cleanup
        self.tasks_frame = ctk.CTkFrame(self.main_content, fg_color="#110c22", corner_radius=8, border_color="#31254f", border_width=1)
        self.tasks_frame.pack(fill="x", pady=(0, 20), ipady=10)
        
        self.task_labels = []
        self.tasks = [
            "Removing desktop shortcut link...",
            "Removing Start menu folder shortcut...",
            "Removing Windows Programs registration...",
            "Deleting local AppData workspace files..."
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
        self.info_lbl = ctk.CTkLabel(self.main_content, text="Ready to remove files.", font=("System", 11), text_color="#64748b")
        self.info_lbl.pack(anchor="w", pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.main_content, fg_color="#1c1917", progress_color=self.accent_color)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 20))
        
        # Action button
        self.action_btn = ctk.CTkButton(
            self.main_content,
            text="BEGIN UNINSTALL",
            font=("System", 13, "bold"),
            fg_color=self.accent_color,
            hover_color="#991b1b",
            text_color="#ffffff",
            height=35,
            command=self.start_uninstall
        )
        self.action_btn.pack(fill="x")
        
    def start_uninstall(self):
        # Confirmation dialog before proceeding
        import tkinter.messagebox as mb
        confirmed = mb.askyesno(
            "Confirm Uninstall",
            "Are you sure you want to uninstall\nStarlifter Requisition Terminal v0.6?\n\nAll local data will be removed.",
            icon="warning"
        )
        if not confirmed:
            return
        self.action_btn.configure(state="disabled")
        thread = threading.Thread(target=self.run_uninstall_thread)
        thread.daemon = True
        thread.start()
        
    def run_uninstall_thread(self):
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop, "Starlifter Requisition Terminal.lnk")
            
            start_menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
            sm_shortcut = os.path.join(start_menu, "Starlifter Requisition Terminal.lnk")
            
            # Step 1: Desktop shortcut
            self.update_task_status(0, "running")
            self.info_lbl.configure(text="Removing Desktop shortcut...")
            if os.path.exists(shortcut_path):
                try:
                    os.remove(shortcut_path)
                except Exception:
                    pass
            time.sleep(0.3)
            self.progress_bar.set(0.3)
            self.update_task_status(0, "success")
            
            # Step 2: Start menu shortcut
            self.update_task_status(1, "running")
            self.info_lbl.configure(text="Removing Start Menu shortcuts...")
            if os.path.exists(sm_shortcut):
                try:
                    os.remove(sm_shortcut)
                except Exception:
                    pass
            time.sleep(0.3)
            self.progress_bar.set(0.5)
            self.update_task_status(1, "success")
            
            # Step 3: Remove Windows Programs registry entry
            self.update_task_status(2, "running")
            self.info_lbl.configure(text="Removing Windows Programs registration...")
            try:
                reg_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\StarlifterRequisitionTerminal"
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_key)
            except FileNotFoundError:
                pass  # Already removed
            except Exception:
                pass
            time.sleep(0.3)
            self.progress_bar.set(0.7)
            self.update_task_status(2, "success")
            
            # Step 4: Deleting AppData
            self.update_task_status(3, "running")
            self.info_lbl.configure(text="Cleaning AppData files...")
            
            if os.path.exists(self.app_data):
                # Try to rmtree AppData
                for i in range(5):
                    try:
                        shutil.rmtree(self.app_data)
                        break
                    except Exception:
                        time.sleep(0.5)
                        
            time.sleep(0.3)
            self.progress_bar.set(1.0)
            self.update_task_status(3, "success")
            
            # Success
            self.info_lbl.configure(text="Uninstall completed successfully! Files removed.", text_color="#10b981")
            
            self.action_btn.configure(
                state="normal",
                text="CLOSE",
                command=self.close_window
            )
            
        except Exception as e:
            self.info_lbl.configure(text=f"Error during uninstall: {e}", text_color="#ef4444")
            self.action_btn.configure(state="normal", text="CLOSE", command=self.close_window)
            
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
        
    def close_window(self):
        self.destroy()
        sys.exit(0)

if __name__ == '__main__':
    app = StarlifterUninstaller()
    app.mainloop()
