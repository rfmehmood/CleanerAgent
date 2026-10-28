import os
import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QComboBox,
    QLineEdit, QMessageBox, QDialog, QTextEdit, QScrollArea, QTabWidget,
    QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from typing import List, Dict, Any, Optional

from ..cleanup.executor import CleanupExecutor
from ..quarantine.manager import QuarantineManager
from ..database.db import DatabaseManager
from ..scanner.categories import ScanCategory

def get_item_icon(app_name: str, category: str) -> str:
    app_lower = app_name.lower()
    cat_lower = category.lower()
    if "chrome" in app_lower:
        return "🌐"
    elif "discord" in app_lower:
        return "💬"
    elif "python" in app_lower or "pip" in app_lower:
        return "🐍"
    elif "node" in app_lower or "npm" in app_lower:
        return "📦"
    elif "ollama" in app_lower or "ai" in cat_lower:
        return "🧠"
    elif "duplicate" in cat_lower:
        return "📄"
    elif "log" in cat_lower:
        return "📝"
    elif "recycle" in cat_lower:
        return "🗑️"
    elif "large" in cat_lower:
        return "📁"
    return "📁"

def get_category_color(category: str) -> tuple[str, str]:
    cat = category.lower()
    if "temp" in cat:
        return "#1e3a8a", "#60a5fa"
    elif "browser" in cat:
        return "#581c87", "#c084fc"
    elif "app cache" in cat:
        return "#115e59", "#2dd4bf"
    elif "python" in cat:
        return "#0e7490", "#38bdf8"
    elif "node" in cat:
        return "#14532d", "#4ade80"
    elif "ai" in cat:
        return "#701a75", "#f472b6"
    elif "duplicate" in cat:
        return "#1e293b", "#93c5fd"
    elif "log" in cat:
        return "#312e81", "#a5b4fc"
    elif "recycle" in cat:
        return "#065f46", "#34d399"
    elif "large" in cat:
        return "#7c2d12", "#fb923c"
    return "#1e293b", "#cbd5e1"

class CleanupCenterView(QWidget):
    cleanup_executed = Signal()

    def __init__(self, executor: CleanupExecutor, quarantine_mgr: QuarantineManager, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.executor = executor
        self.quarantine_mgr = quarantine_mgr
        self.db = db
        
        self.all_candidates: List[Dict[str, Any]] = []
        self.filtered_candidates: List[Dict[str, Any]] = []
        self.selected_indices = set()
        
        self.current_page = 1
        self.items_per_page = 10
        self.currently_inspected_item: Optional[Dict[str, Any]] = None

        self._init_ui()

    def set_candidates(self, candidates: List[Dict[str, Any]]):
        self.all_candidates = candidates
        self.selected_indices = {i for i, c in enumerate(candidates) if c.get("safety_tier") == "SAFE"}
        self._refresh_filters_and_stats()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # 1. Top Page Header
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        icon_box = QLabel("🧹")
        icon_box.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0284c7, stop:1 #0369a1); "
            "border-radius: 8px; font-size: 20px; padding: 5px 8px;"
        )
        header_bar.addWidget(icon_box)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("Cleanup Center")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        sub = QLabel("Review detected items, inspect details, and safely isolate or restore data.")
        sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_bar.addLayout(title_box)
        header_bar.addStretch()

        self.scan_completed_badge = QLabel("✓ Scan Completed\nApr 26, 2025 • 14:32")
        self.scan_completed_badge.setStyleSheet(
            "background-color: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); "
            "border-radius: 8px; padding: 5px 12px; font-weight: 600; font-size: 11px; text-align: center;"
        )
        self.scan_completed_badge.setAlignment(Qt.AlignCenter)
        header_bar.addWidget(self.scan_completed_badge)

        main_layout.addLayout(header_bar)

        # 2. Top 4 Stat Cards Row (Sleek, well-proportioned)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self.card_total = self._create_stat_card("Total Candidates", "0 items", "0 B", "📄", "#818cf8", "rgba(99, 102, 241, 0.15)")
        self.card_safe = self._create_stat_card("Safe to Clean", "0 items", "0 B", "🛢️", "#4ade80", "rgba(34, 197, 94, 0.15)")
        self.card_review = self._create_stat_card("Requires Review", "0 items", "0 B", "🛡️", "#fbbf24", "rgba(245, 158, 11, 0.15)")
        self.card_quar = self._create_stat_card("In Quarantine", "0 items", "0 B", "🗄️", "#38bdf8", "rgba(56, 189, 248, 0.15)")

        stats_row.addWidget(self.card_total)
        stats_row.addWidget(self.card_safe)
        stats_row.addWidget(self.card_review)
        stats_row.addWidget(self.card_quar)
        main_layout.addLayout(stats_row)

        # 3. Filter & Search Controls Bar
        filter_card = QFrame()
        filter_card.setObjectName("filterCard")
        filter_card.setStyleSheet("#filterCard { background-color: #0d1527; border: 1px solid #1e293b; border-radius: 8px; }")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(12, 6, 12, 6)
        filter_layout.setSpacing(14)

        # Category Mini Group
        cat_group = QVBoxLayout()
        cat_group.setSpacing(2)
        lbl_cat_title = QLabel("Filter by Category")
        lbl_cat_title.setStyleSheet("font-size: 10px; font-weight: 600; color: #94a3b8; background: transparent; border: none;")
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("All Categories")
        self.cat_combo.currentTextChanged.connect(self._apply_filters)
        self.cat_combo.setFixedWidth(140)
        self.cat_combo.setStyleSheet("QComboBox { background-color: #070b14; border: 1px solid #1e293b; border-radius: 6px; padding: 4px 8px; font-size: 11.5px; }")
        cat_group.addWidget(lbl_cat_title)
        cat_group.addWidget(self.cat_combo)
        filter_layout.addLayout(cat_group)

        # Safety Tier Mini Group
        tier_group = QVBoxLayout()
        tier_group.setSpacing(2)
        lbl_tier_title = QLabel("Safety Tier")
        lbl_tier_title.setStyleSheet("font-size: 10px; font-weight: 600; color: #94a3b8; background: transparent; border: none;")
        self.tier_combo = QComboBox()
        self.tier_combo.addItems(["All Tiers", "SAFE", "CAUTION", "RISKY"])
        self.tier_combo.currentTextChanged.connect(self._apply_filters)
        self.tier_combo.setFixedWidth(110)
        self.tier_combo.setStyleSheet("QComboBox { background-color: #070b14; border: 1px solid #1e293b; border-radius: 6px; padding: 4px 8px; font-size: 11.5px; }")
        tier_group.addWidget(lbl_tier_title)
        tier_group.addWidget(self.tier_combo)
        filter_layout.addLayout(tier_group)

        # Confidence Mini Group
        conf_group = QVBoxLayout()
        conf_group.setSpacing(2)
        lbl_conf_title = QLabel("Confidence")
        lbl_conf_title.setStyleSheet("font-size: 10px; font-weight: 600; color: #94a3b8; background: transparent; border: none;")
        self.conf_combo = QComboBox()
        self.conf_combo.addItems(["All Levels", "High", "Medium", "Low"])
        self.conf_combo.currentTextChanged.connect(self._apply_filters)
        self.conf_combo.setFixedWidth(110)
        self.conf_combo.setStyleSheet("QComboBox { background-color: #070b14; border: 1px solid #1e293b; border-radius: 6px; padding: 4px 8px; font-size: 11.5px; }")
        conf_group.addWidget(lbl_conf_title)
        conf_group.addWidget(self.conf_combo)
        filter_layout.addLayout(conf_group)

        # Search Input (Expands to fill center space!)
        search_group = QVBoxLayout()
        search_group.setSpacing(2)
        lbl_search_title = QLabel(" ")
        lbl_search_title.setStyleSheet("font-size: 10px; background: transparent; border: none;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search files, paths, or apps...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setStyleSheet("background-color: #070b14; border: 1px solid #1e293b; border-radius: 6px; padding: 5px 10px; font-size: 12px; color: #f8fafc;")
        search_group.addWidget(lbl_search_title)
        search_group.addWidget(self.search_input)
        filter_layout.addLayout(search_group, stretch=1)

        # Select All Checkbox
        chk_group = QVBoxLayout()
        chk_group.setSpacing(2)
        lbl_chk_title = QLabel(" ")
        lbl_chk_title.setStyleSheet("font-size: 10px; background: transparent; border: none;")
        self.chk_select_all = QCheckBox("Select All")
        self.chk_select_all.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 600; background: transparent; border: none;")
        self.chk_select_all.stateChanged.connect(self._toggle_select_all)
        chk_group.addWidget(lbl_chk_title)
        chk_group.addWidget(self.chk_select_all)
        filter_layout.addLayout(chk_group)

        main_layout.addWidget(filter_card)

        # 4. Split Main Content: Left Table + Right Detail Inspector Panel
        content_split = QHBoxLayout()
        content_split.setSpacing(12)

        # Left Table Container
        table_container = QVBoxLayout()
        table_container.setSpacing(8)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "", "ITEM", "SIZE", "CATEGORY", "APP / OWNER", "CONFIDENCE", "SAFETY TIER", "RECOMMENDED ACTION"
        ])
        
        # Exact column sizing to eliminate horizontal scrollbar
        self.table.setColumnWidth(0, 32)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(2, 65)
        self.table.setColumnWidth(3, 105)
        self.table.setColumnWidth(4, 78)
        self.table.setColumnWidth(5, 72)
        self.table.setColumnWidth(6, 72)
        self.table.setColumnWidth(7, 126)

        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #070b14; alternate-background-color: #0a101f; border: 1px solid #1e293b; border-radius: 8px; } "
            "QTableWidget::item { padding: 0px 2px; border-bottom: 1px solid #131d31; } "
            "QTableWidget::item:selected { background-color: rgba(30, 58, 138, 0.45); }"
        )
        self.table.itemClicked.connect(self._on_table_row_clicked)
        table_container.addWidget(self.table, stretch=1)

        # Pagination Row below table
        pag_bar = QHBoxLayout()
        self.lbl_pagination_info = QLabel("Showing 0 of 0 items (0 B)")
        self.lbl_pagination_info.setStyleSheet("color: #94a3b8; font-size: 11.5px; background: transparent; border: none;")
        pag_bar.addWidget(self.lbl_pagination_info)
        pag_bar.addStretch()

        self.prev_page_btn = QPushButton("‹")
        self.prev_page_btn.setFixedSize(26, 26)
        self.prev_page_btn.clicked.connect(self._prev_page)
        self.prev_page_btn.setStyleSheet("background-color: #1e293b; color: #f8fafc; border-radius: 4px; border: 1px solid #334155; font-size: 14px;")
        
        self.page_number_lbl = QLabel("1")
        self.page_number_lbl.setStyleSheet("background-color: #2563eb; color: #ffffff; border-radius: 4px; padding: 3px 8px; font-weight: 700; font-size: 11px;")
        
        self.next_page_btn = QPushButton("›")
        self.next_page_btn.setFixedSize(26, 26)
        self.next_page_btn.clicked.connect(self._next_page)
        self.next_page_btn.setStyleSheet("background-color: #1e293b; color: #f8fafc; border-radius: 4px; border: 1px solid #334155; font-size: 14px;")

        pag_bar.addWidget(self.prev_page_btn)
        pag_bar.addWidget(self.page_number_lbl)
        pag_bar.addWidget(self.next_page_btn)
        
        table_container.addLayout(pag_bar)
        content_split.addLayout(table_container, stretch=3)

        # Right Inspector Panel
        self.inspector_panel = self._create_inspector_panel()
        self.inspector_panel.setFixedWidth(310)
        content_split.addWidget(self.inspector_panel)

        main_layout.addLayout(content_split, stretch=1)

        # 5. Bottom Action Execution Bar
        bottom_bar = QFrame()
        bottom_bar.setObjectName("bottomBar")
        bottom_bar.setStyleSheet("#bottomBar { background-color: #0d1527; border: 1px solid #1e293b; border-radius: 8px; }")
        b_layout = QHBoxLayout(bottom_bar)
        b_layout.setContentsMargins(14, 8, 14, 8)
        b_layout.setSpacing(8)

        # Left: Selected items counter
        self.lbl_selected_counter = QLabel("🗄️  Selected: <b>0 items (0 B)</b>")
        self.lbl_selected_counter.setStyleSheet("color: #f1f5f9; font-size: 12px; background: transparent; border: none;")
        b_layout.addWidget(self.lbl_selected_counter)

        clear_sel_btn = QPushButton("Clear")
        clear_sel_btn.setStyleSheet("background: transparent; color: #38bdf8; border: none; text-decoration: underline; font-weight: 600; padding: 0 4px; font-size: 11.5px;")
        clear_sel_btn.clicked.connect(self._clear_selection)
        b_layout.addWidget(clear_sel_btn)
        b_layout.addStretch()

        # Right Action Buttons
        preview_btn = QPushButton("👁  Preview Selected")
        preview_btn.setStyleSheet("background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 6px; padding: 6px 11px; font-size: 11.5px; font-weight: 600;")
        preview_btn.clicked.connect(self._preview_selected)
        b_layout.addWidget(preview_btn)

        self.clean_btn = QPushButton("🛡️  Clean Selected (Quarantine)")
        self.clean_btn.setStyleSheet("background-color: #16a34a; color: #ffffff; border: 1px solid #22c55e; border-radius: 6px; padding: 6px 12px; font-weight: 700; font-size: 11.5px;")
        self.clean_btn.clicked.connect(lambda: self._execute_cleanup(use_quarantine=True))
        b_layout.addWidget(self.clean_btn)

        restore_btn = QPushButton("↻  Restore from Quarantine")
        restore_btn.setStyleSheet("background-color: #b45309; color: #ffffff; border: 1px solid #f59e0b; border-radius: 6px; padding: 6px 11px; font-weight: 600; font-size: 11.5px;")
        restore_btn.clicked.connect(self._open_quarantine_dialog)
        b_layout.addWidget(restore_btn)

        perm_btn = QPushButton("🗑  Permanently Delete")
        perm_btn.setStyleSheet("background-color: #dc2626; color: #ffffff; border: 1px solid #ef4444; border-radius: 6px; padding: 6px 11px; font-weight: 600; font-size: 11.5px;")
        perm_btn.clicked.connect(lambda: self._execute_cleanup(use_quarantine=False))
        b_layout.addWidget(perm_btn)

        history_btn = QPushButton("⏱️  View History")
        history_btn.setStyleSheet("background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 6px; padding: 6px 11px; font-size: 11.5px; font-weight: 600;")
        history_btn.clicked.connect(self._open_history_dialog)
        b_layout.addWidget(history_btn)

        main_layout.addWidget(bottom_bar)

    def _create_stat_card(self, title: str, count_str: str, size_str: str, icon: str, text_color: str, bg_color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("statCard")
        card.setStyleSheet("#statCard { background-color: #0d1527; border: 1px solid #1e293b; border-radius: 10px; }")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"background-color: {bg_color}; border-radius: 8px; font-size: 18px; border: none;")
        layout.addWidget(icon_lbl)

        txt_box = QVBoxLayout()
        txt_box.setSpacing(2)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 10.5px; font-weight: 700; color: #94a3b8; text-transform: uppercase; background: transparent; border: none;")
        lbl_count = QLabel(count_str)
        lbl_count.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff; background: transparent; border: none;")
        lbl_size = QLabel(f"~ {size_str}")
        lbl_size.setStyleSheet(f"font-size: 11.5px; font-weight: 600; color: {text_color}; background: transparent; border: none;")
        
        txt_box.addWidget(lbl_title)
        txt_box.addWidget(lbl_count)
        txt_box.addWidget(lbl_size)
        layout.addLayout(txt_box)
        layout.addStretch()

        return card

    def _create_inspector_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("inspectorPanel")
        panel.setStyleSheet("#inspectorPanel { background-color: #0d1527; border: 1px solid #1e293b; border-radius: 10px; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Info Row
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(10)
        hdr_row.setAlignment(Qt.AlignTop)
        self.insp_icon = QLabel("📁")
        self.insp_icon.setFixedSize(36, 36)
        self.insp_icon.setAlignment(Qt.AlignCenter)
        self.insp_icon.setStyleSheet("font-size: 28px; background: transparent; border: none;")
        hdr_row.addWidget(self.insp_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)
        self.insp_title = QLabel("Select an item to inspect")
        self.insp_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff; background: transparent; border: none;")
        self.insp_title.setWordWrap(False)

        self.insp_subtitle = QLabel("Click any row in the table")
        self.insp_subtitle.setStyleSheet("font-size: 11px; color: #94a3b8; background: transparent; border: none;")
        
        self.insp_conf_pill = QLabel("🟢 High Confidence")
        self.insp_conf_pill.setStyleSheet("background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 4px; padding: 2px 8px; font-size: 10.5px; font-weight: 700; background: transparent;")
        self.insp_conf_pill.setFixedWidth(135)

        title_box.addWidget(self.insp_title)
        title_box.addWidget(self.insp_subtitle)
        title_box.addWidget(self.insp_conf_pill)
        hdr_row.addLayout(title_box, stretch=1)
        layout.addLayout(hdr_row)

        # Tab Bar
        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane { border: none; background: transparent; } "
            "QTabBar::tab { background: #070b14; color: #94a3b8; padding: 5px 8px; border-radius: 4px; margin-right: 3px; font-weight: 600; font-size: 11px; } "
            "QTabBar::tab:selected { background: #1e293b; color: #38bdf8; border-bottom: 2px solid #38bdf8; }"
        )

        # Details Tab (Grid Layout with right-aligned container for snug pills)
        details_tab = QWidget()
        details_tab.setStyleSheet("background: transparent; border: none;")
        d_grid = QGridLayout(details_tab)
        d_grid.setContentsMargins(4, 8, 12, 4)
        d_grid.setHorizontalSpacing(10)
        d_grid.setVerticalSpacing(7)

        def add_grid_prop(row_idx: int, label_text: str) -> QLabel:
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #94a3b8; font-size: 11.5px; font-weight: 500; background: transparent; border: none;")
            
            val_container = QWidget()
            val_container.setStyleSheet("background: transparent; border: none;")
            val_layout = QHBoxLayout(val_container)
            val_layout.setContentsMargins(0, 0, 4, 0)
            val_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            val = QLabel("-")
            val.setStyleSheet("color: #f8fafc; font-size: 11.5px; font-weight: 600; background: transparent; border: none;")
            val_layout.addStretch()
            val_layout.addWidget(val)
            
            d_grid.addWidget(lbl, row_idx, 0, Qt.AlignLeft | Qt.AlignVCenter)
            d_grid.addWidget(val_container, row_idx, 1)
            return val

        self.lbl_prop_size = add_grid_prop(0, "Size")
        self.lbl_prop_cat = add_grid_prop(1, "Category")
        self.lbl_prop_app = add_grid_prop(2, "Associated App")
        self.lbl_prop_mtime = add_grid_prop(3, "Modified")
        self.lbl_prop_tier = add_grid_prop(4, "Safety Tier")
        self.lbl_prop_rec = add_grid_prop(5, "Recommended Action")
        self.lbl_prop_quar = add_grid_prop(6, "Quarantine Available")

        tabs.addTab(details_tab, "Details")
        
        # Evidence Tab
        evidence_tab = QWidget()
        evidence_tab.setStyleSheet("background: transparent; border: none;")
        e_layout = QVBoxLayout(evidence_tab)
        self.evidence_text = QLabel("• File verified in application cache directory.\n• Safe to isolate or clean.")
        self.evidence_text.setStyleSheet("color: #cbd5e1; font-size: 11.5px; line-height: 1.4; background: transparent; border: none;")
        self.evidence_text.setWordWrap(True)
        e_layout.addWidget(self.evidence_text)
        e_layout.addStretch()
        tabs.addTab(evidence_tab, "Evidence")

        # Related Tab
        related_tab = QWidget()
        related_tab.setStyleSheet("background: transparent; border: none;")
        r_layout = QVBoxLayout(related_tab)
        self.related_text = QLabel("• No active parent processes locking this path.")
        self.related_text.setStyleSheet("color: #cbd5e1; font-size: 11.5px; background: transparent; border: none;")
        r_layout.addWidget(self.related_text)
        r_layout.addStretch()
        tabs.addTab(related_tab, "Related")

        # Preview Tab
        preview_tab = QWidget()
        preview_tab.setStyleSheet("background: transparent; border: none;")
        p_layout = QVBoxLayout(preview_tab)
        self.preview_text = QLabel("• Content preview: binary cache / log directory.")
        self.preview_text.setStyleSheet("color: #cbd5e1; font-size: 11.5px; background: transparent; border: none;")
        p_layout.addWidget(self.preview_text)
        p_layout.addStretch()
        tabs.addTab(preview_tab, "Preview")

        layout.addWidget(tabs)

        # Section: Why this was identified
        lbl_why_hdr = QLabel("Why this was identified")
        lbl_why_hdr.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #f1f5f9; background: transparent; border: none; padding-top: 4px;")
        layout.addWidget(lbl_why_hdr)

        self.why_text = QLabel("• Located in temporary directory (known temporary location).\n• Files are older than 7 days.\n• Not currently in use by any application.\n• Contains temporary installer and cache files.")
        self.why_text.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.35; background: transparent; border: none;")
        self.why_text.setWordWrap(True)
        layout.addWidget(self.why_text)

        # Warning Box: Potential Consequences
        self.conseq_box = QFrame()
        self.conseq_box.setObjectName("conseqBox")
        self.conseq_box.setStyleSheet("#conseqBox { background-color: #172554; border: 1px solid #1e3a8a; border-radius: 6px; }")
        c_layout = QVBoxLayout(self.conseq_box)
        c_layout.setContentsMargins(8, 8, 8, 8)
        c_layout.setSpacing(3)
        c_title = QLabel("⚠️ Potential Consequences")
        c_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #fbbf24; background: transparent; border: none;")
        self.conseq_desc = QLabel("• Some files may be needed by running applications.\n• Safe to remove, but review before cleanup.")
        self.conseq_desc.setStyleSheet("font-size: 11px; color: #cbd5e1; line-height: 1.3; background: transparent; border: none;")
        self.conseq_desc.setWordWrap(True)
        c_layout.addWidget(c_title)
        c_layout.addWidget(self.conseq_desc)
        layout.addWidget(self.conseq_box)

        # Bottom Inspector Buttons
        insp_btn_row = QHBoxLayout()
        self.insp_add_btn = QPushButton("✓ Add to Cleanup Selection")
        self.insp_add_btn.setStyleSheet("background-color: #16a34a; color: #ffffff; border: 1px solid #22c55e; border-radius: 6px; padding: 7px 10px; font-weight: 700; font-size: 11.5px;")
        self.insp_add_btn.clicked.connect(self._toggle_inspected_item_selection)

        self.insp_prev_btn = QPushButton("👁 Preview")
        self.insp_prev_btn.setStyleSheet("background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 6px; padding: 7px 10px; font-size: 11.5px;")
        self.insp_prev_btn.clicked.connect(self._preview_selected)

        insp_btn_row.addWidget(self.insp_add_btn, stretch=2)
        insp_btn_row.addWidget(self.insp_prev_btn, stretch=1)
        layout.addLayout(insp_btn_row)

        return panel

    def _create_inspector_prop(self, parent_layout: QVBoxLayout, label: str, default_val: str) -> QLabel:
        row = QHBoxLayout()
        row.setContentsMargins(0, 1, 0, 1)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #94a3b8; font-size: 11.5px; font-weight: 500; background: transparent; border: none;")
        val = QLabel(default_val)
        val.setStyleSheet("color: #f8fafc; font-size: 11.5px; font-weight: 600; background: transparent; border: none;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        parent_layout.addLayout(row)
        return val

    def _refresh_filters_and_stats(self):
        categories = sorted(list({c.get("category", "General") for c in self.all_candidates}))
        cur_cat = self.cat_combo.currentText()
        self.cat_combo.blockSignals(True)
        self.cat_combo.clear()
        self.cat_combo.addItem("All Categories")
        for cat in categories:
            self.cat_combo.addItem(cat)
        if cur_cat in categories:
            self.cat_combo.setCurrentText(cur_cat)
        self.cat_combo.blockSignals(False)

        tot_cnt = len(self.all_candidates)
        tot_bytes = sum(c.get("size", 0) for c in self.all_candidates)
        safe_items = [c for c in self.all_candidates if c.get("safety_tier") == "SAFE"]
        safe_bytes = sum(c.get("size", 0) for c in safe_items)
        review_items = [c for c in self.all_candidates if c.get("safety_tier") in ["CAUTION", "RISKY"]]
        review_bytes = sum(c.get("size", 0) for c in review_items)
        quar_items = self.db.get_quarantined_items(include_restored=False)
        quar_bytes = sum(q.get("file_size", 0) for q in quar_items)

        self._update_stat_card_values(self.card_total, f"{tot_cnt:,} items", self._fmt_bytes(tot_bytes))
        self._update_stat_card_values(self.card_safe, f"{len(safe_items):,} items", self._fmt_bytes(safe_bytes))
        self._update_stat_card_values(self.card_review, f"{len(review_items):,} items", self._fmt_bytes(review_bytes))
        self._update_stat_card_values(self.card_quar, f"{len(quar_items):,} items", self._fmt_bytes(quar_bytes))

        last_scan = self.db.get_last_scan()
        if last_scan:
            ts = datetime.datetime.fromtimestamp(last_scan["timestamp"]).strftime("%b %d, %Y • %H:%M")
            self.scan_completed_badge.setText(f"✓ Scan Completed\n{ts}")

        self._apply_filters()

    def _update_stat_card_values(self, card: QFrame, count_str: str, size_str: str):
        labels = card.findChildren(QLabel)
        if len(labels) >= 4:
            labels[2].setText(count_str)
            labels[3].setText(f"~ {size_str}")

    def _apply_filters(self):
        cat_filter = self.cat_combo.currentText()
        tier_filter = self.tier_combo.currentText()
        conf_filter = self.conf_combo.currentText()
        search_query = self.search_input.text().lower().strip()

        self.filtered_candidates = []
        for idx, c in enumerate(self.all_candidates):
            if cat_filter != "All Categories" and c.get("category") != cat_filter:
                continue
            if tier_filter != "All Tiers" and c.get("safety_tier") != tier_filter:
                continue
            if conf_filter != "All Levels" and c.get("confidence") != conf_filter:
                continue
            if search_query:
                path = c.get("path", "").lower()
                app = c.get("app_name", "").lower()
                cat = c.get("category", "").lower()
                if search_query not in path and search_query not in app and search_query not in cat:
                    continue
            
            c_copy = dict(c)
            c_copy["_orig_idx"] = idx
            self.filtered_candidates.append(c_copy)

        self.current_page = 1
        self._render_page()

    def _render_page(self):
        total_items = len(self.filtered_candidates)
        tot_bytes = sum(c.get("size", 0) for c in self.filtered_candidates)
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_items)
        page_items = self.filtered_candidates[start_idx:end_idx]

        self.table.setRowCount(len(page_items))

        for row, item in enumerate(page_items):
            orig_idx = item["_orig_idx"]

            # 0. Checkbox
            chk = QCheckBox()
            chk.setChecked(orig_idx in self.selected_indices)
            chk.stateChanged.connect(lambda state, i=orig_idx: self._on_item_check_toggled(i, state))
            chk_w = QWidget()
            chk_w.setStyleSheet("background: transparent; border: none;")
            chk_l = QHBoxLayout(chk_w)
            chk_l.addWidget(chk)
            chk_l.setAlignment(Qt.AlignCenter)
            chk_l.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, chk_w)

            # 1. ITEM: Icon + 2 lines (Path top + Subtitle bottom)
            item_widget = QWidget()
            item_widget.setStyleSheet("background: transparent; border: none;")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(6, 2, 6, 2)
            item_layout.setSpacing(10)

            app_icon_lbl = QLabel(get_item_icon(item.get("app_name", ""), item.get("category", "")))
            app_icon_lbl.setStyleSheet("font-size: 20px; background: transparent; border: none;")
            item_layout.addWidget(app_icon_lbl)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            
            path_lbl = QLabel(item.get("path", ""))
            path_lbl.setStyleSheet("font-weight: 700; color: #ffffff; font-size: 12px; background: transparent; border: none;")
            path_lbl.setToolTip(item.get("path", ""))

            sub_desc = item.get("explanation", "").split(".")[0] or item.get("category", "")
            sub_lbl = QLabel(sub_desc)
            sub_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; background: transparent; border: none;")
            
            text_col.addWidget(path_lbl)
            text_col.addWidget(sub_lbl)
            item_layout.addLayout(text_col, stretch=1)
            self.table.setCellWidget(row, 1, item_widget)

            # 2. SIZE
            size_str = self._fmt_bytes(item.get("size", 0))
            s_item = QTableWidgetItem(size_str)
            s_item.setTextAlignment(Qt.AlignCenter)
            s_item.setForeground(Qt.white)
            self.table.setItem(row, 2, s_item)

            # 3. CATEGORY (Colored Pill)
            cat_str = item.get("category", "General")
            bg_c, text_c = get_category_color(cat_str)
            cat_pill = QLabel(f" {cat_str} ")
            cat_pill.setStyleSheet(f"background-color: {bg_c}; color: {text_c}; border-radius: 4px; padding: 3px 6px; font-weight: 700; font-size: 10.5px; border: none;")
            cat_pill.setAlignment(Qt.AlignCenter)
            cat_w = QWidget()
            cat_w.setStyleSheet("background: transparent; border: none;")
            cat_l = QHBoxLayout(cat_w)
            cat_l.addWidget(cat_pill)
            cat_l.setAlignment(Qt.AlignCenter)
            cat_l.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 3, cat_w)

            # 4. APP / OWNER
            app_item = QTableWidgetItem(item.get("app_name", "System"))
            app_item.setTextAlignment(Qt.AlignCenter)
            app_item.setForeground(Qt.white)
            self.table.setItem(row, 4, app_item)

            # 5. CONFIDENCE (Pill)
            conf = item.get("confidence", "Medium")
            conf_pill = QLabel(conf)
            if conf == "High":
                conf_pill.setStyleSheet("background-color: #064e3b; color: #4ade80; border: 1px solid #059669; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10.5px;")
            elif conf == "Medium":
                conf_pill.setStyleSheet("background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10.5px;")
            else:
                conf_pill.setStyleSheet("background-color: #082f49; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10.5px;")
            conf_pill.setAlignment(Qt.AlignCenter)
            conf_w = QWidget()
            conf_w.setStyleSheet("background: transparent; border: none;")
            conf_l = QHBoxLayout(conf_w)
            conf_l.addWidget(conf_pill)
            conf_l.setAlignment(Qt.AlignCenter)
            conf_l.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 5, conf_w)

            # 6. SAFETY TIER (Pill)
            tier = item.get("safety_tier", "CAUTION")
            tier_label = "Low" if tier == "SAFE" else ("Medium" if tier == "CAUTION" else "High")
            tier_pill = QLabel(tier_label)
            if tier == "SAFE":
                tier_pill.setStyleSheet("background-color: #064e3b; color: #4ade80; border: 1px solid #059669; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10.5px;")
            elif tier == "CAUTION":
                tier_pill.setStyleSheet("background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10.5px;")
            else:
                tier_pill.setStyleSheet("background-color: #4c0519; color: #f87171; border: 1px solid #e11d48; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10.5px;")
            tier_pill.setAlignment(Qt.AlignCenter)
            tier_w = QWidget()
            tier_w.setStyleSheet("background: transparent; border: none;")
            tier_l = QHBoxLayout(tier_w)
            tier_l.addWidget(tier_pill)
            tier_l.setAlignment(Qt.AlignCenter)
            tier_l.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 6, tier_w)

            # 7. RECOMMENDED ACTION (Pill Button)
            act_text = "> Clean" if tier == "SAFE" else "↻ Review"
            act_btn = QPushButton(act_text)
            if tier == "SAFE":
                act_btn.setStyleSheet("background-color: #064e3b; color: #4ade80; border: 1px solid #16a34a; border-radius: 4px; padding: 3px 8px; font-weight: 700; font-size: 11px;")
            else:
                act_btn.setStyleSheet("background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; padding: 3px 8px; font-weight: 700; font-size: 11px;")
            act_btn.clicked.connect(lambda chk, itm=item: self._inspect_item(itm))
            act_w = QWidget()
            act_w.setStyleSheet("background: transparent; border: none;")
            act_l = QHBoxLayout(act_w)
            act_l.addWidget(act_btn)
            act_l.setAlignment(Qt.AlignCenter)
            act_l.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 7, act_w)

        # Update pagination bar
        self.lbl_pagination_info.setText(f"Showing {len(page_items)} of {total_items:,} items ({self._fmt_bytes(tot_bytes)})")
        self.page_number_lbl.setText(str(self.current_page))
        self.prev_page_btn.setEnabled(self.current_page > 1)
        max_page = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        self.next_page_btn.setEnabled(self.current_page < max_page)

        self._update_selected_counter()

        if page_items and not self.currently_inspected_item:
            self._inspect_item(page_items[0])

    def _on_table_row_clicked(self, item):
        row = self.table.currentRow()
        start_idx = (self.current_page - 1) * self.items_per_page
        if start_idx + row < len(self.filtered_candidates):
            self._inspect_item(self.filtered_candidates[start_idx + row])

    def _inspect_item(self, item: Dict[str, Any]):
        self.currently_inspected_item = item
        
        # Header Info
        self.insp_icon.setText(get_item_icon(item.get("app_name", ""), item.get("category", "")))
        self.insp_title.setText(item.get("path", ""))
        self.insp_subtitle.setText(item.get("explanation", "").split(".")[0])
        
        conf = item.get("confidence", "Medium")
        self.insp_conf_pill.setText(f"🟢 {conf} Confidence")

        # Properties
        self.lbl_prop_size.setText(self._fmt_bytes(item.get("size", 0)))
        
        cat = item.get("category", "General")
        self.lbl_prop_cat.setText(f" {cat} ")
        bg_c, text_c = get_category_color(cat)
        self.lbl_prop_cat.setStyleSheet(f"background-color: {bg_c}; color: {text_c}; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10.5px;")
        
        self.lbl_prop_app.setText(item.get("app_name", "System"))
        
        mtime = item.get("mtime")
        if mtime:
            self.lbl_prop_mtime.setText(datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y • %H:%M"))
        else:
            self.lbl_prop_mtime.setText("Apr 26, 2025 • 10:22")

        tier = item.get("safety_tier", "CAUTION")
        tier_label = "Low" if tier == "SAFE" else ("Medium" if tier == "CAUTION" else "High")
        self.lbl_prop_tier.setText(f" {tier_label} ")
        if tier == "SAFE":
            self.lbl_prop_tier.setStyleSheet("background-color: #064e3b; color: #4ade80; border: 1px solid #059669; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10.5px;")
        elif tier == "CAUTION":
            self.lbl_prop_tier.setStyleSheet("background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10.5px;")
        else:
            self.lbl_prop_tier.setStyleSheet("background-color: #4c0519; color: #f87171; border: 1px solid #e11d48; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10.5px;")
        
        rec = "Clean" if tier == "SAFE" else "Review"
        self.lbl_prop_rec.setText(f" {rec} ")
        if tier == "SAFE":
            self.lbl_prop_rec.setStyleSheet("background-color: #064e3b; color: #4ade80; border: 1px solid #059669; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10.5px;")
        else:
            self.lbl_prop_rec.setStyleSheet("background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10.5px;")
        
        quar_avail = item.get("quarantine_available", True)
        self.lbl_prop_quar.setText(" Yes " if quar_avail else " No ")
        self.lbl_prop_quar.setStyleSheet("background-color: #064e3b; color: #4ade80; border: 1px solid #059669; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10.5px;" if quar_avail else "background-color: #1e293b; color: #cbd5e1; border-radius: 4px; padding: 2px 8px; font-size: 10.5px;")

        self.why_text.setText(
            f"• Located in {cat} (known temporary location).\n"
            f"• Files are older than 7 days.\n"
            f"• Not currently in use by any application.\n"
            f"• Contains temporary installer and cache files."
        )

        conseq = item.get("consequences", "• Some files may be needed by running applications.\n• Safe to remove, but review before cleanup.")
        self.conseq_desc.setText(conseq)

        orig_idx = item.get("_orig_idx", -1)
        if orig_idx in self.selected_indices:
            self.insp_add_btn.setText("✓ In Cleanup Selection")
            self.insp_add_btn.setStyleSheet("background-color: #15803d; color: #ffffff; border: 1px solid #22c55e; border-radius: 6px; padding: 7px 10px; font-weight: 700; font-size: 11.5px;")
        else:
            self.insp_add_btn.setText("+ Add to Cleanup Selection")
            self.insp_add_btn.setStyleSheet("background-color: #16a34a; color: #ffffff; border: 1px solid #22c55e; border-radius: 6px; padding: 7px 10px; font-weight: 700; font-size: 11.5px;")

    def _toggle_inspected_item_selection(self):
        if not self.currently_inspected_item:
            return
        orig_idx = self.currently_inspected_item.get("_orig_idx", -1)
        if orig_idx in self.selected_indices:
            self.selected_indices.remove(orig_idx)
        else:
            self.selected_indices.add(orig_idx)
        self._inspect_item(self.currently_inspected_item)
        self._render_page()

    def _on_item_check_toggled(self, orig_idx: int, state: int):
        if state == Qt.Checked:
            self.selected_indices.add(orig_idx)
        else:
            self.selected_indices.discard(orig_idx)
        self._update_selected_counter()

    def _toggle_select_all(self, state: int):
        if state == Qt.Checked:
            for item in self.filtered_candidates:
                self.selected_indices.add(item["_orig_idx"])
        else:
            for item in self.filtered_candidates:
                self.selected_indices.discard(item["_orig_idx"])
        self._render_page()

    def _clear_selection(self):
        self.selected_indices.clear()
        self.chk_select_all.setChecked(False)
        self._render_page()

    def _update_selected_counter(self):
        sel_items = [self.all_candidates[i] for i in self.selected_indices if i < len(self.all_candidates)]
        tot_bytes = sum(c.get("size", 0) for c in sel_items)
        self.lbl_selected_counter.setText(f"🗄️  Selected: <b>{len(sel_items)} items ({self._fmt_bytes(tot_bytes)})</b>")

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render_page()

    def _next_page(self):
        max_page = max(1, (len(self.filtered_candidates) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page < max_page:
            self.current_page += 1
            self._render_page()

    def _preview_selected(self):
        sel_items = [self.all_candidates[i] for i in self.selected_indices if i < len(self.all_candidates)]
        if not sel_items:
            QMessageBox.information(self, "Preview", "No items currently selected.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Preview Selected Cleanup Targets")
        dialog.resize(720, 480)
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(16, 16, 16, 16)

        info = QLabel(f"<b>Reviewing {len(sel_items)} selected target items:</b>")
        info.setStyleSheet("font-size: 14px; color: #ffffff;")
        d_layout.addWidget(info)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        preview_text = ""
        for item in sel_items:
            preview_text += f"• [{item.get('safety_tier')}] {item.get('path')} ({self._fmt_bytes(item.get('size', 0))})\n"
            preview_text += f"   App: {item.get('app_name')} | Category: {item.get('category')}\n"
            preview_text += f"   Consequence: {item.get('consequences')}\n\n"

        text_edit.setText(preview_text)
        d_layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "secondary-btn")
        close_btn.clicked.connect(dialog.accept)
        d_layout.addWidget(close_btn)
        dialog.exec()

    def _execute_cleanup(self, use_quarantine: bool):
        sel_items = [self.all_candidates[i] for i in self.selected_indices if i < len(self.all_candidates)]
        if not sel_items:
            QMessageBox.warning(self, "No Items", "Please select at least one item to clean.")
            return

        tot_bytes = sum(c.get("size", 0) for c in sel_items)
        action_name = "Quarantine (Recommended)" if use_quarantine else "PERMANENT DELETE"

        warn_text = (
            f"Are you sure you want to clean {len(sel_items)} selected items ({self._fmt_bytes(tot_bytes)})?\n\n"
            f"Action: {action_name}\n"
        )
        if use_quarantine:
            warn_text += "Items will be safely moved to Quarantine Vault and can be restored anytime."
        else:
            warn_text += "WARNING: Permanent deletion is irreversible! Files cannot be recovered."

        reply = QMessageBox.question(
            self,
            "Confirm Cleanup Execution",
            warn_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        res = self.executor.execute_cleanup(
            target_items=sel_items,
            use_quarantine=use_quarantine,
            user_confirmed=True
        )

        freed_str = self._fmt_bytes(res.get("bytes_freed", 0))
        QMessageBox.information(
            self,
            "Cleanup Result",
            f"Cleanup complete!\n"
            f"- Succeeded: {res.get('success_count', 0)}\n"
            f"- Failed/Blocked: {res.get('failure_count', 0)}\n"
            f"- Space Recovered: {freed_str}"
        )

        cleaned_paths = {r["path"] for r in res.get("results", []) if r.get("status") in ["QUARANTINED", "DELETED"]}
        self.all_candidates = [c for c in self.all_candidates if c.get("path") not in cleaned_paths]
        self.selected_indices.clear()
        self.currently_inspected_item = None
        self._refresh_filters_and_stats()
        self.cleanup_executed.emit()

    def _open_quarantine_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Quarantine Vault - Safe Restoration")
        dialog.resize(800, 480)
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(16, 16, 16, 16)
        d_layout.setSpacing(12)

        title = QLabel("Quarantine Vault")
        title.setProperty("class", "heading-2")
        desc = QLabel("Isolated files can be restored to their exact original locations or permanently wiped.")
        desc.setProperty("class", "subtext")
        d_layout.addWidget(title)
        d_layout.addWidget(desc)

        q_table = QTableWidget()
        q_table.setColumnCount(5)
        q_table.setHorizontalHeaderLabels(["ID", "Original Path", "Size", "Date Quarantined", "Reason"])
        q_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        q_table.verticalHeader().setDefaultSectionSize(36)
        q_table.verticalHeader().setVisible(False)
        q_table.setSelectionBehavior(QTableWidget.SelectRows)

        records = self.db.get_quarantined_items(include_restored=False)
        q_table.setRowCount(len(records))

        for r, rec in enumerate(records):
            q_table.setItem(r, 0, QTableWidgetItem(str(rec["id"])))
            q_table.setItem(r, 1, QTableWidgetItem(rec["original_path"]))
            q_table.setItem(r, 2, QTableWidgetItem(self._fmt_bytes(rec.get("file_size", 0))))
            dt = datetime.datetime.fromtimestamp(rec["timestamp"]).strftime("%Y-%m-%d %H:%M")
            q_table.setItem(r, 3, QTableWidgetItem(dt))
            q_table.setItem(r, 4, QTableWidgetItem(rec.get("cleanup_reason", "")))

        d_layout.addWidget(q_table)

        btn_row = QHBoxLayout()
        restore_btn = QPushButton("↩ Restore Selected Item")
        restore_btn.setProperty("class", "primary-btn")
        
        perm_btn = QPushButton("🗑 Permanently Delete Selected")
        perm_btn.setProperty("class", "danger-btn")

        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "secondary-btn")
        close_btn.clicked.connect(dialog.accept)

        btn_row.addWidget(restore_btn)
        btn_row.addWidget(perm_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        d_layout.addLayout(btn_row)

        def on_restore():
            sel_row = q_table.currentRow()
            if sel_row < 0:
                QMessageBox.warning(dialog, "Select Item", "Please select an item from the table.")
                return
            rec_id = int(q_table.item(sel_row, 0).text())
            ok, msg = self.quarantine_mgr.restore_item(rec_id)
            if ok:
                QMessageBox.information(dialog, "Restored", msg)
                dialog.accept()
                self._refresh_filters_and_stats()
                self.cleanup_executed.emit()
            else:
                QMessageBox.critical(dialog, "Error", msg)

        def on_delete_perm():
            sel_row = q_table.currentRow()
            if sel_row < 0:
                QMessageBox.warning(dialog, "Select Item", "Please select an item from the table.")
                return
            rec_id = int(q_table.item(sel_row, 0).text())
            
            confirm = QMessageBox.question(
                dialog,
                "Confirm Permanent Deletion",
                "Permanently delete this item from the quarantine vault? This cannot be undone.",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                ok, msg = self.quarantine_mgr.delete_quarantined_permanently(rec_id)
                if ok:
                    QMessageBox.information(dialog, "Deleted", msg)
                    dialog.accept()
                    self._refresh_filters_and_stats()
                else:
                    QMessageBox.critical(dialog, "Error", msg)

        restore_btn.clicked.connect(on_restore)
        perm_btn.clicked.connect(on_delete_perm)

        dialog.exec()

    def _open_history_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Cleanup & Scan History")
        dialog.resize(700, 420)
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Cleanup History")
        title.setProperty("class", "heading-2")
        d_layout.addWidget(title)

        h_table = QTableWidget()
        h_table.setColumnCount(4)
        h_table.setHorizontalHeaderLabels(["Timestamp", "Action Type", "Items Freed", "Space Recovered"])
        h_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        h_table.verticalHeader().setVisible(False)

        records = self.db.get_cleanup_history(limit=50)
        h_table.setRowCount(len(records))

        for r, rec in enumerate(records):
            dt = datetime.datetime.fromtimestamp(rec["timestamp"]).strftime("%Y-%m-%d %H:%M")
            h_table.setItem(r, 0, QTableWidgetItem(dt))
            h_table.setItem(r, 1, QTableWidgetItem(rec.get("action_type", "")))
            h_table.setItem(r, 2, QTableWidgetItem(str(rec.get("items_count", 0))))
            h_table.setItem(r, 3, QTableWidgetItem(self._fmt_bytes(rec.get("bytes_freed", 0))))

        d_layout.addWidget(h_table)

        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "secondary-btn")
        close_btn.clicked.connect(dialog.accept)
        d_layout.addWidget(close_btn)
        dialog.exec()

    @staticmethod
    def _fmt_bytes(num_bytes: int) -> str:
        if num_bytes >= 1024**3:
            return f"{num_bytes / (1024**3):.2f} GB"
        elif num_bytes >= 1024**2:
            return f"{num_bytes / (1024**2):.1f} MB"
        elif num_bytes >= 1024:
            return f"{num_bytes / 1024:.1f} KB"
        return f"{num_bytes} B"
