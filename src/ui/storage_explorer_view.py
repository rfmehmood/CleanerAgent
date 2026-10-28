import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt, Signal
from ..storage.disk_analyzer import DiskStorageAnalyzer
from ..cleanup.safety import SafetyPolicy

class StorageExplorerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path = Path("C:\\")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Storage Explorer")
        title.setProperty("class", "heading-1")
        sub = QLabel("Interactive disk drill-down. Double-click any folder to navigate deeper and discover space hogs.")
        sub.setProperty("class", "subtext")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        layout.addLayout(title_box)

        # Navigation Bar Card
        nav_card = QFrame()
        nav_card.setProperty("class", "card")
        nav_card.setStyleSheet("background-color: #131c2e; border: 1px solid #1e293b; border-radius: 12px; padding: 12px 16px;")
        nav_layout = QHBoxLayout(nav_card)
        nav_layout.setSpacing(12)

        drive_lbl = QLabel("Partition:")
        drive_lbl.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 13px;")
        self.drive_combo = QComboBox()
        self.drive_combo.addItems([f"{letter}:\\" for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{letter}:\\")])
        self.drive_combo.currentTextChanged.connect(self._on_drive_changed)

        self.up_btn = QPushButton("⬆ Level Up")
        self.up_btn.setProperty("class", "secondary-btn")
        self.up_btn.clicked.connect(self._navigate_up)

        path_prefix = QLabel("Location:")
        path_prefix.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 13px; padding-left: 10px;")

        self.path_label = QLabel(str(self.current_path))
        self.path_label.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 13.5px; font-family: monospace;")

        nav_layout.addWidget(drive_lbl)
        nav_layout.addWidget(self.drive_combo)
        nav_layout.addWidget(self.up_btn)
        nav_layout.addWidget(path_prefix)
        nav_layout.addWidget(self.path_label, stretch=1)
        layout.addWidget(nav_card)

        # High-Contrast Storage Explorer Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Size", "File Count", "Last Modified"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 115)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 160)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #0b0f17; alternate-background-color: #131c2e; border: 1px solid #1e293b; border-radius: 10px; } "
            "QTableWidget::item { padding: 4px 8px; }"
        )
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table, stretch=1)

        # Status Bar Card
        self.status_bar = QLabel("Click a folder to view details or double-click to navigate inside.")
        self.status_bar.setStyleSheet("color: #94a3b8; font-size: 12.5px; padding-left: 4px;")
        layout.addWidget(self.status_bar)

        self.load_directory(self.current_path)

    def _on_drive_changed(self, drive_str: str):
        if drive_str and os.path.exists(drive_str):
            self.load_directory(Path(drive_str))

    def _navigate_up(self):
        if self.current_path != self.current_path.parent:
            self.load_directory(self.current_path.parent)

    def _on_row_double_clicked(self, row: int, col: int):
        name_item = self.table.item(row, 0)
        type_item = self.table.item(row, 1)
        if name_item and type_item and type_item.text() == "Folder":
            sub_name = name_item.text().replace("📁 ", "").strip()
            next_path = self.current_path / sub_name
            self.load_directory(next_path)

    def load_directory(self, target_path: Path):
        self.current_path = target_path
        self.path_label.setText(str(self.current_path))
        self.up_btn.setEnabled(self.current_path != self.current_path.parent)

        breakdown = DiskStorageAnalyzer.analyze_folder_breakdown(str(self.current_path), max_depth=1)
        if "error" in breakdown:
            self.status_bar.setText(f"⚠ Warning: {breakdown.get('error')}")
            self.table.setRowCount(0)
            return

        children = breakdown.get("children", [])
        inaccessible = breakdown.get("inaccessible_count", 0)

        self.table.setRowCount(len(children))
        import datetime

        for r, child in enumerate(children):
            name = child["name"]
            is_dir = child["is_dir"]
            size_mb = child["size"] / (1024*1024)
            size_str = f"{size_mb/1024:.2f} GB" if size_mb >= 1024 else f"{size_mb:.1f} MB"
            
            # Name
            n_item = QTableWidgetItem(f"📁 {name}" if is_dir else f"📄 {name}")
            n_item.setToolTip(name)
            self.table.setItem(r, 0, n_item)
            
            # Type
            t_item = QTableWidgetItem("Folder" if is_dir else "File")
            t_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 1, t_item)
            
            # Size
            s_item = QTableWidgetItem(size_str)
            s_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(r, 2, s_item)
            
            # Count
            c_item = QTableWidgetItem(str(child.get("file_count", "-")))
            c_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 3, c_item)
            
            # Mtime
            dt_str = datetime.datetime.fromtimestamp(child.get("mtime", 0)).strftime("%Y-%m-%d %H:%M")
            m_item = QTableWidgetItem(dt_str)
            m_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 4, m_item)

        status_text = f"Showing {len(children)} items in {self.current_path}."
        if inaccessible > 0:
            status_text += f" ({inaccessible} system-protected or locked items were safely skipped)."
        self.status_bar.setText(status_text)
