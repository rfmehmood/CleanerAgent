from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from typing import List, Dict, Any

from .styles import DARK_THEME_QSS
from .dashboard_view import DashboardView
from .ai_assistant_view import AIAssistantView
from .deep_scanner_view import DeepScannerView
from .deep_view import DeepView
from .cleanup_center_view import CleanupCenterView
from .storage_explorer_view import StorageExplorerView
from .settings_view import SettingsView

from ..settings.config import SettingsManager
from ..database.db import DatabaseManager
from ..ai.ollama_client import OllamaClient
from ..ai.intent_parser import IntentParser
from ..quarantine.manager import QuarantineManager
from ..cleanup.executor import CleanupExecutor
from ..monitoring.watcher import BackgroundStorageMonitor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CleannerAgent - Local AI PC Maintenance & Storage Optimizer")
        self.resize(1400, 860)
        self.setMinimumSize(1150, 720)
        self.setStyleSheet(DARK_THEME_QSS)

        # Set Window Icon
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for icon_candidate in [
            os.path.join(base_dir, "assets", "icon.png"),
            os.path.join(base_dir, "icon.png"),
            os.path.join(base_dir, "icon.ico"),
        ]:
            if os.path.exists(icon_candidate):
                self.setWindowIcon(QIcon(icon_candidate))
                break

        # Core Services
        self.settings = SettingsManager()
        self.db = DatabaseManager(self.settings.db_path)
        self.quarantine_mgr = QuarantineManager(self.settings.quarantine_dir, self.db)
        self.executor = CleanupExecutor(self.quarantine_mgr, self.db, self.settings.get_custom_protected_paths())
        
        self.ollama = OllamaClient(
            host=self.settings.get_ollama_host(),
            model_name=self.settings.get_model_name()
        )
        self.intent_parser = IntentParser(self.ollama)
        
        self.current_candidates: List[Dict[str, Any]] = []

        if self.settings.get("background_monitoring_enabled", False):
            self.monitor = BackgroundStorageMonitor()
            self.monitor.start()
        else:
            self.monitor = None

        self._init_ui()
        self._check_ai_status()

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        outer_layout = QVBoxLayout(central_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 1. Top Window Navigation & Status Header Bar
        top_header = QFrame()
        top_header.setObjectName("topHeader")
        top_header.setStyleSheet("#topHeader { background-color: #070b14; border-bottom: 1px solid #1e293b; padding: 6px 16px; }")
        top_header_layout = QHBoxLayout(top_header)
        top_header_layout.setContentsMargins(10, 6, 14, 6)
        top_header_layout.setSpacing(14)

        # Left: App Brand & Subtitle
        brand_icon = QLabel()
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "assets", "icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_dir, "icon.png")
        if os.path.exists(icon_path):
            from PySide6.QtGui import QPixmap
            pm = QPixmap(icon_path).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            brand_icon.setPixmap(pm)
        else:
            brand_icon.setText("🛡️")
            brand_icon.setStyleSheet("font-size: 22px;")
        brand_icon.setStyleSheet(brand_icon.styleSheet() + " background: transparent; border: none;")
        top_header_layout.addWidget(brand_icon)

        brand_text_box = QVBoxLayout()
        brand_text_box.setSpacing(1)
        brand_title = QLabel("CleannerAgent")
        brand_title.setStyleSheet("font-size: 14.5px; font-weight: 800; color: #ffffff; background: transparent; border: none;")
        brand_sub = QLabel("Local • Free • Private")
        brand_sub.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 600; background: transparent; border: none;")
        brand_text_box.addWidget(brand_title)
        brand_text_box.addWidget(brand_sub)
        top_header_layout.addLayout(brand_text_box)

        top_header_layout.addStretch()

        # Right: AI Mode Status Pill & Ollama Badge
        self.ai_status_badge = QLabel("🟢 AI Ready (Qwen3.5:4b)")
        self.ai_status_badge.setStyleSheet(
            "background-color: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); "
            "border-radius: 12px; padding: 5px 14px; font-weight: 600; font-size: 11.5px;"
        )
        top_header_layout.addWidget(self.ai_status_badge)

        self.ollama_badge = QLabel("🦙 Ollama")
        self.ollama_badge.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 12px; padding: 5px 14px; font-weight: 600; font-size: 11.5px;"
        )
        top_header_layout.addWidget(self.ollama_badge)

        outer_layout.addWidget(top_header)

        # 2. Main Workspace (Sidebar on Left + Stacked Views on Right)
        workspace = QWidget()
        workspace.setObjectName("workspace")
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        # Left Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(215)
        sidebar.setStyleSheet("#sidebar { background-color: #070b14; border-right: 1px solid #1e293b; }")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 16)
        sidebar_layout.setSpacing(6)

        # Nav Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("🏠  Dashboard", 0, "dashboard"),
            ("💬  AI Assistant", 1, "assistant"),
            ("🔍  Deep Scanner", 2, "scanner"),
            ("📂  Deep View", 3, "deep_view"),
            ("🗑  Cleanup Center", 4, "cleanup"),
            ("📁  Storage Explorer", 5, "explorer"),
            ("⚙️  Settings", 6, "settings"),
        ]

        self.nav_buttons = {}
        for text, idx, key in nav_items:
            btn = QPushButton(text)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 10px 14px; font-size: 13px; font-weight: 600; color: #94a3b8; background-color: transparent; border: none; border-radius: 8px; margin: 2px 2px; } "
                "QPushButton:hover { background-color: rgba(255, 255, 255, 0.05); color: #f8fafc; } "
                "QPushButton:checked { background-color: #1d4ed8; color: #ffffff; font-weight: 700; }"
            )
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            self.nav_group.addButton(btn, idx)
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        self.nav_group.idClicked.connect(self._on_nav_clicked)
        sidebar_layout.addStretch()

        # Bottom Feature Card: "⚡ Free • Local • Your Data"
        priv_card = QFrame()
        priv_card.setObjectName("privCard")
        priv_card.setStyleSheet("#privCard { background-color: #0f172a; border-radius: 10px; padding: 12px; border: 1px solid #1e293b; }")
        priv_layout = QVBoxLayout(priv_card)
        priv_layout.setSpacing(5)
        priv_layout.setContentsMargins(8, 8, 8, 8)
        
        priv_title = QLabel("⚡ Free • Local • Your Data")
        priv_title.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #38bdf8; background: transparent; border: none;")
        
        priv_desc = QLabel("No telemetry. No tracking.\nNo external services.")
        priv_desc.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.4; background: transparent; border: none;")
        
        priv_layout.addWidget(priv_title)
        priv_layout.addWidget(priv_desc)
        sidebar_layout.addWidget(priv_card)

        # Footer tagline
        tagline = QLabel("A cleaner PC. A smoother you.")
        tagline.setStyleSheet("font-size: 11px; color: #64748b; padding-left: 6px; padding-top: 4px; background: transparent; border: none;")
        sidebar_layout.addWidget(tagline)

        workspace_layout.addWidget(sidebar)

        # Main Stacked Views
        self.stacked = QStackedWidget()

        self.dashboard_view = DashboardView(self.db, self.settings)
        self.dashboard_view.request_navigation.connect(self._navigate_to_key)

        self.assistant_view = AIAssistantView(self.intent_parser, self.db)

        self.scanner_view = DeepScannerView(self.db, self.settings)
        self.scanner_view.scan_completed.connect(self._on_scan_completed)

        self.deep_view = DeepView()
        self.deep_view.request_cleanup_view.connect(self._navigate_to_key)

        self.cleanup_view = CleanupCenterView(self.executor, self.quarantine_mgr, self.db)
        self.cleanup_view.cleanup_executed.connect(self._on_cleanup_executed)

        self.explorer_view = StorageExplorerView()

        self.settings_view = SettingsView(self.settings, self.ollama, self.db)
        self.settings_view.settings_updated.connect(self._on_settings_updated)

        self.stacked.addWidget(self.dashboard_view)  # index 0
        self.stacked.addWidget(self.assistant_view)  # index 1
        self.stacked.addWidget(self.scanner_view)    # index 2
        self.stacked.addWidget(self.deep_view)       # index 3
        self.stacked.addWidget(self.cleanup_view)    # index 4
        self.stacked.addWidget(self.explorer_view)   # index 5
        self.stacked.addWidget(self.settings_view)   # index 6

        workspace_layout.addWidget(self.stacked, stretch=1)
        outer_layout.addWidget(workspace, stretch=1)

    def _on_nav_clicked(self, idx: int):
        self.stacked.setCurrentIndex(idx)

    def _navigate_to_key(self, key: str):
        if key in self.nav_buttons:
            self.nav_buttons[key].setChecked(True)
            idx = list(self.nav_buttons.keys()).index(key)
            self.stacked.setCurrentIndex(idx)

    def _on_scan_completed(self, candidates: List[Dict[str, Any]]):
        self.current_candidates = candidates
        mode_str = self._get_ai_mode_name()
        self.dashboard_view.refresh_dashboard(candidates, ai_mode_str=mode_str)
        self.assistant_view.set_candidates(candidates)
        self.deep_view.set_candidates(candidates)
        self.cleanup_view.set_candidates(candidates)

    def _on_cleanup_executed(self):
        self.current_candidates = self.cleanup_view.all_candidates
        mode_str = self._get_ai_mode_name()
        self.dashboard_view.refresh_dashboard(self.current_candidates, ai_mode_str=mode_str)
        self.assistant_view.set_candidates(self.current_candidates)
        self.deep_view.set_candidates(self.current_candidates)

    def _on_settings_updated(self):
        self.ollama.host = self.settings.get_ollama_host()
        self.ollama.model_name = self.settings.get_model_name()
        self._check_ai_status()

    def _check_ai_status(self):
        ok, _ = self.ollama.check_connection()
        if ok and self.ollama.is_model_available():
            self.ai_status_badge.setText(f"🟢 AI Ready ({self.ollama.model_name})")
            self.ai_status_badge.setStyleSheet("background-color: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 8px; padding: 5px 12px; font-weight: 600; font-size: 12px;")
        else:
            self.ai_status_badge.setText("⚡ Rule Engine Active")
            self.ai_status_badge.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; border-radius: 8px; padding: 5px 12px; font-weight: 600; font-size: 12px;")

        mode_str = self._get_ai_mode_name()
        self.dashboard_view.refresh_dashboard(self.current_candidates, ai_mode_str=mode_str)

    def _get_ai_mode_name(self) -> str:
        ok, _ = self.ollama.check_connection()
        if ok and self.ollama.is_model_available():
            return f"Local AI ({self.ollama.model_name})"
        return "Rule-Based Engine"

    def closeEvent(self, event):
        if self.monitor:
            self.monitor.stop()
        event.accept()
