# ureedxd_client.py
import sys, os, json, hashlib, uuid as _uuid, shutil, requests, subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QFileDialog, 
    QLineEdit, QProgressBar, QListWidget, QCheckBox, QInputDialog, 
    QMessageBox, QFrame, QSlider, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QColor

import minecraft_launcher_lib

CLIENT_ROOT = os.path.dirname(os.path.abspath(__file__))
INSTANCE_JSON = os.path.join(CLIENT_ROOT, "instance.json")
PROFILES_JSON = os.path.join(CLIENT_ROOT, "instance", "profiles.json")

if os.path.exists(INSTANCE_JSON):
    MC_DIR = json.load(open(INSTANCE_JSON, encoding="utf-8")).get("instance_dir", minecraft_launcher_lib.utils.get_minecraft_directory())
else:
    MC_DIR = minecraft_launcher_lib.utils.get_minecraft_directory()

MODRINTH_V2 = "https://api.modrinth.com/v2"
UA = {"User-Agent": "UREEDXDCLIENT/1.0"}
CURRENT_VERSION = "1.0.0"
UPDATE_URL = "https://raw.githubusercontent.com/khalopotty11-prog/nooneknowsfornow/main/version.txt" # You'll create this file later

# --- STYLES ---
SPLASH_STYLE = """
QWidget { background-color: #000000; }
QLabel#logo { color: #0078d4; font-size: 48px; font-weight: bold; }
QLabel#status { color: #ffffff; font-size: 14px; }
QLabel#substatus { color: #666666; font-size: 12px; }
"""

MAIN_STYLE = """
* { font-family: 'Segoe UI', sans-serif; margin: 0px; padding: 0px; }
QMainWindow { background-color: #0e0e0e; }
QWidget#sidebar { background-color: #161616; border-right: 1px solid #2a2a2a; }
QWidget#content { background-color: #0e0e0e; }
QPushButton#navBtn { color: #888; background-color: transparent; border: none; text-align: left; padding: 12px 20px; font-size: 14px; border-radius: 6px; margin: 2px 10px; }
QPushButton#navBtn:hover { background-color: #1e1e1e; color: #fff; }
QPushButton#navBtn:checked { background-color: #0078d4; color: #fff; font-weight: bold; }
QLabel#header { color: #fff; font-size: 24px; font-weight: bold; padding: 20px; background: transparent; }
QLineEdit, QComboBox { background-color: #1a1a1a; border: 1px solid #333; border-radius: 6px; padding: 10px; color: #fff; font-size: 14px; }
QPushButton#actionBtn { background-color: #0078d4; color: white; border: none; border-radius: 6px; padding: 12px; font-weight: bold; font-size: 14px; }
QPushButton#actionBtn:hover { background-color: #1a86d8; }
QPushButton#dangerBtn { background-color: #d13438; color: white; border: none; border-radius: 6px; padding: 10px; font-weight: bold; }
QPushButton#secondaryBtn { background-color: transparent; color: #0078d4; border: 1px solid #0078d4; border-radius: 6px; padding: 10px; font-weight: bold; }
QListWidget { background-color: #1a1a1a; border: 1px solid #333; border-radius: 6px; color: #fff; padding: 10px; font-size: 14px; outline: none; }
QListWidget::item { padding: 10px; border-radius: 4px; }
QListWidget::item:selected { background-color: #0078d4; }
QTextEdit { background-color: #0a0a0a; color: #00ff00; border: 1px solid #2a2a2a; border-radius: 6px; font-family: 'Consolas'; font-size: 12px; padding: 10px; }
QProgressBar { border: none; border-radius: 6px; text-align: center; color: #fff; background-color: #1a1a1a; max-height: 6px; font-size: 0px; }
QProgressBar::chunk { background-color: #0078d4; border-radius: 6px; }
QSlider::groove:horizontal { background: #333; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #0078d4; width: 16px; margin: -5px 0; border-radius: 8px; }
QGroupBox { color: #ccc; border: 1px solid #333; border-radius: 6px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QPushButton#playBtn { background-color: #107c10; color: white; border: none; border-radius: 12px; padding: 30px; font-size: 32px; font-weight: bold; }
QPushButton#playBtn:hover { background-color: #1a9a1a; }
"""

def offline_uuid(name: str) -> str:
    return str(_uuid.UUID(bytes=hashlib.md5(f"OfflinePlayer:{name}".encode("utf-8")).digest()[:16], version=3))

class Worker(QThread):
    log = Signal(str); progress = Signal(int); done_ok = Signal(bool)
    def __init__(self, fn): super().__init__(); self.fn = fn
    def run(self):
        try: self.fn(self.log, self.progress); self.done_ok.emit(True)
        except Exception as e: self.log.emit(f"ERROR: {e}"); self.done_ok.emit(False)

# --- BOOT SCREEN ---
class BootScreen(QWidget):
    finished = Signal()
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(SPLASH_STYLE)
        self.setFixedSize(400, 250)
        
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        
        self.logo = QLabel("UREEDXD")
        self.logo.setObjectName("logo")
        self.logo.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.logo)
        
        self.status = QLabel("Checking for updates...")
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.status)
        
        self.sub = QLabel("Please wait...")
        self.sub.setObjectName("substatus")
        self.sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.sub)
        
        # Simple animation timer
        self.dots = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(500)
        
        # Start actual update check
        QTimer.singleShot(1000, self.do_check)

    def animate(self):
        self.dots = (self.dots + 1) % 4
        self.sub.setText("Please wait" + "." * self.dots)

    def do_check(self):
        self.status.setText("Checking for updates...")
        try:
            r = requests.get(UPDATE_URL, timeout=3)
            if r.status_code == 200 and r.text.strip() != CURRENT_VERSION:
                self.status.setText("Update found! Downloading...")
                # PUT AUTO-UPDATE LOGIC HERE LATER
                # For now, we just finish
        except:
            pass # No internet or file missing, skip update
            
        self.status.setText("Launching Client...")
        self.timer.stop()
        QTimer.singleShot(500, self.finished.emit)

# --- MAIN CLIENT ---
class UreedxdClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UREEDXDCLIENT")
        self.resize(1000, 700)
        self.setStyleSheet(MAIN_STYLE)
        
        self.accounts = self._load_json("accounts.json", [])
        self.profiles = self._load_profiles()
        self.active_user = self.accounts[0] if self.accounts else None
        self._skin_path = None
        self.pages = {}

        self._ui()
        self._refresh_versions()
        self._refresh_profiles_list()

    def _load_json(self, filename, default):
        path = os.path.join(CLIENT_ROOT, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        return default

    def _save_json(self, filename, data):
        with open(os.path.join(CLIENT_ROOT, filename), "w", encoding="utf-8") as f: json.dump(data, f, indent=2)

    def _load_profiles(self):
        if os.path.exists(PROFILES_JSON):
            with open(PROFILES_JSON, "r") as f: return json.load(f)
        # Default profile
        return [{"name": "Latest Release", "version": "1.21", "loader": "fabric", "ram": 4096, "active": True}]

    def _ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        
        lbl_title = QLabel("UREEDXD"); lbl_title.setObjectName("header"); lbl_title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(lbl_title)
        sidebar_layout.addSpacing(20)

        self.nav_buttons = []
        for item in ["Home", "Profiles", "Accounts", "Settings"]:
            btn = QPushButton(f"  {item}"); btn.setObjectName("navBtn"); btn.setCheckable(True); btn.setCursor(Qt.PointingHandCursor)
            if item == "Home": btn.setChecked(True)
            btn.clicked.connect(lambda checked, i=item: self.switch_page(i))
            sidebar_layout.addWidget(btn); self.nav_buttons.append(btn)
        sidebar_layout.addStretch()

        # Content
        self.content = QWidget(); self.content.setObjectName("content")
        self.content_layout = QVBoxLayout(self.content); self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.stack = QWidget(); self.stack_layout = QVBoxLayout(self.stack); self.stack_layout.setContentsMargins(0,0,0,0)
        
        self._build_home(); self._build_profiles(); self._build_accounts(); self._build_settings()
        self.stack_layout.addWidget(self.pages["Home"])
        self.content_layout.addWidget(self.stack)

        self.console = QTextEdit(); self.console.setFixedHeight(120); self.content_layout.addWidget(self.console)
        self.prog = QProgressBar(); self.prog.setValue(0); self.content_layout.addWidget(self.prog)

        main_layout.addWidget(sidebar); main_layout.addWidget(self.content, 1)

    def switch_page(self, name):
        for btn in self.nav_buttons: btn.setChecked(False)
        for btn in self.nav_buttons:
            if name in btn.text(): btn.setChecked(True); break
        old = self.stack_layout.takeAt(0)
        if old and old.widget(): old.widget().hide()
        self.stack_layout.addWidget(self.pages[name]); self.pages[name].show()

    def _build_home(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setAlignment(Qt.AlignCenter)
        act_profile = next((p for p in self.profiles if p["active"]), self.profiles[0])
        
        info = QLabel(f"Profile: {act_profile['name']}\nVersion: {act_profile['version']} | Loader: {act_profile['loader'].capitalize()}\nRAM: {act_profile['ram']//1024}GB")
        info.setAlignment(Qt.AlignCenter); info.setStyleSheet("font-size: 16px; color: #aaa; margin-bottom: 30px;"); lay.addWidget(info)
        
        btn = QPushButton("PLAY"); btn.setObjectName("playBtn"); btn.setFixedSize(200, 100); btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._play); lay.addWidget(btn)
        self.pages["Home"] = page

    def _build_profiles(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("Game Profiles", objectName="header"))
        
        self.profile_list = QListWidget(); lay.addWidget(self.profile_list)
        
        btn_lay = QHBoxLayout()
        b_new = QPushButton("New Profile"); b_new.setObjectName("secondaryBtn"); b_new.clicked.connect(self._new_profile); btn_lay.addWidget(b_new)
        b_del = QPushButton("Delete"); b_del.setObjectName("secondaryBtn"); b_del.clicked.connect(self._del_profile); btn_lay.addWidget(b_del)
        lay.addLayout(btn_lay)
        
        # RAM Slider
        grp = QGroupBox("Selected Profile RAM"); grp_lay = QHBoxLayout(grp)
        self.ram_slider = QSlider(Qt.Orientation.Horizontal); self.ram_slider.setRange(1024, 16384); self.ram_slider.setValue(4096); self.ram_slider.setSingleStep(512)
        self.ram_label = QLabel("4.0 GB"); self.ram_label.setFixedWidth(60)
        self.ram_slider.valueChanged.connect(lambda v: (self.ram_label.setText(f"{v/1024:.1f} GB"), self._update_ram(v)))
        self.profile_list.currentRowChanged.connect(lambda i: self.ram_slider.setValue(self.profiles[i]["ram"]) if i >= 0 else None)
        grp_lay.addWidget(self.ram_slider); grp_lay.addWidget(self.ram_label); lay.addWidget(grp)
        self.pages["Profiles"] = page

    def _build_accounts(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("Accounts", objectName="header"))
        
        self.acc_list = QListWidget(); lay.addWidget(self.acc_list)
        self._refresh_accounts()
        
        btn_lay = QHBoxLayout()
        b_add = QPushButton("Add Offline"); b_add.setObjectName("secondaryBtn"); b_add.clicked.connect(self._add_account); btn_lay.addWidget(b_add)
        b_skin = QPushButton("Skins & Capes"); b_skin.setObjectName("secondaryBtn"); b_skin.clicked.connect(self._pick_skin); btn_lay.addWidget(b_skin)
        lay.addLayout(btn_lay)
        self.pages["Accounts"] = page

    def _build_settings(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("Settings", objectName="header"))
        
        # Directories
        grp_dir = QGroupBox("Directories"); dir_lay = QVBoxLayout(grp_dir)
        dir_lay.addWidget(QLabel(f"Install Dir: {CLIENT_ROOT}"))
        b_open = QPushButton("Open Folder"); b_open.setObjectName("secondaryBtn"); b_open.clicked.connect(lambda: os.startfile(CLIENT_ROOT)); dir_lay.addWidget(b_open)
        lay.addWidget(grp_dir)
        
        # Clear Data
        grp_clear = QGroupBox("Clear Data"); clear_lay = QVBoxLayout(grp_clear)
        clear_lay.addWidget(QLabel("Reset launcher to default state. Deletes profiles and accounts."))
        b_clear = QPushButton("Clear All Data"); b_clear.setObjectName("dangerBtn"); b_clear.clicked.connect(self._clear_data); clear_lay.addWidget(b_clear)
        lay.addWidget(grp_clear)
        
        lay.addStretch()
        self.pages["Settings"] = page

    # --- LOGIC ---
    def _refresh_accounts(self):
        self.acc_list.clear()
        for a in self.accounts: self.acc_list.addItem(f"{a['username']} (OFFLINE)")
        if self.accounts and not self.acc_list.currentItem(): self.acc_list.setCurrentRow(0)

    def _add_account(self):
        name, ok = QInputDialog.getText(self, "Add Offline Account", "Username:")
        if not ok or not name.strip(): return
        name = name.strip(); uid = offline_uuid(name)
        self.accounts.append({"username": name, "uuid": uid, "type": "offline"})
        self._save_json("accounts.json", self.accounts); self._refresh_accounts()

    def _pick_skin(self):
        p, _ = QFileDialog.getOpenFileName(self, "Skin PNG", "", "PNG (*.png)")
        if p:
            self._skin_path = p
            self._run_worker(lambda log, prog: self._apply_skin(log, prog))

    def _apply_skin(self, log, prog):
        rp_dir = os.path.join(MC_DIR, "resourcepacks", "UREEDXD_Skin")
        shutil.rmtree(rp_dir, ignore_errors=True); os.makedirs(rp_dir, exist_ok=True); prog(50)
        with open(os.path.join(rp_dir, "pack.mcmeta"), "w") as f: json.dump({"pack": {"pack_format": 34, "description": "UREEDXD Skin"}}, f)
        tex_dir = os.path.join(rp_dir, "assets", "minecraft", "textures", "entity", "player", "wide")
        os.makedirs(tex_dir, exist_ok=True); shutil.copy2(self._skin_path, os.path.join(tex_dir, "steve.png")); prog(100)

    def _refresh_profiles_list(self):
        self.profile_list.clear()
        for p in self.profiles:
            status = " [ACTIVE]" if p["active"] else ""
            self.profile_list.addItem(f"{p['name']} ({p['version']} {p['loader']}){status}")
        active_idx = next((i for i, p in enumerate(self.profiles) if p["active"]), 0)
        self.profile_list.setCurrentRow(active_idx)

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Profile Name:")
        if not ok: return
        self.profiles.append({"name": name, "version": "1.21", "loader": "fabric", "ram": 4096, "active": False})
        self._save_profiles(); self._refresh_profiles_list()

    def _del_profile(self):
        idx = self.profile_list.currentRow()
        if idx < 0: return
        del self.profiles[idx]
        if not any(p["active"] for p in self.profiles) and self.profiles: self.profiles[0]["active"] = True
        self._save_profiles(); self._refresh_profiles_list()

    def _update_ram(self, val):
        idx = self.profile_list.currentRow()
        if idx >= 0: self.profiles[idx]["ram"] = val; self._save_profiles()

    def _save_profiles(self):
        os.makedirs(os.path.dirname(PROFILES_JSON), exist_ok=True)
        with open(PROFILES_JSON, "w") as f: json.dump(self.profiles, f, indent=2)

    def _clear_data(self):
        if QMessageBox.question(self, "Clear Data", "Are you sure? This deletes everything!") == QMessageBox.StandardButton.Yes:
            for f in ["accounts.json"]: 
                path = os.path.join(CLIENT_ROOT, f)
                if os.path.exists(path): os.remove(path)
            if os.path.exists(PROFILES_JSON): os.remove(PROFILES_JSON)
            QMessageBox.information(self, "Done", "Cleared. Please restart the client.")

    def _play(self):
        if not self.accounts: QMessageBox.warning(self, "Error", "Add an account first!"); return
        acc = self.accounts[self.acc_list.currentRow() if self.acc_list.currentRow() >= 0 else 0]
        act_profile = next((p for p in self.profiles if p["active"]), self.profiles[0])
        
        mc_ver = act_profile["version"]; loader = act_profile["loader"]; ram = act_profile["ram"]
        profile = mc_ver
        
        self.console.append(f"Installing {mc_ver} {loader}...")
        if loader != "vanilla":
            try:
                ml = minecraft_launcher_lib.mod_loader.get_mod_loader(loader)
                profile = ml.install(mc_ver, MC_DIR, callback={"setStatus": lambda s: self.statusBar().showMessage(s)})
            except Exception as e: self.console.append(f"[ERROR] {e}"); return
        try: minecraft_launcher_lib.install.install_minecraft_version(mc_ver, MC_DIR)
        except: pass
        
        self._pre_optimize(mc_ver)
        opts = {
            "username": acc["username"], "uuid": acc["uuid"], "token": "0", 
            "launcherName": "UREEDXDCLIENT", "gameDirectory": MC_DIR,
            "jvmArguments": ["-XX:+UseG1GC", "-Xmx"+str(ram)+"M", "-Xms512M"]
        }
        cmd = minecraft_launcher_lib.command.get_minecraft_command(profile, MC_DIR, opts)
        self.console.append("Launching..."); subprocess.Popen(cmd, cwd=MC_DIR)

    def _pre_optimize(self, mc_ver):
        opt_path = os.path.join(MC_DIR, "options.txt")
        overrides = {"renderDistance":"4","simulationDistance":"3","particles":"0","maxFps":"120","graphicsMode":"1","ao":"0","entityShadows":"false","enableVsync":"false"}
        data = {}
        if os.path.exists(opt_path):
            with open(opt_path, "r") as f:
                for line in f:
                    if ":" in line: k,v=line.strip().split(":",1); data[k]=v
        data.update(overrides)
        with open(opt_path, "w") as f:
            for k,v in data.items(): f.write(f"{k}:{v}\n")

    def _refresh_versions(self):
        # Just keeping this in background in case needed for profile creation later
        pass

    def _run_worker(self, fn):
        self._w = Worker(fn); self._w.log.connect(self.console.append); self._w.progress.connect(self.prog.setValue); self._w.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Show Boot Screen First
    boot = BootScreen()
    boot.show()
    
    main_win = UreedxdClient()
    
    def close_boot_and_show():
        boot.close()
        main_win.show()
        
    boot.finished.connect(close_boot_and_show)
    
    sys.exit(app.exec())
