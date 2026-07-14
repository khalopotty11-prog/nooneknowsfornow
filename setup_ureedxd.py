# setup_ureedxd.py
import sys, os, json, platform, subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QProgressBar, QMessageBox
)
from PySide6.QtCore import QThread, Signal

DARK_QSS = """
QMainWindow, QWidget { background:#111; color:#eee; }
QLabel { color:#bbb; }
QLineEdit { background:#222; border:1px solid #444; border-radius:4px; padding:6px; color:#fff; }
QPushButton { background:#0077b6; color:#fff; border:none; padding:8px 16px; border-radius:4px; font-weight:bold; }
QPushButton:hover { background:#005f8a; }
QPushButton:disabled { background:#333; color:#666; }
QProgressBar { border:1px solid #444; border-radius:4px; text-align:center; color:#fff; background:#222; }
QProgressBar::chunk { background:#00b4d8; }
"""

class Worker(QThread):
    log = Signal(str); progress = Signal(int); done = Signal(bool)
    def __init__(self, target):
        super().__init__()
        self.target = target
    def run(self):
        try:
            self.target(self.log, self.progress)
            self.done.emit(True)
        except Exception as e:
            self.log.emit(f"ERROR: {e}")
            self.done.emit(False)

class SetupWizard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UREEDXDCLIENT — Setup")
        self.setFixedSize(540, 360)
        self.setStyleSheet(DARK_QSS)
        self._build_ui()

    def _build_ui(self):
        c = QWidget(); self.setCentralWidget(c); lay = QVBoxLayout(c)

        t = QLabel("UREEDXDCLIENT — Setup")
        t.setStyleSheet("font-size:18px; color:#00b4d8;")
        lay.addWidget(t)

        lay.addWidget(QLabel("Choose where the client & Minecraft instance will live:"))
        hl = QHBoxLayout()
        self.path_edit = QLineEdit(os.path.join(os.path.expanduser("~"), "UREEDXDCLIENT"))
        hl.addWidget(self.path_edit)
        b = QPushButton("Browse…"); b.clicked.connect(self._browse); hl.addWidget(b)
        lay.addLayout(hl)

        self.prog = QProgressBar(); self.prog.setValue(0); lay.addWidget(self.prog)
        self.status = QLabel("Ready."); lay.addWidget(self.status)

        bl = QHBoxLayout(); bl.addStretch()
        self.install_btn = QPushButton("Install & Launch"); self.install_btn.clicked.connect(self._install); bl.addWidget(self.install_btn)
        lay.addLayout(bl)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select install folder")
        if d: self.path_edit.setText(d)

    def _install(self):
        base = os.path.normpath(self.path_edit.text().strip())
        if not base:
            QMessageBox.warning(self, "Oops", "Pick a folder first."); return
        self.install_btn.setEnabled(False)
        self._worker = Worker(lambda log, prog: self._do_install(base, log, prog))
        self._worker.log.connect(self.status.setText)
        self._worker.progress.connect(self.prog.setValue)
        self._worker.done.connect(lambda ok: self._on_done(base, ok))
        self._worker.start()

    def _do_install(self, base, log, prog):
        def step(p): prog.emit(p)

        instance = os.path.join(base, "instance")
        for d in (
            instance,
            os.path.join(instance, "mods"),
            os.path.join(instance, "resourcepacks"),
            os.path.join(instance, "shaderpacks"),
        ):
            os.makedirs(d, exist_ok=True)
        step(20)

        # Persist instance path for the client
        with open(os.path.join(base, "instance.json"), "w") as f:
            json.dump({"instance_dir": instance}, f, indent=2)
        step(40)

        # Cross‑platform shortcut (BAT for Windows)
        client_py = os.path.abspath("ureedxd_client.py")
        bat_body = f"@echo off\nstart \"\" pythonw \"{client_py}\"\n"
        bat = os.path.join(base, "Launch UREEDXDCLIENT.bat")
        with open(bat, "w") as f:
            f.write(bat_body)
        step(60)

        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            dst = os.path.join(desktop, "UREEDXDCLIENT.bat")
            with open(dst, "w") as f:
                f.write(bat_body)
        except Exception:
            pass
        step(80)

        log("Creating shortcuts…"); step(90); log("Done.")

    def _on_done(self, base, ok):
        if not ok:
            self.status.setText("Setup failed.")
            self.install_btn.setEnabled(True)
            return
        self.status.setText("Installed. Launching client…")
        # Start the client from this process
        client_py = os.path.abspath("ureedxd_client.py")
        subprocess.Popen([sys.executable, client_py], cwd=base)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SetupWizard(); w.show()
    sys.exit(app.exec())
