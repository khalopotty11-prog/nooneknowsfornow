# ureedxd_client.py
import sys, os, json, hashlib, uuid as _uuid, shutil, zipfile, requests, subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTabWidget, QTextEdit,
    QFileDialog, QLineEdit, QProgressBar, QListWidget, QCheckBox, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

import minecraft_launcher_lib

# --- Where to put Minecraft files ---
CLIENT_ROOT = os.path.dirname(os.path.abspath(__file__))
INSTANCE_JSON = os.path.join(CLIENT_ROOT, "instance.json")
if os.path.exists(INSTANCE_JSON):
    MC_DIR = json.load(open(INSTANCE_JSON, encoding="utf-8")).get("instance_dir",
                 minecraft_launcher_lib.utils.get_minecraft_directory())
else:
    MC_DIR = minecraft_launcher_lib.utils.get_minecraft_directory()

MODRINTH_V2 = "https://api.modrinth.com/v2"
UA = {"User-Agent": "UREEDXDCLIENT/1.0 (contact@example.com)"}

# --- Theming (FastClient‑ish dark) ---
STYLE = """
QMainWindow, QWidget { background:#0d0d0d; color:#e0e0e0; }
QLabel { color:#bdbdbd; }
QTabWidget::pane { border:1px solid #222; }
QTabBar::tab { background:#1a1a1a; color:#888; padding:10px 18px; margin-right:2px; border-radius:4px 4px 0 0; }
QTabBar::tab:selected { background:#0077b6; color:#fff; font-weight:bold; }
QComboBox { background:#1a1a1a; border:1px solid #333; border-radius:4px; padding:6px; color:#fff; }
QComboBox QAbstractItemView { background:#1a1a1a; color:#fff; selection-background-color:#0077b6; }
QPushButton { background:#0077b6; color:#fff; border:none; padding:8px 14px; border-radius:4px; font-weight:bold; }
QPushButton:hover { background:#005f8a; }
QPushButton:disabled { background:#2a2a2a; color:#555; }
QLineEdit { background:#1a1a1a; border:1px solid #333; border-radius:4px; padding:6px; color:#fff; }
QTextEdit { background:#0a0a0a; color:#00e676; border:1px solid #222; font-family:Consolas,monospace; }
QListWidget { background:#0f0f0f; border:1px solid #222; color:#e0e0e0; }
QListWidget::item:selected { background:#0077b6; }
QProgressBar { border:1px solid #333; border-radius:4px; text-align:center; color:#fff; background:#1a1a1a; }
QProgressBar::chunk { background:#00b4d8; }
QCheckBox { spacing:6px; }
QCheckBox::indicator { width:16px; height:16px; }
"""

def offline_uuid(name: str) -> str:
    """Standard offline UUID v3 used by offline servers."""
    return str(_uuid.UUID(bytes=hashlib.md5(f"OfflinePlayer:{name}".encode("utf-8")).digest()[:16], version=3))

# ---- Tiny worker thread helper ----
class Worker(QThread):
    log = Signal(str); progress = Signal(int); done_ok = Signal(bool)
    def __init__(self, fn):
        super().__init__(); self.fn = fn
    def run(self):
        try:
            self.fn(self.log, self.progress); self.done_ok.emit(True)
        except Exception as e:
            self.log.emit(f"ERROR: {e}"); self.done_ok.emit(False)

class UreedxdClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UREEDXDCLIENT")
        self.resize(880, 640)
        self.setStyleSheet(STYLE)

        # runtime state
        self.accounts = self._load_accounts()
        self.active_user = None

        self._ui()
        self._refresh_versions()

    # ---- persistence: tiny JSON account DB ----
    ACC_FILE = os.path.join(CLIENT_ROOT, "accounts.json")
    def _load_accounts(self):
        if os.path.exists(self.ACC_FILE):
            with open(self.ACC_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    def _save_accounts(self):
        with open(self.ACC_FILE, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, indent=2)

    # ====================== UI ======================
    def _ui(self):
        cw = QWidget(); self.setCentralWidget(cw); root = QVBoxLayout(cw)

        top = QLabel("UREEDXDCLIENT")
        top.setStyleSheet("color:#00b4d8; font-size:20px; font-weight:bold;")
        top.setAlignment(Qt.AlignCenter); root.addWidget(top)

        self.tabs = QTabWidget(); root.addWidget(self.tabs)

        # tabs
        self._tab_home(); self._tab_versions(); self._tab_skin(); self._tab_mods()

        self.console = QTextEdit(); self.console.setReadOnly(True)
        root.addWidget(self.console)
        self.prog = QProgressBar(); self.prog.setValue(0); root.addWidget(self.prog)

        self.statusBar().showMessage("Ready.")

    # ---------- HOME (accounts + quick launch) ----------
    def _tab_home(self):
        w = QWidget(); lay = QVBoxLayout(w)

        lay.addWidget(QLabel("Offline Accounts"))
        self.acc_list = QListWidget(); lay.addWidget(self.acc_list)
        self._refresh_accounts()

        hl = QHBoxLayout()
        b_add = QPushButton("Add Account"); b_add.clicked.connect(self._add_account); hl.addWidget(b_add)
        b_del = QPushButton("Remove"); b_del.clicked.connect(self._del_account); hl.addWidget(b_del)
        lay.addLayout(hl)

        self.lbl_active = QLabel("No account selected.")
        self.lbl_active.setStyleSheet("color:#ffd54f;"); lay.addWidget(self.lbl_active)

        b_play = QPushButton("▶  Play selected account")
        b_play.setEnabled(False); b_play.clicked.connect(self._play)
        self.btn_play = b_play; lay.addWidget(b_play)

        self.tabs.addTab(w, "Home")

    def _refresh_accounts(self):
        self.acc_list.clear()
        for a in self.accounts:
            self.acc_list.addItem(f"{a['username']}  (offline)")

    def _add_account(self):
        name, ok = QInputDialog.getText(self, "Add offline account", "Username (cracked):")
        if not ok or not name.strip(): return
        name = name.strip()
        uid = offline_uuid(name)
        self.accounts.append({"username": name, "uuid": uid, "type": "offline"})
        self._save_accounts(); self._refresh_accounts()

    def _del_account(self):
        idx = self.acc_list.currentRow()
        if idx < 0: return
        self.accounts.pop(idx)
        self._save_accounts(); self._refresh_accounts()
        self.lbl_active.setText("No account selected."); self.btn_play.setEnabled(False)

    def _select_account(self):
        idx = self.acc_list.currentRow()
        if idx < 0: return None
        a = self.accounts[idx]; self.active_user = a
        self.lbl_active.setText(f"Playing as: {a['username']}  {a['uuid']}")
        self.btn_play.setEnabled(True)
        return a

    # ---------- VERSIONS (choose MC ver + loader) ----------
    def _tab_versions(self):
        w = QWidget(); lay = QVBoxLayout(w)

        lay.addWidget(QLabel("Minecraft version"))
        self.combo_ver = QComboBox(); lay.addWidget(self.combo_ver)

        lay.addWidget(QLabel("Loader"))
        self.combo_loader = QComboBox()
        self.combo_loader.addItems(["Vanilla", "Fabric", "Forge", "Quilt"])
        lay.addWidget(self.combo_loader)

        b = QPushButton("Install selected version/loader")
        b.clicked.connect(self._install_version); lay.addWidget(b)
        lay.addStretch()
        self.tabs.addTab(w, "Versions")

    def _refresh_versions(self):
        vers = [v["id"] for v in minecraft_launcher_lib.utils.get_version_list() if v["type"] == "release"]
        # Keep only 1.16+ where modern loaders are well supported
        vers = [v for v in vers if int(v.split(".")[1]) >= 16]
        self.combo_ver.clear(); self.combo_ver.addItems(vers)

    # ---------- SKIN ----------
    def _tab_skin(self):
        w = QWidget(); lay = QVBoxLayout(w)

        lay.addWidget(QLabel("Offline skin (local resource pack)"))
        self.lbl_skin = QLabel("No skin selected")
        b_pick = QPushButton("Pick 64×64 skin PNG")
        b_pick.clicked.connect(self._pick_skin); lay.addWidget(b_pick)
        lay.addWidget(self.lbl_skin)

        b_apply = QPushButton("Apply skin to current instance")
        b_apply.clicked.connect(self._apply_skin); lay.addWidget(b_apply)
        lay.addStretch()
        self.tabs.addTab(w, "Skin")
        self._skin_path = None

    def _pick_skin(self):
        p, _ = QFileDialog.getOpenFileName(self, "Skin PNG", "", "PNG (*.png)")
        if p:
            self._skin_path = p; self.lbl_skin.setText(p)

    def _apply_skin(self):
        if not self._skin_path:
            QMessageBox.warning(self, "No skin", "Pick a skin first."); return
        self._run_worker(self._do_apply_skin)

    def _do_apply_skin(self, log, prog):
        rp_dir = os.path.join(MC_DIR, "resourcepacks", "UREEDXD_Skin")
        shutil.rmtree(rp_dir, ignore_errors=True)
        os.makedirs(rp_dir, exist_ok=True)
        prog(10)

        # pack.mcmeta (pack_format 34 is safe for 1.20+; for 1.16–1.19.2 use 6/9)
        mcmeta_path = os.path.join(rp_dir, "pack.mcmeta")
        with open(mcmeta_path, "w", encoding="utf-8") as f:
            json.dump({"pack": {"pack_format": 34, "description": "UREEDXD Offline Skin"}}, f, indent=2)
        prog(40)

        # Inject into assets so it replaces Steve/Alex locally
        tex_dir = os.path.join(rp_dir, "assets", "minecraft", "textures", "entity", "player", "wide")
        os.makedirs(tex_dir, exist_ok=True)
        shutil.copy2(self._skin_path, os.path.join(tex_dir, "steve.png"))
        prog(70)

        # Enable it in options.txt if present
        opt_path = os.path.join(MC_DIR, "options.txt")
        packs = []
        if os.path.exists(opt_path):
            with open(opt_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("resourcePacks:"):
                        try:
                            packs = json.loads(line.split(":",1)[1].strip())
                        except Exception:
                            packs = []
        if "file/UREEDXD_Skin" not in packs:
            packs.append("file/UREEDXD_Skin")
            # Rewrite options.txt with updated resourcePacks line
            lines_out = []
            replaced = False
            if os.path.exists(opt_path):
                with open(opt_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("resourcePacks:"):
                            lines_out.append(f"resourcePacks:{json.dumps(packs)}\n"); replaced = True
                        else:
                            lines_out.append(line)
            if not replaced:
                lines_out.append(f"resourcePacks:{json.dumps(packs)}\n")
            with open(opt_path, "w", encoding="utf-8") as f:
                f.writelines(lines_out)
        prog(90); log("Skin applied."); prog(100)

    # ---------- MODS (auto FPS bundle) ----------
    def _tab_mods(self):
        w = QWidget(); lay = QVBoxLayout(w)

        lay.addWidget(QLabel("Optimization mods (Fabric) — will skip if loader != Fabric"))
        self.chk_sodium = QCheckBox("Sodium (rendering)"); self.chk_sodium.setChecked(True); lay.addWidget(self.chk_sodium)
        self.chk_lithium = QCheckBox("Lithium (game logic)"); self.chk_lithium.setChecked(True); lay.addWidget(self.chk_lithium)
        self.chk_ferrite = QCheckBox("FerriteCore (RAM)"); self.chk_ferrite.setChecked(True); lay.addWidget(self.chk_ferrite)
        self.chk_fast = QCheckBox("ImmediatelyFast (GUI/HUD)"); self.chk_fast.setChecked(True); lay.addWidget(self.chk_fast)
        self.chk_cull = QCheckBox("MoreCulling (hide unseen)"); self.chk_cull.setChecked(True); lay.addWidget(self.chk_cull)
        self.chk_iris = QCheckBox("Iris Shaders (optional)"); self.chk_iris.setChecked(False); lay.addWidget(self.chk_iris)

        b = QPushButton("Install selected optimization mods")
        b.clicked.connect(self._install_optimods); lay.addWidget(b)
        lay.addStretch()
        self.tabs.addTab(w, "Mods")

    # ====================== ACTIONS ======================

    def _play(self):
        acc = self._select_account()
        if not acc: return
        mc_ver = self.combo_ver.currentText()
        loader = self.combo_loader.currentText().lower()  # vanilla/fabric/forge/quilt

        # Determine the exact profile name to launch (Vanilla vs loader)
        profile = mc_ver
        if loader != "vanilla":
            try:
                ml = minecraft_launcher_lib.mod_loader.get_mod_loader(loader)
                profile = ml.install(mc_ver, MC_DIR, callback={"setStatus": lambda s: self.statusBar().showMessage(s)})
            except Exception as e:
                self.console.append(f"[ERROR] Failed to install {loader}: {e}")
                return

        # Ensure the base version files exist too (safe to call even if already installed)
        try:
            minecraft_launcher_lib.install.install_minecraft_version(mc_ver, MC_DIR)
        except Exception:
            pass

        # Pre‑optimize: low‑end options.txt + smart JVM
        self._pre_optimize(mc_ver)

        opts = {
            "username": acc["username"],
            "uuid": acc["uuid"],
            "token": "0",
            "launcherName": "UREEDXDCLIENT",
            "gameDirectory": MC_DIR,
        }

        # Smart JVM flags tuned for low‑end (no more than ~2G unless user has more)
        opts["jvmArguments"] = [
            "-XX:+UseG1GC",
            "-XX:+ParallelRefProcEnabled",
            "-XX:MaxGCPauseMillis=50",
            "-XX:G1NewSizePercent=30",
            "-XX:G1MaxNewSizePercent=40",
            "-XX:G1HeapRegionSize=8M",
            "-XX:G1ReservePercent=20",
            "-XX:G1HeapWastePercent=5",
            "-XX:G1MixedGCCountTarget=4",
            "-XX:InitiatingHeapOccupancyPercent=15",
            "-XX:G1MixedGCLiveThresholdPercent=90",
            "-XX:G1RSetUpdatingPauseTimePercent=5",
            "-Xmx2G", "-Xms512M",
        ]

        cmd = minecraft_launcher_lib.command.get_minecraft_command(profile, MC_DIR, opts)
        self.console.append(f"[LAUNCH] profile={profile} dir={MC_DIR}")
        self.console.append(" ".join(cmd))
        try:
            subprocess.Popen(cmd, cwd=MC_DIR)
        except Exception as e:
            self.console.append(f"[LAUNCH ERROR] {e}")

    def _install_version(self):
        mc_ver = self.combo_ver.currentText()
        loader = self.combo_loader.currentText().lower()
        self._run_worker(lambda log, prog: self._do_install_version(mc_ver, loader, log, prog))

    def _do_install_version(self, mc_ver, loader, log, prog):
        log(f"Installing MC {mc_ver}…")
        def cb_setStatus(s): self.statusBar().showMessage(s)
        maxv = [0]
        def cb_setMax(m): maxv[0] = m
        def cb_setProgress(v):
            if maxv[0] > 0:
                prog(int(100 * v / maxv[0]))

        callback = {"setStatus": cb_setStatus, "setMax": cb_setMax, "setProgress": cb_setProgress}
        minecraft_launcher_lib.install.install_minecraft_version(mc_ver, MC_DIR, callback=callback)

        if loader != "vanilla":
            log(f"Installing {loader}…")
            try:
                ml = minecraft_launcher_lib.mod_loader.get_mod_loader(loader)
                profile = ml.install(mc_ver, MC_DIR, callback={"setStatus": cb_setStatus})
                log(f"Installed loader profile: {profile}")
            except Exception as e:
                log(f"Loader error (you can still play Vanilla): {e}")

        # Pre‑optimize right after install
        self._pre_optimize(mc_ver)
        prog(100); log("Done.")

    def _pre_optimize(self, mc_ver):
        """Optimize before mods: low-end options.txt + ensure JVM hints in options if you want."""
        opt_path = os.path.join(MC_DIR, "options.txt")
        overrides = {
            "renderDistance": "4",
            "simulationDistance": "3",
            "entityDistanceScaling": "0.5",
            "guiScale": "0",
            "particles": "0",
            "maxFps": "120",
            "graphicsMode": "1",
            "ao": "0",
            "biomeBlendRadius": "0",
            "entityShadows": "false",
            "enableVsync": "false",
            "renderClouds": "false",
        }
        data = {}
        if os.path.exists(opt_path):
            with open(opt_path, "r", encoding="utf-8") as f:
                for line in f:
                    if ":" in line:
                        k, v = line.strip().split(":", 1)
                        data[k] = v
        data.update(overrides)
        with open(opt_path, "w", encoding="utf-8") as f:
            for k, v in data.items():
                f.write(f"{k}:{v}\n")

    def _install_optimods(self):
        loader = self.combo_loader.currentText().lower()
        if loader not in ("fabric", "quilt"):
            QMessageBox.information(self, "Mods", "Auto FPS bundle needs Fabric/Quilt."); return
        mc_ver = self.combo_ver.currentText()
        self._run_worker(lambda log, prog: self._do_install_optimods(mc_ver, loader, log, prog))

    def _do_install_optimods(self, mc_ver, loader, log, prog):
        MODS_DIR = os.path.join(MC_DIR, "mods")
        os.makedirs(MODS_DIR, exist_ok=True)

        bundle = []
        if self.chk_sodium.isChecked(): bundle.append(("sodium", "Sodium"))
        if self.chk_lithium.isChecked(): bundle.append(("lithium", "Lithium"))
        if self.chk_ferrite.isChecked(): bundle.append(("ferrite-core", "FerriteCore"))
        if self.chk_fast.isChecked(): bundle.append(("immediatelyfast", "ImmediatelyFast"))
        if self.chk_cull.isChecked(): bundle.append(("moreculling", "MoreCulling"))
        if self.chk_iris.isChecked(): bundle.append(("iris", "Iris Shaders"))

        n = len(bundle)
        for i, (slug, label) in enumerate(bundle, 1):
            log(f"[{i}/{n}] {label}…")
            try:
                url = self._modrinth_file_url(slug, mc_ver, loader)
                if not url:
                    log(f"  Skipped (no compatible version)."); continue
                fname = url.split("/")[-1]
                dst = os.path.join(MODS_DIR, fname)
                self._download(url, dst)
                log(f"  → {fname}")
            except Exception as e:
                log(f"  Error: {e}")
            prog(int(100 * i / n))
        log("Bundle done."); prog(100)

    # ---- Modrinth helpers ----
    def _modrinth_file_url(self, slug: str, game_version: str, loader: str):
        """Get primary file URL for the latest version matching game_version & loader."""
        r = requests.get(f"{MODRINTH_V2}/project/{slug}/version",
                         params={"loaders": json.dumps([loader]),
                                 "game_versions": json.dumps([game_version])},
                         headers=UA, timeout=30)
        r.raise_for_status()
        versions = r.json()
        if not versions:
            return None
        for v in versions:
            for f in v.get("files", []):
                if f.get("primary"):
                    return f["url"]
        # fallback: first file of latest
        return versions[0]["files"][0]["url"]

    def _download(self, url, dst):
        r = requests.get(url, headers=UA, stream=True, timeout=120)
        r.raise_for_status()
        with open(dst, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

    # ---- small threading helper ----
    def _run_worker(self, fn):
        self._w = Worker(fn)
        self._w.log.connect(self.console.append)
        self._w.progress.connect(self.prog.setValue)
        self._w.done_ok.connect(lambda ok: self.statusBar().showMessage("Done." if ok else "Failed."))
        self._w.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = UreedxdClient()
    win.show()
    sys.exit(app.exec())
