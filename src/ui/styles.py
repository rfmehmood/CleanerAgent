DARK_THEME_QSS = """
/* ==========================================================================
   PREMIUM ULTRA-READABLE DARK THEME (HIGH-CONTRAST MODERN FLUENT STYLE)
   ========================================================================== */

/* Global Window & Typography */
QMainWindow, QDialog {
    background-color: #070b14;
}
QWidget {
    color: #f1f5f9;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* Tooltips */
QToolTip {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #334155;
    min-height: 30px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #0f172a;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #334155;
    min-width: 30px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #475569;
}

/* Sidebar Navigation */
QFrame#sidebar {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
}

QPushButton.nav-btn {
    text-align: left;
    padding: 12px 18px;
    font-size: 14px;
    font-weight: 500;
    color: #94a3b8;
    background-color: transparent;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 8px;
    margin: 2px 8px;
}
QPushButton.nav-btn:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #f8fafc;
}
QPushButton.nav-btn:checked {
    background-color: #1e293b;
    color: #38bdf8;
    font-weight: 600;
    border-left: 3px solid #38bdf8;
}

/* Cards & Surfaces */
QFrame.card {
    background-color: #131c2e;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 18px;
}
QFrame.card:hover {
    border-color: #334155;
}

QFrame.highlight-card {
    background-color: #172554;
    border: 1px solid #1d4ed8;
    border-radius: 12px;
    padding: 18px;
}

/* Typography Hierarchy */
QLabel.heading-1 {
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.3px;
}
QLabel.heading-2 {
    font-size: 18px;
    font-weight: 600;
    color: #f8fafc;
}
QLabel.heading-3 {
    font-size: 15px;
    font-weight: 600;
    color: #e2e8f0;
}
QLabel.stat-value {
    font-size: 30px;
    font-weight: 700;
    color: #38bdf8;
}
QLabel.stat-label {
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QLabel.subtext {
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.4;
}

/* Action Buttons */
QPushButton.primary-btn {
    background-color: #16a34a;
    color: #ffffff;
    border: 1px solid #22c55e;
    border-radius: 8px;
    padding: 11px 22px;
    font-weight: 600;
    font-size: 13.5px;
}
QPushButton.primary-btn:hover {
    background-color: #22c55e;
}
QPushButton.primary-btn:pressed {
    background-color: #15803d;
}
QPushButton.primary-btn:disabled {
    background-color: #1e293b;
    color: #64748b;
    border-color: #334155;
}

QPushButton.action-blue-btn {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    padding: 11px 22px;
    font-weight: 600;
    font-size: 13.5px;
}
QPushButton.action-blue-btn:hover {
    background-color: #3b82f6;
}
QPushButton.action-blue-btn:pressed {
    background-color: #1d4ed8;
}

QPushButton.danger-btn {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton.danger-btn:hover {
    background-color: #ef4444;
}

QPushButton.secondary-btn {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 500;
    font-size: 13px;
}
QPushButton.secondary-btn:hover {
    background-color: #334155;
    color: #ffffff;
    border-color: #475569;
}

QPushButton.chip-btn {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 7px 14px;
    font-size: 12.5px;
    font-weight: 500;
}
QPushButton.chip-btn:hover {
    background-color: #334155;
    color: #38bdf8;
    border-color: #38bdf8;
}

/* High-Contrast Tables */
QTableWidget {
    background-color: #070b14;
    border: 1px solid #1e293b;
    border-radius: 8px;
    gridline-color: transparent;
    color: #f1f5f9;
    font-size: 12px;
    selection-background-color: rgba(37, 99, 235, 0.25);
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #0b1120;
    color: #94a3b8;
    padding: 6px 2px;
    border: none;
    border-bottom: 1px solid #1e293b;
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
QTableWidget::item {
    padding: 4px 6px;
    border-bottom: 1px solid #111827;
}
QTableWidget::item:selected {
    background-color: rgba(37, 99, 235, 0.25);
    color: #ffffff;
}

/* Inputs & Form Controls */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #070b14;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 7px 12px;
    color: #ffffff;
    font-size: 12.5px;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #38bdf8;
    background-color: #0d1527;
}

QComboBox {
    background-color: #070b14;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 5px 10px;
    color: #f8fafc;
    font-weight: 500;
    font-size: 12px;
    min-height: 20px;
}
QComboBox:hover {
    border-color: #334155;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #0f172a;
    color: #f8fafc;
    selection-background-color: #2563eb;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px;
}

/* Progress Bars */
QProgressBar {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 7px;
    height: 16px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    font-size: 11.5px;
}
QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 6px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #0f172a;
}
QCheckBox::indicator:hover {
    border-color: #38bdf8;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #38bdf8;
}
"""
