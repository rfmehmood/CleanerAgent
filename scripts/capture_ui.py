import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure Windows font directory is loaded for QPA offscreen rendering
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1400, 860)

    # Populate sample scan candidates matching the reference mockup
    sample_candidates = [
        {
            "path": r"C:\Users\Farhan\AppData\Local\Temp",
            "size": 1288490188,  # ~1.2 GB
            "category": "Temporary Files",
            "app_name": "System",
            "confidence": "High",
            "safety_tier": "SAFE",
            "explanation": "Temporary files older than 7 days in system temp folder.",
            "consequences": "Some files may be needed by running applications.\nSafe to remove, but review before cleanup.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\AppData\Local\Google\Chrome\User Data\Default\Cache",
            "size": 863004262,  # ~823 MB
            "category": "Browser Cache",
            "app_name": "Chrome",
            "confidence": "High",
            "safety_tier": "SAFE",
            "explanation": "Chrome web browser disk cache.",
            "consequences": "Web pages may load slightly slower on first revisit as cache rebuilds.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\AppData\Roaming\discord\Cache",
            "size": 432013312,  # ~412 MB
            "category": "App Cache",
            "app_name": "Discord",
            "confidence": "Medium",
            "safety_tier": "SAFE",
            "explanation": "Discord media and message cache.",
            "consequences": "Images will redownload when viewed again in Discord.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Python\Lib\site-packages\pip\cache",
            "size": 384829030,  # ~367 MB
            "category": "Python Cache",
            "app_name": "Python",
            "confidence": "High",
            "safety_tier": "SAFE",
            "explanation": "Cached python wheels and downloaded packages.",
            "consequences": "Pip will redownload packages next time pip install is executed.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\AppData\Local\npm-cache",
            "size": 260046848,  # ~248 MB
            "category": "Node.js Cache",
            "app_name": "Node.js",
            "confidence": "High",
            "safety_tier": "SAFE",
            "explanation": "Node package manager tarball cache.",
            "consequences": "NPM will fetch packages from registry on subsequent installs.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\.ollama\models",
            "size": 1932735283,  # ~1.8 GB
            "category": "AI Model Storage",
            "app_name": "Ollama",
            "confidence": "Medium",
            "safety_tier": "CAUTION",
            "explanation": "Unused Ollama model manifests and blob weights.",
            "consequences": "Models will need to be repulled using `ollama pull` if needed.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\Downloads\Duplicate_Setup_Files",
            "size": 666894336,  # ~636 MB
            "category": "Duplicate Files",
            "app_name": "User",
            "confidence": "Low",
            "safety_tier": "CAUTION",
            "explanation": "Exact byte duplicates of files already present in Software archive.",
            "consequences": "Duplicate copies removed, original retained in source directory.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Windows\Logs",
            "size": 224395264,  # ~214 MB
            "category": "Logs & Reports",
            "app_name": "System",
            "confidence": "High",
            "safety_tier": "SAFE",
            "explanation": "Windows setup and CBS diagnostic logs.",
            "consequences": "Diagnostic event logs cleared.",
            "quarantine_available": True
        },
        {
            "path": r"C:\$Recycle.Bin",
            "size": 181403648,  # ~173 MB
            "category": "Recycle Bin",
            "app_name": "System",
            "confidence": "High",
            "safety_tier": "SAFE",
            "explanation": "Deleted files waiting in Windows Recycle Bin.",
            "consequences": "Recycle bin emptied permanently.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\Documents\Old Projects",
            "size": 1181116006,  # ~1.1 GB
            "category": "Large Files",
            "app_name": "User",
            "confidence": "Low",
            "safety_tier": "CAUTION",
            "explanation": "Large archived folders untouched for over 180 days.",
            "consequences": "Archive project folders removed.",
            "quarantine_available": True
        }
    ]

    window._on_scan_completed(sample_candidates)
    
    # Switch to Cleanup Center tab (index 3)
    window._navigate_to_key("cleanup")
    
    window.show()

    # Allow layout passes to complete
    app.processEvents()

    os.makedirs(r"d:\PC Cleaner\screenshots", exist_ok=True)
    out_path = r"d:\PC Cleaner\screenshots\cleanup_center_rendered.png"
    pixmap = window.grab()
    pixmap.save(out_path)
    print(f"Captured screenshot to: {out_path} ({pixmap.width()}x{pixmap.height()})")

if __name__ == "__main__":
    main()
