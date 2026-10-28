import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QLineEdit, QCheckBox, QListWidget, QFileDialog, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from ..settings.config import SettingsManager
from ..ai.ollama_client import OllamaClient
from ..database.db import DatabaseManager

class SettingsView(QWidget):
    settings_updated = Signal()

    def __init__(self, settings_mgr: SettingsManager, ollama_client: OllamaClient, db_mgr: DatabaseManager, parent=None):
        super().__init__(parent)
        self.settings = settings_mgr
        self.ollama = ollama_client
        self.db = db_mgr
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header Title
        top_box = QVBoxLayout()
        top_box.setSpacing(4)
        title = QLabel("Settings & Preferences")
        title.setProperty("class", "heading-1")
        sub = QLabel("Configure local AI runtime, protected directories, exclusions, and privacy options.")
        sub.setProperty("class", "subtext")
        top_box.addWidget(title)
        top_box.addWidget(sub)
        layout.addLayout(top_box)

        # 1. Local AI Configuration Card
        ai_card = QFrame()
        ai_card.setProperty("class", "card")
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setSpacing(14)

        ai_title = QLabel("🤖 Local AI Engine (Ollama & Qwen3.5 4B)")
        ai_title.setProperty("class", "heading-2")
        ai_desc = QLabel("The agent uses Ollama for local inference. When unavailable, it automatically uses deterministic rule-based analysis.")
        ai_desc.setProperty("class", "subtext")
        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(ai_desc)

        # Host Row
        host_row = QHBoxLayout()
        host_lbl = QLabel("Ollama API URL:")
        host_lbl.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 13px;")
        host_lbl.setFixedWidth(140)
        self.host_input = QLineEdit(self.settings.get_ollama_host())
        host_row.addWidget(host_lbl)
        host_row.addWidget(self.host_input)
        ai_layout.addLayout(host_row)

        # Model Row
        model_row = QHBoxLayout()
        model_lbl = QLabel("Model Identifier:")
        model_lbl.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 13px;")
        model_lbl.setFixedWidth(140)
        self.model_input = QLineEdit(self.settings.get_model_name())
        model_row.addWidget(model_lbl)
        model_row.addWidget(self.model_input)
        ai_layout.addLayout(model_row)

        # Status & Test Button Row
        test_row = QHBoxLayout()
        test_btn = QPushButton("⚡ Verify Ollama Connection")
        test_btn.setProperty("class", "action-blue-btn")
        test_btn.clicked.connect(self._test_ollama)
        
        self.ollama_status_lbl = QLabel("Status: Not checked yet")
        self.ollama_status_lbl.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 13px;")
        test_row.addWidget(test_btn)
        test_row.addWidget(self.ollama_status_lbl)
        test_row.addStretch()
        ai_layout.addLayout(test_row)

        self.setup_instructions_lbl = QLabel("")
        self.setup_instructions_lbl.setStyleSheet("background-color: #0b0f17; color: #fbbf24; border: 1px solid #334155; border-radius: 8px; padding: 10px; font-size: 12.5px; line-height: 1.5;")
        self.setup_instructions_lbl.setWordWrap(True)
        self.setup_instructions_lbl.setVisible(False)
        ai_layout.addWidget(self.setup_instructions_lbl)

        layout.addWidget(ai_card)

        # 2. Exclusions Card
        ex_card = QFrame()
        ex_card.setProperty("class", "card")
        ex_layout = QVBoxLayout(ex_card)
        ex_layout.setSpacing(12)

        ex_title = QLabel("📁 Scan Exclusions")
        ex_title.setProperty("class", "heading-2")
        ex_desc = QLabel("Directories matching these paths will be completely bypassed during all scanning operations.")
        ex_desc.setProperty("class", "subtext")
        ex_layout.addWidget(ex_title)
        ex_layout.addWidget(ex_desc)

        self.ex_list = QListWidget()
        self.ex_list.setStyleSheet(
            "QListWidget { background-color: #0b0f17; border: 1px solid #334155; border-radius: 8px; padding: 8px; font-size: 13px; color: #f1f5f9; } "
            "QListWidget::item { padding: 6px 10px; border-bottom: 1px solid #1e293b; }"
        )
        self.ex_list.setMinimumHeight(120)
        for ex in self.settings.get_exclusions():
            self.ex_list.addItem(ex)
        ex_layout.addWidget(self.ex_list)

        ex_btn_row = QHBoxLayout()
        add_ex_btn = QPushButton("➕ Add Folder Exclusion...")
        add_ex_btn.setProperty("class", "secondary-btn")
        add_ex_btn.clicked.connect(self._add_exclusion)
        
        del_ex_btn = QPushButton("✕ Remove Selected")
        del_ex_btn.setProperty("class", "secondary-btn")
        del_ex_btn.clicked.connect(self._remove_exclusion)
        
        ex_btn_row.addWidget(add_ex_btn)
        ex_btn_row.addWidget(del_ex_btn)
        ex_btn_row.addStretch()
        ex_layout.addLayout(ex_btn_row)

        layout.addWidget(ex_card)

        # 3. Privacy & History Card
        mon_card = QFrame()
        mon_card.setProperty("class", "card")
        mon_layout = QVBoxLayout(mon_card)
        mon_layout.setSpacing(14)

        mon_title = QLabel("🔒 Privacy & History Management")
        mon_title.setProperty("class", "heading-2")
        mon_layout.addWidget(mon_title)

        self.mon_chk = QCheckBox("Enable Low-Disk Space Background Monitoring (Opt-in)")
        self.mon_chk.setChecked(self.settings.get("background_monitoring_enabled", False))
        self.mon_chk.stateChanged.connect(lambda state: self.settings.set("background_monitoring_enabled", state == Qt.Checked))
        mon_layout.addWidget(self.mon_chk)

        clear_hist_btn = QPushButton("🗑 Wipe All Local History & Audit Logs")
        clear_hist_btn.setProperty("class", "danger-btn")
        clear_hist_btn.setFixedWidth(280)
        clear_hist_btn.clicked.connect(self._clear_history)
        mon_layout.addWidget(clear_hist_btn)

        layout.addWidget(mon_card)

        # Save Button
        save_btn = QPushButton("💾 Save All Settings")
        save_btn.setProperty("class", "primary-btn")
        save_btn.setStyleSheet("padding: 13px 36px; font-size: 14px;")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _test_ollama(self):
        host = self.host_input.text().strip()
        model = self.model_input.text().strip()
        self.ollama.host = host
        self.ollama.model_name = model

        ok, msg = self.ollama.check_connection()
        if ok:
            has_model = self.ollama.is_model_available()
            if has_model:
                self.ollama_status_lbl.setText(f"✓ Connected: Model '{model}' is ready!")
                self.ollama_status_lbl.setStyleSheet("color: #4ade80; font-weight: 700;")
                self.setup_instructions_lbl.setVisible(False)
            else:
                self.ollama_status_lbl.setText(f"⚠ Connected, but '{model}' is not downloaded yet.")
                self.ollama_status_lbl.setStyleSheet("color: #fbbf24; font-weight: 700;")
                self.setup_instructions_lbl.setText(
                    f"To download model, open PowerShell and run:\n  ollama run {model}\n\n"
                    "Estimated download size is ~2.5 GB. Ensure sufficient disk space is free."
                )
                self.setup_instructions_lbl.setVisible(True)
        else:
            self.ollama_status_lbl.setText(f"✗ Offline: {msg}")
            self.ollama_status_lbl.setStyleSheet("color: #f87171; font-weight: 700;")
            self.setup_instructions_lbl.setText(self.ollama.get_setup_instructions())
            self.setup_instructions_lbl.setVisible(True)

    def _add_exclusion(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Exclusion Directory")
        if folder:
            self.settings.add_exclusion(folder)
            self.ex_list.addItem(folder)

    def _remove_exclusion(self):
        item = self.ex_list.currentItem()
        if item:
            self.settings.remove_exclusion(item.text())
            self.ex_list.takeItem(self.ex_list.row(item))

    def _clear_history(self):
        confirm = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to delete all stored scan history, cleanup records, and audit logs?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.db.clear_history()
            QMessageBox.information(self, "History Cleared", "Local history has been completely wiped.")

    def _save_settings(self):
        self.settings.set("ollama_host", self.host_input.text().strip())
        self.settings.set("model_name", self.model_input.text().strip())
        self.settings_updated.emit()
        QMessageBox.information(self, "Settings", "Settings saved successfully.")
