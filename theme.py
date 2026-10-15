"""Golden dark theme for Vicky Talk.

Palette mirrors design-v1.html. Note: Qt stylesheets (QSS) require the alpha
channel of rgba() as an integer 0-255, so the CSS floats from the design
(.16 / .36) are stored here as 41 / 92.
"""

GOLD = {
    "bg0": "#060402",
    "bg1": "#0a0703",
    "panel": "#100b05",
    "panel2": "#151006",
    "line": "rgba(242, 193, 78, 41)",     # design: rgba(242,193,78,.16)
    "line2": "rgba(242, 193, 78, 92)",    # design: rgba(242,193,78,.36)
    "gold": "#f2c14e",
    "gold2": "#c9962e",
    "champ": "#ffe6ad",
    "text": "#f7ecd4",
    "dim": "#a89a7c",
    "green": "#34d399",
    "amber": "#fbbf24",
    "red": "#f87171",
}


def _qss() -> str:
    g = GOLD
    return f"""
QWidget {{
    background-color: {g['bg1']};
    color: {g['text']};
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background-color: {g['bg0']};
}}
QLabel[heading="true"] {{
    color: {g['dim']};
    font-size: 10px;
    font-weight: 600;
}}
QLabel[pill="true"] {{
    color: {g['gold']};
    font-size: 10px;
    font-weight: 600;
    background: rgba(242, 193, 78, 18);
    border: 1px solid {g['line2']};
    border-radius: 12px;
    padding: 3px 12px;
}}
QToolTip {{
    background-color: {g['panel']};
    color: {g['text']};
    border: 1px solid {g['line2']};
    padding: 6px 10px;
}}

/* ---------- frames / cards ---------- */
QFrame[card="true"] {{
    background-color: {g['panel']};
    border: 1px solid {g['line']};
    border-radius: 14px;
}}
QFrame[card="true"][selected="true"] {{
    border: 1px solid {g['line2']};
    background-color: {g['panel2']};
}}
QFrame[panel="true"] {{
    background-color: rgba(255, 255, 255, 4);
    border: 1px solid {g['line']};
    border-radius: 14px;
}}

/* ---------- buttons ---------- */
QPushButton {{
    background-color: rgba(255, 255, 255, 10);
    border: 1px solid {g['line']};
    color: {g['text']};
    border-radius: 10px;
    padding: 9px 18px;
}}
QPushButton:hover {{
    border: 1px solid {g['line2']};
    color: {g['champ']};
}}
QPushButton:disabled {{
    color: {g['dim']};
    border: 1px solid {g['line']};
    background-color: rgba(255, 255, 255, 4);
}}
QPushButton[gold="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffd97a, stop:1 {g['gold2']});
    color: #2a1c02;
    font-weight: 700;
    border: none;
    border-radius: 18px;
    padding: 12px 34px;
}}
QPushButton[gold="true"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffe6ad, stop:1 {g['gold']});
    color: #2a1c02;
}}
QPushButton[gold="true"]:disabled {{
    background: #3a2c10;
    color: {g['dim']};
}}
QPushButton[nav="true"] {{
    background: transparent;
    border: 1px solid transparent;
    color: {g['dim']};
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 12px;
}}
QPushButton[nav="true"]:hover {{
    color: {g['text']};
}}
QPushButton[nav="true"]:checked {{
    background: rgba(242, 193, 78, 36);
    color: {g['gold']};
    border: 1px solid {g['line2']};
}}
QPushButton[chip="true"] {{
    border-radius: 16px;
    padding: 6px 14px;
    font-size: 11px;
    color: {g['dim']};
}}
QPushButton[chip="true"]:checked {{
    color: {g['gold']};
    border: 1px solid {g['line2']};
    background: rgba(242, 193, 78, 22);
}}
QPushButton[danger="true"]:hover {{
    border: 1px solid rgba(248, 113, 113, 128);
    color: {g['red']};
}}

/* ---------- inputs ---------- */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: #070402;
    border: 1px solid {g['line']};
    border-radius: 10px;
    padding: 8px 12px;
    color: {g['text']};
    selection-background-color: rgba(242, 193, 78, 80);
}}
QLineEdit:focus, QTextEdit:focus {{
    border: 1px solid {g['line2']};
}}
QLineEdit:disabled {{
    color: {g['dim']};
}}
QComboBox {{
    background-color: #070402;
    border: 1px solid {g['line']};
    border-radius: 10px;
    padding: 8px 12px;
    color: {g['text']};
}}
QComboBox QAbstractItemView {{
    background-color: {g['panel']};
    border: 1px solid {g['line2']};
    selection-background-color: rgba(242, 193, 78, 60);
    color: {g['text']};
    outline: none;
}}

/* ---------- progress ---------- */
QProgressBar {{
    background: rgba(255, 255, 255, 14);
    border: 1px solid {g['line']};
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: {g['dim']};
    font-size: 10px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {g['gold']}, stop:1 {g['gold2']});
    border-radius: 5px;
}}

/* ---------- lists ---------- */
QListWidget {{
    background-color: #070402;
    border: 1px solid {g['line']};
    border-radius: 10px;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 8px;
    color: {g['text']};
}}
QListWidget::item:selected {{
    background: rgba(242, 193, 78, 36);
    color: {g['champ']};
}}

/* ---------- checkbox ---------- */
QCheckBox {{
    spacing: 8px;
    color: {g['text']};
}}
QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 10px;
    border: 1px solid {g['line2']};
    background: transparent;
}}
QCheckBox::indicator:checked {{
    background: rgba(52, 211, 153, 40);
    border: 1px solid {g['green']};
}}

/* ---------- scrollbars ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: rgba(242, 193, 78, 60);
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(242, 193, 78, 60);
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ---------- groups / tabs ---------- */
QGroupBox {{
    border: 1px solid {g['line']};
    border-radius: 12px;
    margin-top: 14px;
    padding-top: 10px;
    color: {g['dim']};
    font-size: 11px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {g['dim']};
}}
QTabWidget::pane {{
    border: 1px solid {g['line']};
    border-radius: 10px;
}}
QTabBar::tab {{
    background: transparent;
    color: {g['dim']};
    padding: 8px 20px;
    border: 1px solid transparent;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{
    color: {g['gold']};
    border: 1px solid {g['line2']};
    border-bottom: none;
    background: rgba(242, 193, 78, 24);
}}
"""


def apply_theme(app) -> None:
    """Apply the Vicky Talk dark-gold stylesheet to the whole application."""
    app.setStyleSheet(_qss())


def gold_button_style() -> str:
    """Standalone gold-button QSS for widgets that style themselves directly."""
    g = GOLD
    return (
        "QPushButton {"
        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffd97a, stop:1 {g['gold2']});"
        "color: #2a1c02; font-weight: 700; border: none; border-radius: 18px; padding: 12px 34px;"
        "}"
        "QPushButton:hover {"
        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffe6ad, stop:1 {g['gold']});"
        "}"
        "QPushButton:disabled { background: #3a2c10; color: #a89a7c; }"
    )


def refresh_dynamic_style(widget) -> None:
    """Re-apply QSS after a dynamic property (card/selected/nav/...) changed."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
