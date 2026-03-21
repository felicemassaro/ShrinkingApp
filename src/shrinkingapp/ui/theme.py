from __future__ import annotations


APP_STYLESHEET = """
QWidget {
    background: #f4f1eb;
    color: #1f2933;
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
}

QMainWindow, QFrame#MainShell, QWidget#ContentArea {
    background: #f4f1eb;
}

QFrame#NavRail {
    background: #18363b;
    border-right: 1px solid #244951;
}

QLabel#NavTitle {
    color: #f4f7f5;
    font-size: 22px;
    font-weight: 700;
}

QLabel#NavSubtitle {
    color: #a8c2c1;
    font-size: 12px;
}

QListWidget#NavList {
    background: transparent;
    border: none;
    color: #dce8e7;
    outline: none;
}

QListWidget#NavList::item {
    margin: 4px 8px;
    padding: 12px 14px;
    border-radius: 10px;
}

QListWidget#NavList::item:selected {
    background: #2c6a67;
    color: #ffffff;
}

QListWidget#NavList::item:hover:!selected {
    background: #244951;
}

QFrame#SectionCard, QGroupBox {
    background: #fbfaf8;
    border: 1px solid #d5ddd8;
    border-radius: 16px;
}

QFrame#SummaryRow {
    background: #f7f4ef;
    border: 1px solid #e3e9e4;
    border-radius: 10px;
}

QGroupBox {
    margin-top: 12px;
    padding-top: 14px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 4px;
}

QLabel#SectionTitle {
    font-size: 24px;
    font-weight: 700;
    color: #172126;
}

QLabel#SectionLead {
    color: #55646f;
    font-size: 13px;
}

QLabel#MonitorTitle {
    font-size: 18px;
    font-weight: 700;
}

QLabel#MonitorMeta {
    color: #55646f;
}

QLineEdit, QComboBox, QPlainTextEdit, QTextEdit {
    background: #ffffff;
    border: 1px solid #c6d2cb;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #2c6a67;
}

QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #2c6a67;
}

QComboBox::drop-down {
    width: 28px;
    border: none;
}

QPushButton {
    background: #244951;
    color: #ffffff;
    border: 1px solid #1a3940;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background: #2f5d64;
    border: 1px solid #23484f;
}

QPushButton:pressed {
    background: #1b3b42;
    border: 1px solid #163238;
    padding-top: 11px;
    padding-bottom: 9px;
}

QPushButton:focus {
    border: 1px solid #5f9f98;
}

QPushButton:disabled {
    background: #b8c6c4;
    color: #eef3f2;
    border: 1px solid #b8c6c4;
}

QPushButton#SecondaryButton {
    background: #e8efeb;
    color: #18363b;
    border: 1px solid #c6d2cb;
}

QPushButton#SecondaryButton:hover {
    background: #dde8e3;
    border: 1px solid #b2c3bb;
}

QPushButton#SecondaryButton:pressed {
    background: #d0ddd7;
    border: 1px solid #a4b8af;
}

QPushButton#DangerButton {
    background: #8f3a37;
    border: 1px solid #762d2b;
}

QPushButton#DangerButton:hover {
    background: #a34541;
    border: 1px solid #893633;
}

QPushButton#DangerButton:pressed {
    background: #7b2f2d;
    border: 1px solid #682725;
}

QPushButton#PrimaryButton {
    background: #244951;
    border: 1px solid #1a3940;
}

QPushButton#PrimaryButton:hover {
    background: #2f5d64;
    border: 1px solid #23484f;
}

QPushButton#PrimaryButton:pressed {
    background: #1b3b42;
    border: 1px solid #163238;
}

QCheckBox {
    spacing: 8px;
}

QProgressBar {
    background: #e5ece8;
    border: 1px solid #c6d2cb;
    border-radius: 10px;
    text-align: center;
    min-height: 20px;
}

QProgressBar::chunk {
    background: #2c6a67;
    border-radius: 9px;
}

QStatusBar {
    background: #fbfaf8;
    border-top: 1px solid #d5ddd8;
}
"""
