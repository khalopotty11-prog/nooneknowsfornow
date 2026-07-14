# main.py
import os, sys, urllib.request
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox, QProgressBar
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

CLIENT_DOWNLOAD_URL = "https://raw.githubusercontent.com/khalopotty11-prog/nooneknowsfornow/main/ureedxd_client.py"
ICON_FILENAME = "UREEDXD.ico"

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except: pass

STYLE = """
QMainWindow { background-color: #0e0e0e; }
QWidget { background-color: #0e0e0e; color: #fff; }
QLabel#title { color: #0078d4; font-size: 28px; font-weight: bold; }
QLabel#sub { color: #666; font-size: 12px; }
QLineEdit { background: #1a1a1a; border: 1px solid #333; border-radius: 6px; padding: 12px; color: #fff; font-size: 14px; }
QPushButton#browse { background: #1a1a1a; border: 1px solid #333; border-radius: 6px; padding: 12px; color: #fff; }
QPushButton#install { background: #0078d4; border: none; border-radius: 6px; padding: 15px; font-size: 16px; font-weight: bold; color: white; }
QPushButton#install:hover { background: #1a86d8; }
QProgressBar { border: none; border-radius: 6px; background: #1a1a1a; max-height: 6px; color: none; }
QProgressBar::chunk { background: #0078d4; border-radius: 6px; }
"""

class Worker(QThread):
    log = Signal(str); progress = Signal(int); done = Signal(bool)
    def __init__(self, fn): super().__init__(); self.fn = fn
    def run(self):
        try: self.fn(self.log, self.progress); self.done.emit(True)
        except Exception as e: self.log.emit(str(e)); self.done.emit(False)

class SetupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UREEDXDCLIENT Setup")
        self.setFixedSize(500, 300)
        self.setStyleSheet(STYLE)
        self.icon_path = os.path.join(os.path.dirname(sys.executable), ICON_FILENAME)

        central = QWidget(); self.setCentralWidget(central)
        lay = QVBoxLayout(central); lay.setSpacing(15)

        lay.addWidget(QLabel("UREEDXDCLIENT", objectName="title"))
        lay.addWidget(QLabel("Ultra Optimized Minecraft Client", objectName="sub"))

        hl = QWidget(); hl_lay = QVBoxLayout(hl); hl_lay.setContentsMargins(0,0,0,0)
        hl_lay.addWidget(QLabel("Installation Path:"))
        path_lay = QHBoxLayout()
        self.path = QLineEdit(os.path.join("C:", "Games", "UREEDXDCLIENT"))
        path_lay.addWidget(self.path)
        b = QPushButton("Browse", objectName="browse"); b.clicked.connect(self.browse); path_lay.addWidget(b)
        hl_lay.addLayout(path_lay)
        lay.addWidget(hl)

        self.prog = QProgressBar(); self.prog.setValue(0); lay.addWidget(self.prog)
        self.status = QLabel(""); self.status.setStyleSheet("color: #888; font-size: 11px;"); lay.addWidget(self.status)

        b_install = QPushButton("Install & Create Desktop Shortcut", objectName="install")
        b_install.setCursor(Qt.PointingHandCursor)
        b_install.clicked.connect(self.start_install); lay.addWidget(b_install)

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Folder")
        if d: self.path.setText(d)

    def start_install(self):
        for w in self.findChildren(QPushButton): w.setEnabled(False)
        self.w = Worker(lambda log, prog: self.do_install(self.path.text(), log, prog))
        self.w.log.connect(self.status.setText)
        self.w.progress.connect(self.prog.setValue)
        self.w.done.connect(self.finished)
        self.w.start()

    def do_install(self, path, log, prog):
        os.makedirs(os.path.join(path, "instance", "mods"), exist_ok=True); prog(10)
        log("Downloading client...")
        urllib.request.urlretrieve(CLIENT_DOWNLOAD_URL, os.path.join(path, "ureedxd_client.py")); prog(60)
        
        bat = f"@echo off\nstart \"\" pythonw \"{os.path.join(path, 'ureedxd_client.py')}\"\nexit\n"
        with open(os.path.join(path, "Play UREEDXDCLIENT.bat"), "w") as f: f.write(bat)
        
        if os.path.exists(self.icon_path):
            import shutil
            shutil.copy(self.icon_path, os.path.join(path, ICON_FILENAME))
        prog(80)
        log("Creating shortcut...")
        
        # VBS Script for perfect Windows Shortcut
        vbs = f"""Set WshShell = CreateObject("WScript.Shell")
oShellLink = WshShell.CreateShortcut("{os.path.join(os.path.expanduser('~'), 'Desktop', 'UREEDXDCLIENT.lnk')}")
oShellLink.TargetPath = "{os.path.join(path, 'Play UREEDXDCLIENT.bat')}"
oShellLink.WorkingDirectory = "{path}"
oShellLink.IconLocation = "{os.path.join(path, ICON_FILENAME)}"
oShellLink.Save"""
        vbs_path = os.path.join(path, "set.vbs")
        with open(vbs_path, "w") as f: f.write(vbs)
        import subprocess; subprocess.run(['wscript.exe', vbs_path], shell=True)
        try: os.remove(vbs_path)
        except: pass
        prog(100); log("Done!")

    def finished(self, ok):
        if ok: QMessageBox.information(self, "Done", "Installed! Check your desktop.")
        else: QMessageBox.critical(self, "Error", "Check your internet connection.")
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SetupApp(); w.show()
    sys.exit(app.exec())
