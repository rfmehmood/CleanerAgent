from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QProgressBar, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from typing import Dict, Any, List
from ..storage.disk_analyzer import DiskStorageAnalyzer

class DashboardView(QWidget):
    request_navigation = Signal(str)

    def __init__(self, db_manager, settings_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.settings = settings_manager
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(20)

        # Header Title Area
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        title = QLabel("System Storage Overview")
        title.setProperty("class", "heading-1")
        subtitle = QLabel("Local AI-Assisted Windows Storage Optimization • 100% Offline & Private")
        subtitle.setProperty("class", "subtext")
        
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Engine Mode Status Indicator
        self.mode_badge = QLabel("Mode: Checking...")
        self.mode_badge.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; "
            "border-radius: 8px; padding: 8px 16px; font-weight: 600; font-size: 13px;"
        )
        header_layout.addWidget(self.mode_badge)
        main_layout.addLayout(header_layout)

        # Scrollable Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(20)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Drive Storage Container
        drives_title = QLabel("Physical Disk Partitions")
        drives_title.setProperty("class", "heading-2")
        self.content_layout.addWidget(drives_title)

        self.drives_container = QVBoxLayout()
        self.drives_container.setSpacing(12)
        self.content_layout.addLayout(self.drives_container)

        # 2. Key Metrics Row
        metrics_title = QLabel("Optimization Summary")
        metrics_title.setProperty("class", "heading-2")
        self.content_layout.addWidget(metrics_title)

        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(16)

        self.candidates_card = self._create_stat_card("Cleanup Candidates", "0 items", "Discovered potential items to clean", "🔍")
        metrics_grid.addWidget(self.candidates_card, 0, 0)

        self.recoverable_card = self._create_stat_card("Estimated Recoverable", "0.0 MB", "*Calculated potential savings across selected caches", "💾")
        metrics_grid.addWidget(self.recoverable_card, 0, 1)

        self.last_scan_card = self._create_stat_card("Last Completed Scan", "Never", "No scan recorded yet in local database", "⏱️")
        metrics_grid.addWidget(self.last_scan_card, 0, 2)

        self.content_layout.addLayout(metrics_grid)

        # 3. Quick Action Controls Banner
        actions_card = QFrame()
        actions_card.setProperty("class", "card")
        actions_card.setStyleSheet("background-color: #131c2e; border: 1px solid #1e293b; border-radius: 12px; padding: 16px;")
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setSpacing(16)

        actions_info = QVBoxLayout()
        actions_title = QLabel("Ready to analyze your storage?")
        actions_title.setProperty("class", "heading-3")
        actions_sub = QLabel("Launch a deep read-only scan to detect application caches, leftovers, and dev junk.")
        actions_sub.setProperty("class", "subtext")
        actions_info.addWidget(actions_title)
        actions_info.addWidget(actions_sub)
        actions_layout.addLayout(actions_info)
        actions_layout.addStretch()

        scan_btn = QPushButton("🚀 Start Deep Scan")
        scan_btn.setProperty("class", "action-blue-btn")
        scan_btn.clicked.connect(lambda: self.request_navigation.emit("scanner"))

        ai_btn = QPushButton("🤖 Ask AI Assistant")
        ai_btn.setProperty("class", "secondary-btn")
        ai_btn.clicked.connect(lambda: self.request_navigation.emit("assistant"))

        cleanup_btn = QPushButton("🧹 Cleanup Center")
        cleanup_btn.setProperty("class", "secondary-btn")
        cleanup_btn.clicked.connect(lambda: self.request_navigation.emit("cleanup"))

        actions_layout.addWidget(scan_btn)
        actions_layout.addWidget(ai_btn)
        actions_layout.addWidget(cleanup_btn)

        self.content_layout.addWidget(actions_card)

        # 4. Recent Activity Log
        self.activity_card = QFrame()
        self.activity_card.setProperty("class", "card")
        self.activity_layout = QVBoxLayout(self.activity_card)
        self.activity_layout.setSpacing(8)
        
        act_title = QLabel("Recent Scan & Cleanup Activity")
        act_title.setProperty("class", "heading-3")
        self.activity_layout.addWidget(act_title)
        
        self.activity_content = QLabel("No recent activity recorded.")
        self.activity_content.setStyleSheet("color: #cbd5e1; padding-top: 4px; font-size: 13px; line-height: 1.6;")
        self.activity_layout.addWidget(self.activity_content)
        self.content_layout.addWidget(self.activity_card)

        self.content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self.refresh_dashboard(candidates=[])

    def _create_stat_card(self, title: str, value: str, subtext: str, icon: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        header_row = QHBoxLayout()
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 18px;")
        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "stat-label")
        header_row.addWidget(lbl_icon)
        header_row.addWidget(lbl_title)
        header_row.addStretch()
        layout.addLayout(header_row)

        lbl_val = QLabel(value)
        lbl_val.setProperty("class", "stat-value")
        layout.addWidget(lbl_val)

        lbl_sub = QLabel(subtext)
        lbl_sub.setProperty("class", "subtext")
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_sub)
        
        return card

    def refresh_dashboard(self, candidates: List[Dict[str, Any]] = None, ai_mode_str: str = "Rule-Based Engine"):
        self.mode_badge.setText(f"Mode: {ai_mode_str}")
        
        # Clear existing drive widgets
        while self.drives_container.count():
            item = self.drives_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Refresh drive cards with readable layout
        drives = DiskStorageAnalyzer.get_drive_summary()
        for d in drives:
            d_card = QFrame()
            d_card.setProperty("class", "card")
            d_card.setStyleSheet("background-color: #131c2e; border: 1px solid #1e293b; border-radius: 12px; padding: 18px;")
            d_layout = QVBoxLayout(d_card)
            d_layout.setSpacing(10)

            top_row = QHBoxLayout()
            d_icon = QLabel("💽")
            d_icon.setStyleSheet("font-size: 20px;")
            d_name = QLabel(f"Local Disk ({d['letter']}:)")
            d_name.setProperty("class", "heading-3")
            d_name.setStyleSheet("font-weight: 700; color: #ffffff;")
            
            top_row.addWidget(d_icon)
            top_row.addWidget(d_name)
            top_row.addStretch()

            used_gb = d["used_bytes"] / (1024**3)
            total_gb = d["total_bytes"] / (1024**3)
            free_gb = d["free_bytes"] / (1024**3)
            
            stats_box = QHBoxLayout()
            stats_box.setSpacing(14)

            free_badge = QLabel(f"<b>{free_gb:.1f} GB</b> Free")
            free_badge.setStyleSheet("background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 6px; padding: 4px 10px; font-size: 13px;")
            
            used_lbl = QLabel(f"{used_gb:.1f} GB Used of {total_gb:.1f} GB")
            used_lbl.setStyleSheet("color: #cbd5e1; font-weight: 500; font-size: 13px;")

            stats_box.addWidget(used_lbl)
            stats_box.addWidget(free_badge)
            top_row.addLayout(stats_box)
            d_layout.addLayout(top_row)

            # Progress Bar
            pbar = QProgressBar()
            pbar.setValue(int(d["percent_used"]))
            pbar.setFormat(f"{d['percent_used']}% Used")
            if d["percent_used"] > 90:
                pbar.setStyleSheet("QProgressBar::chunk { background-color: #ef4444; border-radius: 6px; }")
            elif d["percent_used"] > 75:
                pbar.setStyleSheet("QProgressBar::chunk { background-color: #f59e0b; border-radius: 6px; }")
            else:
                pbar.setStyleSheet("QProgressBar::chunk { background-color: #3b82f6; border-radius: 6px; }")
            d_layout.addWidget(pbar)

            self.drives_container.addWidget(d_card)

        # Update Candidate Stats
        candidates = candidates or []
        tot_candidates = len(candidates)
        tot_bytes = sum(c.get("size", 0) for c in candidates)
        tot_mb = tot_bytes / (1024*1024)

        val_labels = self.candidates_card.findChildren(QLabel)
        if len(val_labels) >= 3:
            val_labels[2].setText(f"{tot_candidates} items")

        rec_labels = self.recoverable_card.findChildren(QLabel)
        if len(rec_labels) >= 3:
            if tot_mb >= 1024:
                rec_labels[2].setText(f"{tot_mb / 1024:.2f} GB")
            else:
                rec_labels[2].setText(f"{tot_mb:.1f} MB")

        # Update Last Scan
        last_scan = self.db.get_last_scan()
        scan_labels = self.last_scan_card.findChildren(QLabel)
        if len(scan_labels) >= 3:
            if last_scan:
                import datetime
                ts = datetime.datetime.fromtimestamp(last_scan["timestamp"]).strftime("%b %d, %H:%M")
                scan_labels[2].setText(ts)
                scan_labels[3].setText(f"{last_scan.get('total_items', 0)} items discovered ({last_scan.get('duration_seconds', 0):.1f}s)")
            else:
                scan_labels[2].setText("Never")

        # Update recent activity
        history = self.db.get_cleanup_history(limit=4)
        if history:
            text = ""
            import datetime
            for h in history:
                dt_str = datetime.datetime.fromtimestamp(h["timestamp"]).strftime("%b %d, %H:%M")
                mb = h.get("bytes_freed", 0) / (1024*1024)
                text += f"• <b>[{dt_str}]</b> {h['action_type']} — Freed <b style='color: #4ade80;'>{mb:.1f} MB</b> across {h.get('items_count', 0)} items ({h['status']})<br>"
            self.activity_content.setText(text.strip())
        else:
            self.activity_content.setText("No cleanup operations executed yet.")
