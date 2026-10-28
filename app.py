import sys
import os

# Ensure src is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from src.ui.main_window import MainWindow

def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    app.setApplicationName("CleannerAgent")
    app.setApplicationDisplayName("CleannerAgent")
    app.setOrganizationName("CleannerAgent")

    # Set Application Icon from assets/icon.png or icon.ico
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for icon_candidate in [
        os.path.join(base_dir, "assets", "icon.png"),
        os.path.join(base_dir, "icon.png"),
        os.path.join(base_dir, "icon.ico"),
    ]:
        if os.path.exists(icon_candidate):
            from PySide6.QtGui import QIcon
            app.setWindowIcon(QIcon(icon_candidate))
            break

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
