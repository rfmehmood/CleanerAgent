import os
import sys
import shutil
import zipfile
import winreg
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QCheckBox,
    QProgressBar, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor, QPalette

APP_NAME = "CleannerAgent"
APP_VERSION = "1.0.0"
APP_PUBLISHER = "CleannerAgent"
APP_DESCRIPTION = "CleannerAgent - Local AI PC Maintenance & Storage Optimizer"
DEFAULT_INSTALL_SUBDIR = "Programs\\CleannerAgent"

def get_default_install_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / DEFAULT_INSTALL_SUBDIR
    return Path.home() / "AppData" / "Local" / DEFAULT_INSTALL_SUBDIR

def get_embedded_payload_path() -> Path:
    # PyInstaller extracts bundled files to sys._MEIPASS
    if hasattr(sys, "_MEIPASS"):
        embedded = Path(sys._MEIPASS) / "payload.zip"
        if embedded.exists():
            return embedded
    # Local fallback
    local_payload = Path(__file__).parent / "payload.zip"
    if local_payload.exists():
        return local_payload
    # Project root fallback
    root_payload = Path(__file__).resolve().parent.parent / "installer" / "payload.zip"
    if root_payload.exists():
        return root_payload
    return Path("installer/payload.zip").resolve()


def create_windows_shortcut(target_exe: str, shortcut_path: str, working_dir: str, description: str):
    powershell_code = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_exe}"
$Shortcut.WorkingDirectory = "{working_dir}"
$Shortcut.Description = "{description}"
$Shortcut.Save()
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", powershell_code], capture_output=True, check=False)


def register_uninstall(install_dir: Path, target_exe: Path, uninstaller_path: Path):
    try:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\CleannerAgent"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{str(target_exe)},0")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{str(uninstaller_path)}"')
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    except Exception as e:
        print(f"Failed to register uninstaller in registry: {e}")


def write_uninstaller_script(install_dir: Path) -> Path:
    uninstaller_bat = install_dir / "uninstall.bat"
    desktop_shortcut = Path.home() / "Desktop" / f"{APP_NAME}.lnk"
    start_menu_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    start_shortcut = start_menu_dir / f"{APP_NAME}.lnk"

    script = f"""@echo off
title Uninstalling {APP_NAME}...
echo ====================================================
echo        Uninstalling {APP_NAME}
echo ====================================================
echo.

:: 1. Remove Shortcuts
if exist "{desktop_shortcut}" (
    del /f /q "{desktop_shortcut}"
    echo [-] Removed Desktop shortcut.
)
if exist "{start_shortcut}" (
    del /f /q "{start_shortcut}"
    echo [-] Removed Start Menu shortcut.
)

:: 2. Remove Registry Entry
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\CleannerAgent" /f >nul 2>&1
echo [-] Removed Windows Registry registration.

:: 3. Clean files (wait for caller process to exit, then delete directory)
echo [-] Removing application files...
timeout /t 1 /nobreak >nul
cd /d "%TEMP%"
rd /s /q "{install_dir}" >nul 2>&1

echo.
echo {APP_NAME} has been completely uninstalled.
echo.
pause
"""
    with open(uninstaller_bat, "w", encoding="utf-8") as f:
        f.write(script)
    return uninstaller_bat


class InstallWorker(QThread):
    progress_changed = Signal(int, str)
    install_finished = Signal(bool, str)

    def __init__(self, target_dir: Path, create_desktop: bool, create_start: bool, register_app: bool):
        super().__init__()
        self.target_dir = target_dir
        self.create_desktop = create_desktop
        self.create_start = create_start
        self.register_app = register_app

    def run(self):
        try:
            payload_path = get_embedded_payload_path()
            if not payload_path.exists():
                self.install_finished.emit(False, f"Installation payload not found: {payload_path}")
                return

            self.progress_changed.emit(5, "Preparing target installation directory...")
            self.target_dir.mkdir(parents=True, exist_ok=True)

            self.progress_changed.emit(10, "Opening installation archive...")
            with zipfile.ZipFile(payload_path, "r") as z:
                total_files = len(z.infolist())
                extracted_files = 0

                for item in z.infolist():
                    z.extract(item, self.target_dir)
                    extracted_files += 1
                    pct = 10 + int((extracted_files / total_files) * 75)
                    self.progress_changed.emit(pct, f"Installing: {item.filename}")

            target_exe = self.target_dir / "CleannerAgent.exe"
            if not target_exe.exists():
                target_exe = self.target_dir / "AIPCCleanupAgent.exe"

            if not target_exe.exists():
                self.install_finished.emit(False, f"Installed executable missing in: {self.target_dir}")
                return

            # Create uninstaller
            self.progress_changed.emit(88, "Writing uninstaller script...")
            uninstaller_path = write_uninstaller_script(self.target_dir)

            # Shortcuts
            if self.create_desktop:
                self.progress_changed.emit(92, "Creating Desktop shortcut...")
                desktop_lnk = Path.home() / "Desktop" / f"{APP_NAME}.lnk"
                create_windows_shortcut(
                    str(target_exe),
                    str(desktop_lnk),
                    str(self.target_dir),
                    APP_DESCRIPTION
                )

            if self.create_start:
                self.progress_changed.emit(95, "Creating Start Menu shortcut...")
                start_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
                start_dir.mkdir(parents=True, exist_ok=True)
                start_lnk = start_dir / f"{APP_NAME}.lnk"
                create_windows_shortcut(
                    str(target_exe),
                    str(start_lnk),
                    str(self.target_dir),
                    APP_DESCRIPTION
                )

            # Registry registration
            if self.register_app:
                self.progress_changed.emit(98, "Registering in Windows Settings (Apps & features)...")
                register_uninstall(self.target_dir, target_exe, uninstaller_path)

            self.progress_changed.emit(100, "Installation complete!")
            self.install_finished.emit(True, str(target_exe))

        except Exception as e:
            self.install_finished.emit(False, str(e))


class SetupWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Setup")
        self.resize(620, 480)
        self.setMinimumSize(580, 440)
        self.installed_exe: str = ""

        # Set Window Icon
        from PySide6.QtGui import QIcon, QPixmap
        base_dir = Path(__file__).resolve().parent
        for icon_path in [
            base_dir / "icon.png",
            base_dir.parent / "icon.png",
            base_dir.parent / "assets" / "icon.png",
            base_dir.parent / "icon.ico",
        ]:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                break

        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #070b14;
            }
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                color: #e2e8f0;
            }
            QLineEdit {
                background-color: #0d1527;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 12.5px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12.5px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QPushButton#primaryBtn {
                background-color: #2563eb;
                border: 1px solid #3b82f6;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                padding: 9px 22px;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#primaryBtn:disabled {
                background-color: #1e293b;
                border-color: #334155;
                color: #64748b;
            }
            QCheckBox {
                color: #cbd5e1;
                font-size: 12.5px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #334155;
                background-color: #0d1527;
            }
            QCheckBox::indicator:checked {
                background-color: #2563eb;
                border: 1px solid #38bdf8;
            }
            QProgressBar {
                background-color: #0d1527;
                border: 1px solid #1e293b;
                border-radius: 6px;
                height: 18px;
                text-align: center;
                color: #ffffff;
                font-size: 11px;
                font-weight: 700;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #38bdf8);
                border-radius: 5px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(16)

        # Header Banner
        header = QFrame()
        header.setStyleSheet("background-color: #0d1527; border: 1px solid #1e293b; border-radius: 10px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(18, 16, 18, 16)
        h_layout.setSpacing(14)

        logo = QLabel()
        from PySide6.QtGui import QPixmap
        base_dir = Path(__file__).resolve().parent
        logo_loaded = False
        for icon_path in [
            base_dir / "icon.png",
            base_dir.parent / "icon.png",
            base_dir.parent / "assets" / "icon.png",
        ]:
            if icon_path.exists():
                pm = QPixmap(str(icon_path)).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo.setPixmap(pm)
                logo_loaded = True
                break
        if not logo_loaded:
            logo.setText("🛡️")
            logo.setStyleSheet("font-size: 32px;")
        logo.setStyleSheet(logo.styleSheet() + " background: transparent; border: none;")
        h_layout.addWidget(logo)

        h_text = QVBoxLayout()
        h_text.setSpacing(2)
        title_lbl = QLabel(f"{APP_NAME} Setup")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff; background: transparent; border: none;")
        ver_lbl = QLabel(f"Version {APP_VERSION} • 100% Free, Offline-Capable, and Local")
        ver_lbl.setStyleSheet("font-size: 11.5px; color: #38bdf8; background: transparent; border: none;")
        h_text.addWidget(title_lbl)
        h_text.addWidget(ver_lbl)
        h_layout.addLayout(h_text, stretch=1)
        main_layout.addWidget(header)

        # Installation Directory Selector
        dest_card = QFrame()
        dest_card.setStyleSheet("background-color: #0d1527; border: 1px solid #1e293b; border-radius: 10px;")
        d_layout = QVBoxLayout(dest_card)
        d_layout.setContentsMargins(18, 14, 18, 14)
        d_layout.setSpacing(8)

        dest_title = QLabel("Destination Folder:")
        dest_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #94a3b8; background: transparent; border: none;")
        d_layout.addWidget(dest_title)

        browse_box = QHBoxLayout()
        browse_box.setSpacing(8)
        self.path_edit = QLineEdit(str(get_default_install_dir()))
        browse_box.addWidget(self.path_edit, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_clicked)
        browse_box.addWidget(browse_btn)
        d_layout.addLayout(browse_box)
        main_layout.addWidget(dest_card)

        # Options Card
        options_card = QFrame()
        options_card.setStyleSheet("background-color: #0d1527; border: 1px solid #1e293b; border-radius: 10px;")
        o_layout = QVBoxLayout(options_card)
        o_layout.setContentsMargins(18, 14, 18, 14)
        o_layout.setSpacing(10)

        opt_title = QLabel("Setup Options:")
        opt_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #94a3b8; background: transparent; border: none;")
        o_layout.addWidget(opt_title)

        self.cb_desktop = QCheckBox("Create a Desktop Shortcut (Instant 1-click access)")
        self.cb_desktop.setChecked(True)
        o_layout.addWidget(self.cb_desktop)

        self.cb_start = QCheckBox("Add to Windows Start Menu Programs")
        self.cb_start.setChecked(True)
        o_layout.addWidget(self.cb_start)

        self.cb_register = QCheckBox("Register in Windows Installed Apps (Settings / Control Panel)")
        self.cb_register.setChecked(True)
        o_layout.addWidget(self.cb_register)

        self.cb_launch = QCheckBox(f"Launch {APP_NAME} automatically when setup finishes")
        self.cb_launch.setChecked(True)
        o_layout.addWidget(self.cb_launch)

        main_layout.addWidget(options_card)

        # Progress Section
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 11.5px; color: #94a3b8; background: transparent;")
        self.status_lbl.setVisible(False)
        main_layout.addWidget(self.status_lbl)

        main_layout.addStretch()

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.close)
        btn_bar.addWidget(self.cancel_btn)

        self.install_btn = QPushButton("Install Now")
        self.install_btn.setObjectName("primaryBtn")
        self.install_btn.clicked.connect(self._on_install_clicked)
        btn_bar.addWidget(self.install_btn)

        main_layout.addLayout(btn_bar)

    def _on_browse_clicked(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select Installation Folder", self.path_edit.text())
        if chosen:
            self.path_edit.setText(chosen)

    def _on_install_clicked(self):
        target_path_str = self.path_edit.text().strip()
        if not target_path_str:
            QMessageBox.warning(self, "Missing Path", "Please specify an installation directory.")
            return

        target_dir = Path(target_path_str)

        # Disable interactive inputs
        self.path_edit.setEnabled(False)
        self.cb_desktop.setEnabled(False)
        self.cb_start.setEnabled(False)
        self.cb_register.setEnabled(False)
        self.cb_launch.setEnabled(False)
        self.install_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.status_lbl.setVisible(True)
        self.status_lbl.setText("Starting installation...")

        self.worker = InstallWorker(
            target_dir=target_dir,
            create_desktop=self.cb_desktop.isChecked(),
            create_start=self.cb_start.isChecked(),
            register_app=self.cb_register.isChecked()
        )
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.install_finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, percent: int, text: str):
        self.progress_bar.setValue(percent)
        self.status_lbl.setText(text)

    def _on_finished(self, success: bool, msg: str):
        if success:
            self.installed_exe = msg
            self.status_lbl.setText("Installation completed successfully!")
            self.status_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #4ade80;")
            self.install_btn.setText("Finish & Launch" if self.cb_launch.isChecked() else "Finish")
            self.install_btn.setEnabled(True)
            self.install_btn.clicked.disconnect()
            self.install_btn.clicked.connect(self._on_finish_action)
        else:
            QMessageBox.critical(self, "Installation Error", f"Installation failed:\n\n{msg}")
            self.install_btn.setEnabled(True)
            self.install_btn.setText("Retry")
            self.cancel_btn.setEnabled(True)

    def _on_finish_action(self):
        if self.cb_launch.isChecked() and self.installed_exe and os.path.exists(self.installed_exe):
            try:
                subprocess.Popen([self.installed_exe], cwd=os.path.dirname(self.installed_exe))
            except Exception as e:
                print(f"Failed to launch installed app: {e}")
        self.close()


def main():
    app = QApplication(sys.argv)
    window = SetupWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

