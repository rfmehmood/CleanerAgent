from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTextEdit, QLineEdit, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from typing import Dict, Any, List
from ..ai.intent_parser import IntentParser

class AIAssistantView(QWidget):
    request_action = Signal(str)

    def __init__(self, intent_parser: IntentParser, db_manager, parent=None):
        super().__init__(parent)
        self.parser = intent_parser
        self.db = db_manager
        self.candidates_cache: List[Dict[str, Any]] = []
        self._init_ui()

    def set_candidates(self, candidates: List[Dict[str, Any]]):
        self.candidates_cache = candidates

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Header Title
        top_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("AI PC Maintenance Assistant")
        title.setProperty("class", "heading-1")
        sub = QLabel("Powered by local Qwen3.5 4B & deterministic system verification. 100% Private.")
        sub.setProperty("class", "subtext")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        top_layout.addLayout(title_box)
        top_layout.addStretch()

        self.status_chip = QLabel("AI Engine: Verifying...")
        self.status_chip.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 8px 16px; border-radius: 8px; font-weight: 600; font-size: 13px;")
        
        clear_btn = QPushButton("Clear Chat")
        clear_btn.setProperty("class", "secondary-btn")
        clear_btn.setStyleSheet("padding: 7px 14px; font-size: 12px;")
        clear_btn.clicked.connect(self._clear_chat)

        top_layout.addWidget(self.status_chip)
        top_layout.addWidget(clear_btn)
        layout.addLayout(top_layout)

        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(
            "background-color: #0b0f17; border: 1px solid #1e293b; border-radius: 12px; "
            "padding: 18px; font-size: 13.5px; line-height: 1.6; color: #f8fafc;"
        )
        layout.addWidget(self.chat_display, stretch=1)

        # Prompt Suggestions Title & Chips
        prompt_label = QLabel("Suggested Questions:")
        prompt_label.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;")
        layout.addWidget(prompt_label)

        chips_frame = QFrame()
        chips_layout = QHBoxLayout(chips_frame)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(8)

        prompts = [
            "Why is my C drive almost full?",
            "Find uninstalled leftovers",
            "Find Python & Node caches",
            "Analyze AI model storage",
            "Explain risky recommendations",
            "Compare with previous scan"
        ]
        for p in prompts:
            chip_btn = QPushButton(p)
            chip_btn.setProperty("class", "chip-btn")
            chip_btn.clicked.connect(lambda checked, text=p: self._send_user_message(text))
            chips_layout.addWidget(chip_btn)
        chips_layout.addStretch()
        layout.addWidget(chips_frame)

        # Input Row Card
        input_frame = QFrame()
        input_frame.setProperty("class", "card")
        input_frame.setStyleSheet("background-color: #131c2e; border: 1px solid #1e293b; border-radius: 12px; padding: 10px;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask a question about your PC storage (e.g., 'Why is my C drive almost full?')...")
        self.input_field.returnPressed.connect(self._on_send_clicked)

        send_btn = QPushButton("Send Message ⏎")
        send_btn.setProperty("class", "action-blue-btn")
        send_btn.clicked.connect(self._on_send_clicked)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)
        layout.addWidget(input_frame)

        # Welcome message
        self._append_message("Assistant", (
            "👋 Welcome! I am your **Local AI PC Cleanup Assistant**.\n\n"
            "• I analyze your actual storage, temporary files, developer caches, and application leftovers.\n"
            "• **100% Private**: All scans and AI reasoning run locally on your computer with zero cloud telemetry.\n"
            "• **Deterministic Safety**: I inspect real filesystem data and explain what is safe to clean and what requires caution.\n\n"
            "Click one of the suggested prompts above or ask any question to get started!"
        ), is_user=False, mode="Rule-Based Engine")

    def _clear_chat(self):
        self.chat_display.clear()
        self._append_message("Assistant", "Chat cleared. How can I assist you with your storage?", is_user=False, mode="System")

    def _on_send_clicked(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._send_user_message(text)

    def _send_user_message(self, text: str):
        self._append_message("You", text, is_user=True)
        recent_scans = self.db.get_recent_scans(limit=5)
        
        res = self.parser.process_user_query(
            query=text,
            candidates=self.candidates_cache,
            recent_scans=recent_scans
        )

        response_text = res.get("response", "")
        mode_str = res.get("mode", "Rule-Based Engine")
        self.status_chip.setText(f"Active: {mode_str}")

        actions = res.get("suggested_actions", [])
        if actions:
            response_text += "\n\n💡 **Suggested Actions:** " + " • ".join(actions)

        self._append_message("Assistant", response_text, is_user=False, mode=mode_str)

    def _append_message(self, sender: str, text: str, is_user: bool, mode: str = ""):
        html_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        import re
        html_text = re.sub(r'\*\*(.*?)\*\*', r'<b style="color: #ffffff;">\1</b>', html_text)
        html_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html_text)
        html_text = re.sub(r'`(.*?)`', r'<code style="background-color: #0b0f17; padding: 2px 5px; border-radius: 4px; color: #38bdf8; font-family: monospace;">\1</code>', html_text)

        if is_user:
            msg_html = f"""
            <div style="margin: 12px 0px; text-align: right;">
                <span style="background-color: #2563eb; color: #ffffff; padding: 11px 16px; border-radius: 14px; display: inline-block; max-width: 75%; font-size: 13.5px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                    <b>You:</b> {html_text}
                </span>
            </div>
            """
        else:
            mode_badge = f'<span style="font-size: 11px; background-color: #0f172a; color: #38bdf8; border: 1px solid #1e293b; padding: 2px 8px; border-radius: 6px; margin-left: 8px; font-weight: 600;">{mode}</span>' if mode else ''
            msg_html = f"""
            <div style="margin: 14px 0px; text-align: left;">
                <div style="margin-bottom: 6px; color: #cbd5e1; font-weight: 700; font-size: 13px;">
                    🤖 Assistant {mode_badge}
                </div>
                <div style="background-color: #131c2e; color: #f1f5f9; padding: 14px 18px; border-radius: 12px; border: 1px solid #1e293b; display: inline-block; max-width: 85%; font-size: 13.5px; line-height: 1.6;">
                    {html_text}
                </div>
            </div>
            """

        self.chat_display.append(msg_html)
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
