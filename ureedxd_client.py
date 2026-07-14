# ureedxd_client.py
import sys, os, json, hashlib, uuid as _uuid, shutil, requests, subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QFileDialog, 
    QLineEdit, QProgressBar, QListWidget, QCheckBox, QInputDialog, 
    QMessageBox, QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QSize
from PySide6.QtGui import QFont, QIcon, QColor

import minecraft_launcher_lib

CLIENT_ROOT = os.path.dirname(os.path.abspath(__file__))
INSTANCE_JSON = os.path.join(CLIENT_ROOT, "instance.json")
if os.path.exists(INSTANCE_JSON):
    MC_DIR = json.load(open(INSTANCE_JSON, encoding="utf-8")).get("instance_dir", minecraft_launcher_lib.utils.get_minecraft_directory())
else:
    MC_DIR = minecraft_launcher_lib.utils.get_minecraft_directory()

MODRINTH_V2 = "https://api.modrinth.com/v2"
UA = {"User-Agent": "UREEDXDCLIENT/1.0"}

# --- FLUENT/MODERN DARK THEME (FASTCLIENT STYLE) ---
STYLE = """
* { font-family: 'Segoe UI', sans-serif; margin: 0px; padding: 0px; }
QMainWindow { background-color: #0e0e0e; }
QWidget#sidebar { background-color: #161616; border-right: 1px solid #2a2a2a; }
QWidget#content { background-color: #0e0e0e; }
QPushButton#navBtn { 
    color: #888; background-color: transparent; border: none; text-align: left; 
    padding: 15px 20px; font-size: 14px; border-radius: 8px; margin: 2px 10px;
}
QPushButton#navBtn:hover { background-color: #1e1e1e; color: #fff; }
QPushButton#navBtn:checked { background-color: #0078d4; color: #fff; font-weight: bold; }
QLabel#title { color: #fff; font-size: 24px; font-weight: bold; padding: 20px; background: transparent; }
QLabel#subtitle { color: #666; font-size: 12px; background: transparent; }
QLabel#header { color: #fff; font-size: 18px; font-weight: bold; padding: 20px; background: transparent;}
QLineEdit { 
    background-color: #1a1a1a; border: 1px solid #333; border-radius: 6px; 
    padding: 12px; color: #fff; font-size: 14px;
}
QLineEdit:focus { border: 1px solid #0078d4; }
QComboBox { 
    background-color: #1a1a1a; border: 1px solid #333; border-radius: 6px; 
    padding: 12px; color: #fff; font-size: 14px;
}
QComboBox::drop-down { border: none; width: 30px; }
QComboBox QAbstractItemView { background-color: #1a1a1a; color: #fff; selection-background-color: #0078d4; border: 1px solid #333; }
QPushButton#actionBtn { 
    background-color: #0078d4; color: white; border: none; border-radius: 6px; 
    padding: 12px; font-weight: bold; font-size: 14px;
}
QPushButton#actionBtn:hover { background-color: #1a86d8; }
QPushButton#actionBtn:disabled { background-color: #333; color: #666; }
QPushButton#secondaryBtn { 
    background-color: transparent; color: #0078d4; border: 1px solid #0078d4; 
    border-radius: 6px; padding: 10px; font-weight: bold;
}
QPushButton#secondaryBtn:hover { background-color: #0078d4; color: white; }
QListWidget { 
    background-color: #1a1a1a; border: 1px solid #333; border-radius: 6px; 
    color: #fff; padding: 10px; font-size: 14px; outline: none;
}
QListWidget::item { padding: 10px; border-radius: 4px; }
QListWidget::item:selected { background-color: #0078d4; }
QTextEdit { 
    background-color: #0a0a0a; color: #00ff00; border: 1px solid #2a2a2a; 
    border-radius: 6px; font-family: 'Consolas', monospace; font-size: 12px; padding: 10px;
}
QProgressBar { 
    border: none; border-radius: 6px; text-align: center; color: #fff; 
    background-color: #1a1a1a; max-height: 6px; font-size: 0px;
}
QProgressBar::chunk { background-color: #0078d4; border-radius: 6px; }
QCheckBox { color: #ccc; spacing: 10px; font-size: 14px; background: transparent; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #444; background: #1a1a1a; }
QCheckBox::indicator:checked { background-color: #0078d4; border-color: #0078d4; }
"""

def offline_uuid(name: str) -> str:
    return str(_uuid.UUID(bytes=hashlib.md5(f"OfflinePlayer:{name}".encode("utf-8")).digest()[:16], version=3))

class Worker(QThread):
    log = Signal(str); progress = Signal(int); done_ok = Signal(bool)
    def __init__(self, fn): super().__init__(); self.fn = fn
    def run(self):
        try: self.fn(self.log, self.progress); self.done_ok.emit(True)
        except Exception as e: self.log.emit(f"ERROR: {e}"); self.done_ok.emit(False)

class UreedxdClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UREEDXDCLIENT")
        self.resize(1000, 700)
        self.setStyleSheet(STYLE)
        
        self.accounts = self._load_accounts()
        self.active_user = None
        self._skin_path = None
        self.pages = {}

        self._ui()
        self._refresh_versions()

    ACC_FILE = os.path.join(CLIENT_ROOT, "accounts.json")
    def _load_accounts(self):
        if os.path.exists(self.ACC_FILE):
            with open(self.ACC_FILE, "r", encoding="utf-8") as f: return json.load(f)
        return []
    def _save_accounts(self):
        with open(self.ACC_FILE, "w", encoding="utf-8") as f: json.dump(self.accounts, f, indent=2)

    def _ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        
        lbl_title = QLabel("UREEDXD")
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(lbl_title)
        
        lbl_sub = QLabel("Optimized Client")
        lbl_sub.setObjectName("subtitle")
        lbl_sub.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(lbl_sub)
        sidebar_layout.addSpacing(20)

        self.nav_buttons = []
        nav_items = ["Home", "Versions", "Skin", "Mods"]
        for item in nav_items:
            btn = QPushButton(f"  {item}")
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            if item == "Home": btn.setChecked(True)
            btn.clicked.connect(lambda checked, i=item: self.switch_page(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            
        sidebar_layout.addStretch()

        # Content Area
        self.content = QWidget()
        self.content.setObjectName("content")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)

        self.stack = QWidget()
        self.stack_layout = QVBoxLayout(self.stack)
        self.stack_layout.setContentsMargins(0,0,0,0)
        
        self._build_home_page()
        self._build_versions_page()
        self._build_skin_page()
        self._build_mods_page()
        
        self.stack_layout.addWidget(self.pages["Home"])
        self.content_layout.addWidget(self.stack)

        # Console at bottom
        self.console = QTextEdit()
        self.console.setFixedHeight(150)
        self.content_layout.addWidget(self.console)
        
        self.prog = QProgressBar()
        self.prog.setValue(0)
        self.content_layout.addWidget(self.prog)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content, 1)

    def switch_page(self, name):
        for btn in self.nav_buttons: btn.setChecked(False)
        for btn in self.nav_buttons:
            if name in btn.text(): btn.setChecked(True); break
            
        old = self.stack_layout.takeAt(0)
        if old and old.widget(): old.widget().hide()
        self.stack_layout.addWidget(self.pages[name])
        self.pages[name].show()

    # --- PAGES ---
    def _build_home_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("Offline Accounts"))
        lay.addSpacing(10)
        
        self.acc_list = QListWidget(); lay.addWidget(self.acc_list)
        self._refresh_accounts()

        btn_lay = QHBoxLayout()
        b_add = QPushButton("Add Account"); b_add.setObjectName("secondaryBtn"); b_add.clicked.connect(self._add_account); btn_lay.addWidget(b_add)
        b_del = QPushButton("Remove"); b_del.setObjectName("secondaryBtn"); b_del.clicked.connect(self._del_account); btn_lay.addWidget(b_del)
        lay.addLayout(btn_lay)

        self.lbl_active = QLabel("No account selected.")
        self.lbl_active.setStyleSheet("color: #888; margin-top: 10px;"); lay.addWidget(self.lbl_active)

        b_play = QPushButton("▶  LAUNCH GAME")
        b_play.setObjectName("actionBtn"); b_play.setFixedHeight(50)
        b_play.setEnabled(False); b_play.clicked.connect(self._play)
        self.btn_play = b_play; lay.addWidget(b_play)
        lay.addStretch()
        self.pages["Home"] = page

    def _build_versions_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("Select Version & Loader"))
        lay.addSpacing(10)
        
        lay.addWidget(QLabel("Minecraft Version"))
        self.combo_ver = QComboBox(); lay.addWidget(self.combo_ver)

        lay.addWidget(QLabel("Mod Loader"))
        self.combo_loader = QComboBox()
        self.combo_loader.addItems(["Vanilla", "Fabric", "Forge", "Quilt"])
        lay.addWidget(self.combo_loader)

        b = QPushButton("Install Selected Profile"); b.setObjectName("actionBtn"); b.clicked.connect(self._install_version); lay.addWidget(b)
        lay.addStretch()
        self.pages["Versions"] = page

    def _build_skin_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("Offline Skin Injector"))
        lay.addSpacing(10)
        
        self.lbl_skin = QLabel("No skin selected")
        self.lbl_skin.setStyleSheet("color: #888;")
        b_pick = QPushButton("Select 64x64 PNG"); b_pick.setObjectName("secondaryBtn"); b_pick.clicked.connect(self._pick_skin); lay.addWidget(b_pick)
        lay.addWidget(self.lbl_skin)

        b_apply = QPushButton("Apply Skin"); b_apply.setObjectName("actionBtn"); b_apply.clicked.connect(self._apply_skin); lay.addWidget(b_apply)
        lay.addStretch()
        self.pages["Skin"] = page

    def _build_mods_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("Auto-Optimize Mod Bundle (Requires Fabric/Quilt)"))
        lay.addSpacing(10)
        
        mods = [("Sodium (Rendering)", "sodium"), ("Lithium (Physics)", "lithium"), ("FerriteCore (RAM)", "ferrite-core"), 
                ("ImmediatelyFast (GUI)", "immediatelyfast"), ("MoreCulling (Visibility)", "moreculling"), ("Iris Shaders", "iris")]
        self.chk_mods = {}
        for name, slug in mods:
            chk = QCheckBox(name)
            if slug != "iris": chk.setChecked(True)
            self.chk_mods[slug] = chk
            lay.addWidget(chk)

        b = QPushButton("Download & Install Mods"); b.setObjectName("actionBtn"); b.clicked.connect(self._install_optimods); lay.addWidget(b)
        lay.addStretch()
        self.pages["Mods"] = page

    # --- LOGIC (Same reliable backend as before) ---
    def _refresh_accounts(self):
        self.acc_list.clear()
        for a in self.accounts: self.acc_list.addItem(f"{a['username']}  (offline)")

    def _add_account(self):
        name, ok = QInputDialog.getText(self, "Add Offline Account", "Username:")
        if not ok or not name.strip(): return
        name = name.strip(); uid = offline_uuid(name)
        self.accounts.append({"username": name, "uuid": uid, "type": "offline"})
        self._save_accounts(); self._refresh_accounts()

    def _del_account(self):
        idx = self.acc_list.currentRow()
        if idx < 0: return
        self.accounts.pop(idx); self._save_accounts(); self._refresh_accounts()
        self.lbl_active.setText("No account selected."); self.btn_play.setEnabled(False)

    def _pick_skin(self):
        p, _ = QFileDialog.getOpenFileName(self, "Skin PNG", "", "PNG (*.png)")
        if p: self._skin_path = p; self.lbl_skin.setText(p)

    def _apply_skin(self):
        if not self._skin_path: return
        self._run_worker(self._do_apply_skin)

    def _do_apply_skin(self, log, prog):
        rp_dir = os.path.join(MC_DIR, "resourcepacks", "UREEDXD_Skin")
        shutil.rmtree(rp_dir, ignore_errors=True); os.makedirs(rp_dir, exist_ok=True); prog(10)
        with open(os.path.join(rp_dir, "pack.mcmeta"), "w") as f: json.dump({"pack": {"pack_format": 34, "description": "UREEDXD Skin"}}, f)
        tex_dir = os.path.join(rp_dir, "assets", "minecraft", "textures", "entity", "player", "wide")
        os.makedirs(tex_dir, exist_ok=True); shutil.copy2(self._skin_path, os.path.join(tex_dir, "steve.png")); prog(100)

    def _play(self):
        idx = self.acc_list.currentRow()
        if idx < 0: return
        acc = self.accounts[idx]; mc_ver = self.combo_ver.currentText(); loader = self.combo_loader.currentText().lower()
        profile = mc_ver
        if loader != "vanilla":
            try:
                ml = minecraft_launcher_lib.mod_loader.get_mod_loader(loader)
                profile = ml.install(mc_ver, MC_DIR, callback={"setStatus": lambda s: self.statusBar().showMessage(s)})
            except Exception as e: self.console.append(f"[ERROR] {e}"); return
        try: minecraft_launcher_lib.install.install_minecraft_version(mc_ver, MC_DIR)
        except: pass
        self._pre_optimize(mc_ver)
        opts = {"username": acc["username"], "uuid": acc["uuid"], "token": "0", "launcherName": "UREEDXDCLIENT", "gameDirectory": MC_DIR,
                "jvmArguments": ["-XX:+UseG1GC", "-XX:+ParallelRefProcEnabled", "-XX:MaxGCPauseMillis=50", "-Xmx2G", "-Xms512M"]}
        cmd = minecraft_launcher_lib.command.get_minecraft_command(profile, MC_DIR, opts)
        subprocess.Popen(cmd, cwd=MC_DIR)

    def _install_version(self):
        mc_ver = self.combo_ver.currentText(); loader = self.combo_loader.currentText().lower()
        self._run_worker(lambda log, prog: self._do_install_version(mc_ver, loader, log, prog))

    def _do_install_version(self, mc_ver, loader, log, prog):
        def cb(s): self.statusBar().showMessage(s)
        maxv=[0]
        def cm(m): maxv[0]=m
        def cp(v): prog(int(100*v/maxv[0]) if maxv[0]>0 else 0)
        callback = {"setStatus": cb, "setMax": cm, "setProgress": cp}
        minecraft_launcher_lib.install.install_minecraft_version(mc_ver, MC_DIR, callback=callback)
        if loader != "vanilla":
            try:
                ml = minecraft_launcher_lib.mod_loader.get_mod_loader(loader)
                ml.install(mc_ver, MC_DIR, callback={"setStatus": cb})
            except Exception as e: log(f"Loader error: {e}")
        self._pre_optimize(mc_ver); prog(100)

    def _pre_optimize(self, mc_ver):
        opt_path = os.path.join(MC_DIR, "options.txt")
        overrides = {"renderDistance":"4","simulationDistance":"3","entityDistanceScaling":"0.5","particles":"0","maxFps":"120","graphicsMode":"1","ao":"0","entityShadows":"false","enableVsync":"false"}
        data = {}
        if os.path.exists(opt_path):
            with open(opt_path, "r") as f:
                for line in f:
                    if ":" in line: k,v=line.strip().split(":",1); data[k]=v
        data.update(overrides)
        with open(opt_path, "w") as f:
            for k,v in data.items(): f.write(f"{k}:{v}\n")

    def _install_optimods(self):
        loader = self.combo_loader.currentText().lower()
        if loader not in ("fabric", "quilt"): QMessageBox.warning(self, "Mods", "Requires Fabric/Quilt."); return
        mc_ver = self.combo_ver.currentText()
        self._run_worker(lambda log, prog: self._do_install_optimods(mc_ver, loader, log, prog))

    def _do_install_optimods(self, mc_ver, loader, log, prog):
        MODS_DIR = os.path.join(MC_DIR, "mods"); os.makedirs(MODS_DIR, exist_ok=True)
        bundle = [slug for slug, chk in self.chk_mods.items() if chk.isChecked()]
        n = len(bundle)
        for i, slug in enumerate(bundle, 1):
            log(f"[{i}/{n}] {slug}…")
            try:
                url = self._modrinth_file_url(slug, mc_ver, loader)
                if not url: continue
                self._download(url, os.path.join(MODS_DIR, url.split("/")[-1]))
            except Exception as e: log(f"  Error: {e}")
            prog(int(100 * i / n))

    def _modrinth_file_url(self, slug, game_version, loader):
        r = requests.get(f"{MODRINTH_V2}/project/{slug}/version", params={"loaders": json.dumps([loader]), "game_versions": json.dumps([game_version])}, headers=UA, timeout=30)
        if not r.json(): return None
        for f in r.json()[0].get("files", []):
            if f.get("primary"): return f["url"]
        return r.json()[0]["files"][0]["url"]

    def _download(self, url, dst):
        r = requests.get(url, headers=UA, stream=True, timeout=120); r.raise_for_status()
        with open(dst, "wb") as f:
            for chunk in r.iter_content(8192): f.write(chunk)

    def _refresh_versions(self):
        vers = [v["id"] for v in minecraft_launcher_lib.utils.get_version_list() if v["type"] == "release" and int(v["id"].split(".")[1]) >= 16]
        self.combo_ver.clear(); self.combo_ver.addItems(vers)

    def _run_worker(self, fn):
        self._w = Worker(fn)
        self._w.log.connect(self.console.append)
        self._w.progress.connect(self.prog.setValue)
        self._w.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = UreedxdClient()
    win.show()
    sys.exit(app.exec())
