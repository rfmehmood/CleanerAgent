import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1400, 860)

    sample_candidates = [
        {
            "path": r"C:\Users\Farhan\AppData\Local\Temp\vscode-update.zip",
            "size": 1288490188,  # ~1.2 GB
            "category": "Temporary Files",
            "app_name": "VS Code",
            "confidence": "High",
            "safety_tier": "SAFE",
            "action": "Quarantine & Clean",
            "explanation": "Temporary files older than 7 days in user temp directory.",
            "consequences": "Safe to remove. No disruption to running applications.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\AppData\Local\Google\Chrome\User Data\Default\Cache\data_0",
            "size": 863004262,  # ~823 MB
            "category": "Browser Cache",
            "app_name": "Google Chrome",
            "confidence": "High",
            "safety_tier": "SAFE",
            "action": "Safe to Delete",
            "explanation": "Chrome web browser disk cache and network responses.",
            "consequences": "Web pages may load slightly slower on first revisit as cache rebuilds.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\AppData\Roaming\discord\Cache\index",
            "size": 432013312,  # ~412 MB
            "category": "App Cache",
            "app_name": "Discord",
            "confidence": "Medium",
            "safety_tier": "SAFE",
            "action": "Safe to Delete",
            "explanation": "Discord media, emote, and message cache.",
            "consequences": "Images will redownload when viewed again in Discord.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\AppData\Local\Spotify\Storage",
            "size": 650000000,
            "category": "App Cache",
            "app_name": "Spotify",
            "confidence": "High",
            "safety_tier": "SAFE",
            "action": "Safe to Delete",
            "explanation": "Spotify streaming music local cache.",
            "consequences": "Songs stream from network rather than disk.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\AppData\Local\DeletedApp_Orphan",
            "size": 320000000,
            "category": "Uninstalled App Leftovers",
            "app_name": "DeletedApp",
            "confidence": "Medium",
            "safety_tier": "SAFE",
            "action": "Quarantine & Clean",
            "explanation": "Registry and folder remnants from uninstalled application.",
            "consequences": "No known active dependencies.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Python\Lib\site-packages\pip\cache\wheels",
            "size": 384829030,  # ~367 MB
            "category": "Python Cache",
            "app_name": "Python",
            "confidence": "High",
            "safety_tier": "SAFE",
            "action": "Safe to Delete",
            "explanation": "Cached python wheels and downloaded packages.",
            "consequences": "Pip will redownload packages next time pip install is executed.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\AppData\Local\npm-cache\_cacache",
            "size": 260046848,  # ~248 MB
            "category": "Node.js Cache",
            "app_name": "Node.js",
            "confidence": "High",
            "safety_tier": "SAFE",
            "action": "Safe to Delete",
            "explanation": "Node package manager tarball cache.",
            "consequences": "NPM will fetch packages from registry on subsequent installs.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\.ollama\models\blobs\sha256-43b7c",
            "size": 1932735283,  # ~1.8 GB
            "category": "AI Model Storage",
            "app_name": "Ollama",
            "confidence": "Medium",
            "safety_tier": "CAUTION",
            "action": "Review Before Action",
            "explanation": "Unused Ollama model manifests and blob weights.",
            "consequences": "Models will need to be repulled using `ollama pull` if needed.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\Downloads\Duplicate_Setup_Files\installer_v2.exe",
            "size": 666894336,  # ~636 MB
            "category": "Duplicate Files",
            "app_name": "File Explorer",
            "confidence": "Low",
            "safety_tier": "CAUTION",
            "action": "Review Before Action",
            "explanation": "Exact byte duplicates of files already present in Software archive.",
            "consequences": "Duplicate copies removed, original retained in source directory.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Windows\Logs\CBS\CBS.log",
            "size": 224395264,  # ~214 MB
            "category": "Logs & Reports",
            "app_name": "System",
            "confidence": "High",
            "safety_tier": "SAFE",
            "action": "Safe to Delete",
            "explanation": "Windows setup and CBS diagnostic logs.",
            "consequences": "Diagnostic event logs cleared.",
            "quarantine_available": True
        },
        {
            "path": r"C:\$Recycle.Bin\S-1-5-21\trash.bin",
            "size": 181403648,  # ~173 MB
            "category": "Recycle Bin",
            "app_name": "System",
            "confidence": "High",
            "safety_tier": "SAFE",
            "action": "Empty Recycle Bin",
            "explanation": "Deleted files waiting in Windows Recycle Bin.",
            "consequences": "Recycle bin emptied permanently.",
            "quarantine_available": True
        },
        {
            "path": r"C:\Users\Farhan\Documents\Old_Projects\archive_backup_2023.tar",
            "size": 3181116006,  # ~3.1 GB
            "category": "Large Files",
            "app_name": "User File",
            "confidence": "Low",
            "safety_tier": "CAUTION",
            "action": "Review Before Action",
            "explanation": "Large archived file (>100MB) untouched for over 180 days.",
            "consequences": "Archive file removed.",
            "quarantine_available": True
        }
    ]

    window._on_scan_completed(sample_candidates)
    
    # 1. Capture Deep View Overview
    window._navigate_to_key("deep_view")
    window.show()
    app.processEvents()

    os.makedirs(r"d:\PC Cleaner\screenshots", exist_ok=True)
    out_overview = r"d:\PC Cleaner\screenshots\deep_view_overview.png"
    window.grab().save(out_overview)
    print(f"Captured overview to: {out_overview}")

    # 2. Open Category Detail for Temporary Files
    window.deep_view._open_category("temp_files")
    app.processEvents()

    out_detail = r"d:\PC Cleaner\screenshots\deep_view_detail.png"
    window.grab().save(out_detail)
    print(f"Captured detail to: {out_detail}")

    # 3. Test Navigation back to Overview
    window.deep_view._back_to_overview()
    app.processEvents()

    # 4. Open Category Detail for AI Models & Storage
    window.deep_view._open_category("ai_models")
    app.processEvents()

    out_ai_detail = r"d:\PC Cleaner\screenshots\deep_view_ai_detail.png"
    window.grab().save(out_ai_detail)
    print(f"Captured AI detail to: {out_ai_detail}")


if __name__ == "__main__":
    main()
