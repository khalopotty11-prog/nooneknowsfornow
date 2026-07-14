# main.py
import os
import sys
import urllib.request
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess

# --- CONFIGURATION ---
# IMPORTANT: Upload your ureedxd_client.py to GitHub and put the RAW link here!
CLIENT_DOWNLOAD_URL = "https://github.com/khalopotty11-prog/nooneknowsfornow.git"
ICON_FILENAME = "UREEDXD.ico"
# ---------------------

# Try to fix Windows scaling so it doesn't look blurry
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

class DarkSetupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UREEDXDCLIENT Setup")
        self.root.geometry("500x280")
        self.root.configure(bg="#121212")
        self.root.resizable(False, False)

        # Find the icon inside the PyInstaller temp folder
        try:
            self.icon_path = os.path.join(sys._MEIPASS, ICON_FILENAME)
        except Exception:
            self.icon_path = os.path.join(os.path.dirname(sys.executable), ICON_FILENAME)

        # --- DARK THEME UI ELEMENTS ---
        tk.Label(root, text="UREEDXDCLIENT", fg="#00d4ff", bg="#121212", font=("Segoe UI", 20, "bold")).pack(pady=(25, 5))
        tk.Label(root, text="Choose where to install the client:", fg="#aaaaaa", bg="#121212", font=("Segoe UI", 10)).pack()

        self.path_var = tk.StringVar(value=os.path.join("C:", "Games", "UREEDXDCLIENT"))
        
        # Custom Entry styling workaround
        entry_frame = tk.Frame(root, bg="#2d2d2d", highlightbackground="#444", highlightthickness=1)
        entry_frame.pack(pady=15, padx=30, fill="x", ipady=6)
        
        tk.Entry(entry_frame, textvariable=self.path_var, bg="#2d2d2d", fg="white", insertbackground="white", font=("Segoe UI", 10), bd=0, highlightthickness=0).pack(side="left", fill="x", expand=True, padx=10)
        
        # Custom Button styling
        browse_btn = tk.Button(entry_frame, text="Browse", command=self.browse, bg="#333333", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=15, activebackground="#555", activeforeground="white", cursor="hand2")
        browse_btn.pack(side="right", padx=10)

        install_btn = tk.Button(root, text="Install & Add Desktop Icon", command=self.install, bg="#00d4ff", fg="#000000", font=("Segoe UI", 12, "bold"), relief="flat", padx=20, pady=8, activebackground="#00a8cc", activeforeground="#000000", cursor="hand2")
        install_btn.pack(pady=15)

    def browse(self):
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)

    def install(self):
        install_dir = self.path_var.get().strip()
        if not install_dir:
            return

        try:
            # 1. Create Folders
            os.makedirs(os.path.join(install_dir, "instance", "mods"), exist_ok=True)
            
            # 2. Download Main Client
            client_path = os.path.join(install_dir, "ureedxd_client.py")
            urllib.request.urlretrieve(CLIENT_DOWNLOAD_URL, client_path)
            
            # 3. Create a silent launch .bat file
            bat_path = os.path.join(install_dir, "Play UREEDXDCLIENT.bat")
            with open(bat_path, "w") as f:
                f.write(f"@echo off\nstart \"\" pythonw \"{client_path}\"\nexit\n")
            
            # 4. Copy Icon to install folder
            dest_icon = os.path.join(install_dir, ICON_FILENAME)
            if os.path.exists(self.icon_path):
                with open(self.icon_path, 'rb') as f_in, open(dest_icon, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            # 5. Create Desktop Shortcut with Icon using a hidden VBS script
            # 5. Create Desktop Shortcut with Icon using a hidden VBS script
            self.create_shortcut(bat_path, dest_icon)
            
            messagebox.showinfo("UREEDXDCLIENT", "Installed successfully!\nCheck your Desktop for the icon.")
            sys.exit()

        except Exception as e:
            messagebox.showerror("Setup Error", f"Failed to install:\n{str(e)}")

    def create_shortcut(self, target_bat, target_icon):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        vbs_path = os.path.join(desktop, "create_shortcut.vbs")
        lnk_path = os.path.join(desktop, "UREEDXDCLIENT.lnk")
        
        # VBS script to create a proper Windows .lnk file with a custom icon
        vbs_code = f"""Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
Set oShellLink = WshShell.CreateShortcut("{lnk_path}")
oShellLink.TargetPath = "{target_bat}"
oShellLink.WorkingDirectory = "{os.path.dirname(target_bat)}"
oShellLink.IconLocation = "{target_icon}"
oShellLink.Save
"""
        with open(vbs_path, "w") as f:
            f.write(vbs_code)
        
        # Run the script silently, then delete it
        subprocess.run(['wscript.exe', vbs_path], shell=True)
        try:
            os.remove(vbs_path)
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = DarkSetupApp(root)
    root.mainloop()
