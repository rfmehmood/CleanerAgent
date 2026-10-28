import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QComboBox,
    QStackedWidget, QScrollArea, QGridLayout, QSizePolicy, QToolTip
)
from PySide6.QtCore import Qt, Signal

from ..scanner.categories import ScanCategory

CATEGORIES_CONFIG = [
    {
        "id": "large_files",
        "title": "Large Files",
        "icon": "📁",
        "color": "#fb923c",
        "bg_color": "rgba(251, 146, 60, 0.15)",
        "desc": "Files exceeding 500 MB located outside protected directories.",
        "match": lambda c: (
            c.get("category") == ScanCategory.LARGE_FILES or
            c.get("size", 0) >= 500 * 1024 * 1024 or
            "large" in c.get("category", "").lower()
        )
    },
    {
        "id": "duplicates",
        "title": "Duplicate Files",
        "icon": "👥",
        "color": "#93c5fd",
        "bg_color": "rgba(147, 197, 253, 0.15)",
        "desc": "Exact byte-for-byte duplicate copies identified across storage locations.",
        "match": lambda c: (
            c.get("category") == ScanCategory.DUPLICATES or
            "duplicate" in c.get("category", "").lower()
        )
    },
    {
        "id": "temp_files",
        "title": "Temporary Files",
        "icon": "🧹",
        "color": "#60a5fa",
        "bg_color": "rgba(96, 165, 250, 0.15)",
        "desc": "System and user temp files, installers, and transient caches older than 7 days.",
        "match": lambda c: (
            c.get("category") == ScanCategory.TEMP_FILES or
            "temp" in c.get("category", "").lower()
        )
    },
    {
        "id": "app_cache",
        "title": "Application Cache",
        "icon": "📦",
        "color": "#2dd4bf",
        "bg_color": "rgba(45, 212, 191, 0.15)",
        "desc": "Discord, Spotify, Electron, and general desktop application local caches.",
        "match": lambda c: (
            c.get("category") == ScanCategory.APP_CACHE or
            "app cache" in c.get("category", "").lower() or
            "application cache" in c.get("category", "").lower()
        )
    },
    {
        "id": "leftovers",
        "title": "Uninstalled App Leftovers",
        "icon": "🧩",
        "color": "#f472b6",
        "bg_color": "rgba(244, 114, 182, 0.15)",
        "desc": "Orphaned AppData configurations and data from uninstalled programs.",
        "match": lambda c: (
            c.get("category") == ScanCategory.LEFTOVERS or
            "leftover" in c.get("category", "").lower()
        )
    },
    {
        "id": "browser_cache",
        "title": "Browser Cache",
        "icon": "🌐",
        "color": "#c084fc",
        "bg_color": "rgba(192, 132, 252, 0.15)",
        "desc": "Chrome, Edge, Firefox, Brave, and Chromium browser disk caches.",
        "match": lambda c: (
            c.get("category") == ScanCategory.BROWSER_CACHE or
            "browser" in c.get("category", "").lower()
        )
    },
    {
        "id": "dev_caches",
        "title": "Python & Node.js Caches",
        "icon": "🐍",
        "color": "#38bdf8",
        "bg_color": "rgba(56, 189, 248, 0.15)",
        "desc": "pip, conda, npm, pnpm, yarn caches, and build artifacts.",
        "match": lambda c: (
            c.get("category") in (ScanCategory.PYTHON_CONDA, ScanCategory.NODE_JS) or
            "python" in c.get("category", "").lower() or
            "node" in c.get("category", "").lower() or
            "conda" in c.get("category", "").lower()
        )
    },
    {
        "id": "ai_models",
        "title": "AI Models & Storage",
        "icon": "🧠",
        "color": "#e879f9",
        "bg_color": "rgba(232, 121, 249, 0.15)",
        "desc": "Ollama local model blobs, Hugging Face hub weights, and LLM stores.",
        "match": lambda c: (
            c.get("category") == ScanCategory.AI_MODELS or
            "ai model" in c.get("category", "").lower() or
            "ollama" in c.get("app_name", "").lower() or
            "huggingface" in c.get("app_name", "").lower()
        )
    },
    {
        "id": "logs_crash",
        "title": "Logs & Crash Reports",
        "icon": "📝",
        "color": "#a5b4fc",
        "bg_color": "rgba(165, 180, 252, 0.15)",
        "desc": "Windows setup logs, CBS diagnostics, and application crash telemetry dumps.",
        "match": lambda c: (
            c.get("category") == ScanCategory.LOGS_CRASH or
            "log" in c.get("category", "").lower() or
            "crash" in c.get("category", "").lower()
        )
    },
    {
        "id": "other_candidates",
        "title": "Other Cleanup Candidates",
        "icon": "🗄️",
        "color": "#34d399",
        "bg_color": "rgba(52, 211, 153, 0.15)",
        "desc": "Recycle Bin files, miscellaneous build outputs, and general candidates.",
        "match": lambda c: (
            c.get("category") in (ScanCategory.RECYCLE_BIN, ScanCategory.BUILD_ARTIFACTS, ScanCategory.GENERAL) or
            "recycle" in c.get("category", "").lower()
        )
    }
]

def fmt_bytes(num_bytes: int) -> str:
    if num_bytes <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


class DeepView(QWidget):
    request_cleanup_view = Signal(str)  # Emits target category or "" to navigate

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_candidates: List[Dict[str, Any]] = []
        self.current_category_id: Optional[str] = None
        self.current_category_items: List[Dict[str, Any]] = []
        self.filtered_detail_items: List[Dict[str, Any]] = []

        self._init_ui()

    def set_candidates(self, candidates: List[Dict[str, Any]]):
        self.all_candidates = candidates
        self._refresh_overview()
        if self.current_category_id:
            self._open_category(self.current_category_id)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # 1. Top Header
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        icon_box = QLabel("📂")
        icon_box.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1d4ed8, stop:1 #2563eb); "
            "border-radius: 8px; font-size: 20px; padding: 6px 9px;"
        )
        header_bar.addWidget(icon_box)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("Deep View")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff; background: transparent; border: none;")
        sub = QLabel("Explore detected storage clutter organized into 10 specialized category buckets.")
        sub.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent; border: none;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_bar.addLayout(title_box)
        header_bar.addStretch()

        self.overview_badge = QLabel("10 Categories • 0 unique items (0 B)")
        self.overview_badge.setStyleSheet(
            "background-color: rgba(37, 99, 235, 0.15); color: #60a5fa; border: 1px solid rgba(37, 99, 235, 0.35); "
            "border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 11.5px;"
        )
        header_bar.addWidget(self.overview_badge)

        main_layout.addLayout(header_bar)

        # 2. Stacked Pages: Index 0 = Categories Overview, Index 1 = Category Details Table
        self.stack = QStackedWidget()
        
        self.page_overview = self._create_overview_page()
        self.page_detail = self._create_detail_page()

        self.stack.addWidget(self.page_overview)  # index 0
        self.stack.addWidget(self.page_detail)    # index 1

        main_layout.addWidget(self.stack, stretch=1)

    # ==========================================
    # PAGE 1: CATEGORIES OVERVIEW GRID
    # ==========================================
    def _create_overview_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        # Scroll Area holding the 10 category cards in a 2-column responsive grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(container)
        self.grid_layout.setContentsMargins(0, 0, 4, 0)
        self.grid_layout.setSpacing(12)

        self.category_cards: Dict[str, Dict[str, Any]] = {}

        for idx, cfg in enumerate(CATEGORIES_CONFIG):
            card, widgets = self._create_category_card(cfg)
            row = idx // 2
            col = idx % 2
            self.grid_layout.addWidget(card, row, col)
            self.category_cards[cfg["id"]] = {
                "config": cfg,
                "card": card,
                "widgets": widgets
            }

        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        return page

    def _create_category_card(self, cfg: Dict[str, Any]) -> tuple[QFrame, Dict[str, QLabel]]:
        card = QFrame()
        card.setObjectName(f"catCard_{cfg['id']}")
        card.setStyleSheet(
            f"#{card.objectName()} {{ background-color: #0d1527; border: 1px solid #1e293b; border-radius: 10px; }} "
            f"#{card.objectName()}:hover {{ border-color: #3b82f6; background-color: #0f1a30; }}"
        )
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setMinimumHeight(110)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        # Top row: Icon + Title + Count/Size Pill
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        icon_lbl = QLabel(cfg["icon"])
        icon_lbl.setFixedSize(38, 38)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"background-color: {cfg['bg_color']}; border-radius: 8px; font-size: 18px; border: none;")
        top_row.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_lbl = QLabel(cfg["title"])
        title_lbl.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #ffffff; background: transparent; border: none;")
        
        count_lbl = QLabel("0 items (0 B)")
        count_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {cfg['color']}; background: transparent; border: none;")
        
        title_box.addWidget(title_lbl)
        title_box.addWidget(count_lbl)
        top_row.addLayout(title_box)
        top_row.addStretch()

        status_pill = QLabel("Not Scanned")
        status_pill.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 4px; "
            "padding: 3px 8px; font-size: 10.5px; font-weight: 600;"
        )
        top_row.addWidget(status_pill)
        card_layout.addLayout(top_row)

        # Middle: Description
        desc_lbl = QLabel(cfg["desc"])
        desc_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; background: transparent; border: none; line-height: 1.3;")
        desc_lbl.setWordWrap(True)
        card_layout.addWidget(desc_lbl)

        # Bottom row: Action button to open details
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        title_escaped = cfg["title"].replace("&", "&&")
        inspect_btn = QPushButton(f"Inspect {title_escaped}  →")
        inspect_btn.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 6px; "
            "padding: 5px 12px; font-size: 11.5px; font-weight: 600; } "
            "QPushButton:hover { background-color: #2563eb; color: #ffffff; border-color: #3b82f6; }"
        )
        inspect_btn.clicked.connect(lambda chk=False, cid=cfg["id"]: self._open_category(cid))
        btn_row.addWidget(inspect_btn)
        card_layout.addLayout(btn_row)

        widgets = {
            "count": count_lbl,
            "status": status_pill,
            "btn": inspect_btn
        }

        return card, widgets

    # ==========================================
    # PAGE 2: CATEGORY DETAIL TABLE VIEW
    # ==========================================
    def _create_detail_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Top Category Banner
        top_banner = QFrame()
        top_banner.setObjectName("detailBanner")
        top_banner.setStyleSheet("#detailBanner { background-color: #0d1527; border: 1px solid #1e293b; border-radius: 8px; }")
        banner_layout = QHBoxLayout(top_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        banner_layout.setSpacing(12)

        # Back Button
        back_btn = QPushButton("‹  Back to All Categories")
        back_btn.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; border: 1px solid #0284c7; border-radius: 6px; "
            "padding: 6px 14px; font-weight: 700; font-size: 12px; } "
            "QPushButton:hover { background-color: #0369a1; color: #ffffff; }"
        )
        back_btn.clicked.connect(self._back_to_overview)
        banner_layout.addWidget(back_btn)

        # Category Title and Stats
        self.detail_icon = QLabel("📁")
        self.detail_icon.setStyleSheet("font-size: 22px; background: transparent; border: none;")
        banner_layout.addWidget(self.detail_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.detail_title = QLabel("Category Name")
        self.detail_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff; background: transparent; border: none;")
        self.detail_desc = QLabel("Category description goes here")
        self.detail_desc.setStyleSheet("font-size: 11px; color: #94a3b8; background: transparent; border: none;")
        title_box.addWidget(self.detail_title)
        title_box.addWidget(self.detail_desc)
        banner_layout.addLayout(title_box)

        banner_layout.addStretch()

        self.detail_stats_pill = QLabel("0 items (0 B)")
        self.detail_stats_pill.setStyleSheet(
            "background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.35); "
            "border-radius: 6px; padding: 5px 12px; font-weight: 700; font-size: 11.5px;"
        )
        banner_layout.addWidget(self.detail_stats_pill)

        open_cleanup_btn = QPushButton("🛡️  Open in Cleanup Center")
        open_cleanup_btn.setStyleSheet(
            "QPushButton { background-color: #16a34a; color: #ffffff; border: 1px solid #22c55e; border-radius: 6px; "
            "padding: 6px 14px; font-weight: 700; font-size: 11.5px; } "
            "QPushButton:hover { background-color: #15803d; }"
        )
        open_cleanup_btn.clicked.connect(self._on_open_cleanup_clicked)
        banner_layout.addWidget(open_cleanup_btn)

        layout.addWidget(top_banner)

        # Filter & Search bar for this category
        filter_card = QFrame()
        filter_card.setObjectName("detailFilterCard")
        filter_card.setStyleSheet("#detailFilterCard { background-color: #0d1527; border: 1px solid #1e293b; border-radius: 8px; }")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(12, 6, 12, 6)
        filter_layout.setSpacing(12)

        self.detail_search = QLineEdit()
        self.detail_search.setPlaceholderText("🔍  Search within this category...")
        self.detail_search.textChanged.connect(self._apply_detail_filters)
        self.detail_search.setStyleSheet("background-color: #070b14; border: 1px solid #1e293b; border-radius: 6px; padding: 5px 10px; font-size: 12px; color: #ffffff;")
        filter_layout.addWidget(self.detail_search, stretch=1)

        tier_lbl = QLabel("Safety:")
        tier_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 600; background: transparent; border: none;")
        filter_layout.addWidget(tier_lbl)

        self.detail_tier_combo = QComboBox()
        self.detail_tier_combo.addItems(["All Tiers", "SAFE", "CAUTION", "RISKY"])
        self.detail_tier_combo.currentTextChanged.connect(self._apply_detail_filters)
        self.detail_tier_combo.setFixedWidth(105)
        self.detail_tier_combo.setStyleSheet("QComboBox { background-color: #070b14; border: 1px solid #1e293b; border-radius: 6px; padding: 4px 8px; font-size: 11.5px; }")
        filter_layout.addWidget(self.detail_tier_combo)

        sort_lbl = QLabel("Sort:")
        sort_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 600; background: transparent; border: none;")
        filter_layout.addWidget(sort_lbl)

        self.detail_sort_combo = QComboBox()
        self.detail_sort_combo.addItems(["Size (Largest)", "Size (Smallest)", "Path (A-Z)", "Safety Tier"])
        self.detail_sort_combo.currentTextChanged.connect(self._apply_detail_filters)
        self.detail_sort_combo.setFixedWidth(135)
        self.detail_sort_combo.setStyleSheet("QComboBox { background-color: #070b14; border: 1px solid #1e293b; border-radius: 6px; padding: 4px 8px; font-size: 11.5px; }")
        filter_layout.addWidget(self.detail_sort_combo)

        layout.addWidget(filter_card)

        # Table for Category Items
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(7)
        self.detail_table.setHorizontalHeaderLabels([
            "ITEM / NAME", "SIZE", "APP / OWNER", "DETECTION REASON", "CONFIDENCE", "SAFETY TIER", "RECOMMENDED ACTION"
        ])

        self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.detail_table.setColumnWidth(1, 80)
        self.detail_table.setColumnWidth(2, 95)
        self.detail_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.detail_table.setColumnWidth(4, 76)
        self.detail_table.setColumnWidth(5, 76)
        self.detail_table.setColumnWidth(6, 126)

        self.detail_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.detail_table.verticalHeader().setDefaultSectionSize(46)
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setStyleSheet(
            "QTableWidget { background-color: #070b14; alternate-background-color: #0a101f; border: 1px solid #1e293b; border-radius: 8px; } "
            "QTableWidget::item { padding: 0px 4px; border-bottom: 1px solid #131d31; } "
            "QTableWidget::item:selected { background-color: rgba(30, 58, 138, 0.45); }"
        )
        self.detail_table.itemClicked.connect(self._on_detail_row_clicked)
        layout.addWidget(self.detail_table, stretch=1)

        # Bottom Inspector Strip for selected item in detail view
        self.inspector_strip = QFrame()
        self.inspector_strip.setObjectName("inspStrip")
        self.inspector_strip.setStyleSheet("#inspStrip { background-color: #0d1527; border: 1px solid #1e293b; border-radius: 8px; }")
        strip_layout = QHBoxLayout(self.inspector_strip)
        strip_layout.setContentsMargins(12, 8, 12, 8)
        strip_layout.setSpacing(10)

        strip_icon = QLabel("📍")
        strip_icon.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        strip_layout.addWidget(strip_icon)

        strip_info_box = QVBoxLayout()
        strip_info_box.setSpacing(1)
        self.strip_path = QLabel("Select an item above to inspect full path and details")
        self.strip_path.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #ffffff; background: transparent; border: none;")
        self.strip_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        self.strip_explanation = QLabel("Click any row in the table")
        self.strip_explanation.setStyleSheet("font-size: 10.5px; color: #94a3b8; background: transparent; border: none;")
        
        strip_info_box.addWidget(self.strip_path)
        strip_info_box.addWidget(self.strip_explanation)
        strip_layout.addLayout(strip_info_box, stretch=1)

        open_folder_btn = QPushButton("📂 Open Folder")
        open_folder_btn.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 6px; "
            "padding: 5px 12px; font-size: 11.5px; font-weight: 600; } "
            "QPushButton:hover { background-color: #334155; color: #ffffff; }"
        )
        open_folder_btn.clicked.connect(self._open_selected_in_explorer)
        strip_layout.addWidget(open_folder_btn)

        layout.addWidget(self.inspector_strip)

        return page

    # ==========================================
    # LOGIC & DATA REFRESH
    # ==========================================
    def _refresh_overview(self):
        # Calculate unique items and size across all candidates (prevent double counting)
        unique_map = {c.get("path"): c for c in self.all_candidates if c.get("path")}
        unique_cnt = len(unique_map)
        unique_bytes = sum(c.get("size", 0) for c in unique_map.values())

        if unique_cnt > 0:
            self.overview_badge.setText(f"✓ 10 Categories Analyzed • {unique_cnt:,} unique items ({fmt_bytes(unique_bytes)})")
            self.overview_badge.setStyleSheet(
                "background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.35); "
                "border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 11.5px;"
            )
        else:
            self.overview_badge.setText("10 Categories • No items detected / Scan required")
            self.overview_badge.setStyleSheet(
                "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; "
                "border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 11.5px;"
            )

        for cfg in CATEGORIES_CONFIG:
            matching_items = [c for c in self.all_candidates if cfg["match"](c)]
            card_info = self.category_cards.get(cfg["id"])
            if not card_info:
                continue

            cnt = len(matching_items)
            tot_b = sum(c.get("size", 0) for c in matching_items)
            
            card_info["widgets"]["count"].setText(f"{cnt:,} items ({fmt_bytes(tot_b)})")
            
            title_escaped = cfg["title"].replace("&", "&&")
            if cnt > 0:
                card_info["widgets"]["status"].setText(f"{cnt} detected")
                card_info["widgets"]["status"].setStyleSheet(
                    "background-color: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); "
                    "border-radius: 4px; padding: 3px 8px; font-size: 10.5px; font-weight: 700;"
                )
                card_info["widgets"]["btn"].setText(f"Inspect {title_escaped} ({cnt})  →")
            else:
                card_info["widgets"]["status"].setText("Clean / 0 detected" if self.all_candidates else "Not Scanned")
                card_info["widgets"]["status"].setStyleSheet(
                    "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 4px; "
                    "padding: 3px 8px; font-size: 10.5px; font-weight: 600;"
                )
                card_info["widgets"]["btn"].setText(f"Inspect {title_escaped}  →")

    def _open_category(self, cat_id: str):
        cfg = next((c for c in CATEGORIES_CONFIG if c["id"] == cat_id), None)
        if not cfg:
            return

        self.current_category_id = cat_id
        self.current_category_items = [c for c in self.all_candidates if cfg["match"](c)]

        self.detail_icon.setText(cfg["icon"])
        self.detail_title.setText(f"{cfg['title']} ({len(self.current_category_items)} items)")
        self.detail_desc.setText(cfg["desc"])
        
        tot_b = sum(c.get("size", 0) for c in self.current_category_items)
        self.detail_stats_pill.setText(f"{len(self.current_category_items):,} items • {fmt_bytes(tot_b)}")

        self.detail_search.blockSignals(True)
        self.detail_search.clear()
        self.detail_search.blockSignals(False)

        self._apply_detail_filters()
        self.stack.setCurrentIndex(1)

    def _back_to_overview(self):
        self.current_category_id = None
        self.stack.setCurrentIndex(0)

    def _apply_detail_filters(self):
        query = self.detail_search.text().lower().strip()
        tier_filter = self.detail_tier_combo.currentText()
        sort_mode = self.detail_sort_combo.currentText()

        filtered = []
        for c in self.current_category_items:
            if tier_filter != "All Tiers" and c.get("safety_tier") != tier_filter:
                continue
            if query:
                p_str = c.get("path", "").lower()
                app_str = c.get("app_name", "").lower()
                exp_str = c.get("explanation", "").lower()
                if query not in p_str and query not in app_str and query not in exp_str:
                    continue
            filtered.append(c)

        # Sorting
        if sort_mode == "Size (Largest)":
            filtered.sort(key=lambda x: x.get("size", 0), reverse=True)
        elif sort_mode == "Size (Smallest)":
            filtered.sort(key=lambda x: x.get("size", 0))
        elif sort_mode == "Path (A-Z)":
            filtered.sort(key=lambda x: x.get("path", "").lower())
        elif sort_mode == "Safety Tier":
            tier_order = {"SAFE": 0, "CAUTION": 1, "RISKY": 2, "PROTECTED": 3}
            filtered.sort(key=lambda x: tier_order.get(x.get("safety_tier", "CAUTION"), 9))

        self.filtered_detail_items = filtered
        self._render_detail_table()

    def _render_detail_table(self):
        self.detail_table.clearContents()
        self.detail_table.setRowCount(0)
        self.detail_table.setRowCount(len(self.filtered_detail_items))


        for row, item in enumerate(self.filtered_detail_items):
            path_str = item.get("path", "")
            name = Path(path_str).name if path_str else "Unknown"

            # 0. ITEM / NAME (Icon + filename / path)
            item_w = QWidget()
            item_w.setStyleSheet("background: transparent; border: none;")
            i_l = QHBoxLayout(item_w)
            i_l.setContentsMargins(6, 2, 6, 2)
            i_l.setSpacing(8)

            icon_lbl = QLabel("📄" if not item.get("is_dir") else "📁")
            icon_lbl.setStyleSheet("font-size: 16px; background: transparent; border: none;")
            i_l.addWidget(icon_lbl)

            col = QVBoxLayout()
            col.setSpacing(1)
            name_lbl = QLabel(name or path_str)
            name_lbl.setStyleSheet("font-weight: 700; color: #ffffff; font-size: 11.5px; background: transparent; border: none;")
            name_lbl.setToolTip(path_str)

            path_sub = QLabel(path_str)
            path_sub.setStyleSheet("font-size: 10.5px; color: #94a3b8; background: transparent; border: none;")
            path_sub.setToolTip(path_str)

            col.addWidget(name_lbl)
            col.addWidget(path_sub)
            i_l.addLayout(col, stretch=1)
            self.detail_table.setCellWidget(row, 0, item_w)

            # 1. SIZE
            s_item = QTableWidgetItem(fmt_bytes(item.get("size", 0)))
            s_item.setTextAlignment(Qt.AlignCenter)
            s_item.setForeground(Qt.white)
            self.detail_table.setItem(row, 1, s_item)

            # 2. APP / OWNER
            app_item = QTableWidgetItem(item.get("app_name", "System"))
            app_item.setTextAlignment(Qt.AlignCenter)
            app_item.setForeground(Qt.white)
            self.detail_table.setItem(row, 2, app_item)

            # 3. DETECTION REASON
            reason_text = item.get("explanation", "").split(".")[0] or item.get("category", "")
            r_item = QTableWidgetItem(reason_text)
            r_item.setForeground(Qt.white)
            r_item.setToolTip(item.get("explanation", ""))
            self.detail_table.setItem(row, 3, r_item)

            # 4. CONFIDENCE (Pill)
            conf = item.get("confidence", "Medium")
            conf_pill = QLabel(conf)
            if conf == "High":
                conf_pill.setStyleSheet("background-color: #064e3b; color: #4ade80; border: 1px solid #059669; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10px;")
            elif conf == "Medium":
                conf_pill.setStyleSheet("background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10px;")
            else:
                conf_pill.setStyleSheet("background-color: #082f49; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10px;")
            conf_pill.setAlignment(Qt.AlignCenter)
            c_w = QWidget()
            c_w.setStyleSheet("background: transparent; border: none;")
            c_l = QHBoxLayout(c_w)
            c_l.addWidget(conf_pill)
            c_l.setAlignment(Qt.AlignCenter)
            c_l.setContentsMargins(0, 0, 0, 0)
            self.detail_table.setCellWidget(row, 4, c_w)

            # 5. SAFETY TIER (Pill)
            tier = item.get("safety_tier", "CAUTION")
            tier_label = "Low" if tier == "SAFE" else ("Medium" if tier == "CAUTION" else "High")
            tier_pill = QLabel(tier_label)
            if tier == "SAFE":
                tier_pill.setStyleSheet("background-color: #064e3b; color: #4ade80; border: 1px solid #059669; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10px;")
            elif tier == "CAUTION":
                tier_pill.setStyleSheet("background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10px;")
            else:
                tier_pill.setStyleSheet("background-color: #4c0519; color: #f87171; border: 1px solid #e11d48; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10px;")
            tier_pill.setAlignment(Qt.AlignCenter)
            t_w = QWidget()
            t_w.setStyleSheet("background: transparent; border: none;")
            t_l = QHBoxLayout(t_w)
            t_l.addWidget(tier_pill)
            t_l.setAlignment(Qt.AlignCenter)
            t_l.setContentsMargins(0, 0, 0, 0)
            self.detail_table.setCellWidget(row, 5, t_w)

            # 6. RECOMMENDED ACTION (Pill)
            act_text = "> Clean" if tier == "SAFE" else "↻ Review"
            act_pill = QLabel(act_text)
            if tier == "SAFE":
                act_pill.setStyleSheet("background-color: #064e3b; color: #4ade80; border: 1px solid #16a34a; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10.5px;")
            else:
                act_pill.setStyleSheet("background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10.5px;")
            act_pill.setAlignment(Qt.AlignCenter)
            a_w = QWidget()
            a_w.setStyleSheet("background: transparent; border: none;")
            a_l = QHBoxLayout(a_w)
            a_l.addWidget(act_pill)
            a_l.setAlignment(Qt.AlignCenter)
            a_l.setContentsMargins(0, 0, 0, 0)
            self.detail_table.setCellWidget(row, 6, a_w)

        if self.filtered_detail_items:
            self._select_detail_item(self.filtered_detail_items[0])

    def _on_detail_row_clicked(self, item):
        row = self.detail_table.currentRow()
        if 0 <= row < len(self.filtered_detail_items):
            self._select_detail_item(self.filtered_detail_items[row])

    def _select_detail_item(self, item: Dict[str, Any]):
        path = item.get("path", "")
        self.strip_path.setText(path)
        exp = item.get("explanation", "Detected clutter.")
        conseq = item.get("consequences", "")
        self.strip_explanation.setText(f"{exp} • {conseq}" if conseq else exp)

    def _open_selected_in_explorer(self):
        path = self.strip_path.text()
        if path and os.path.exists(path):
            try:
                subprocess.Popen(f'explorer /select,"{path}"')
            except Exception:
                pass

    def _on_open_cleanup_clicked(self):
        # Emits signal to main window to open cleanup center
        self.request_cleanup_view.emit("cleanup")
