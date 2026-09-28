"""The app's two-color palette (red and white) and Qt stylesheet.

Everything is red, white, or a tint/shade of red: the "ink" used for text is a
very dark shade of the red, and the light greys are tints of that ink.
"""

from PySide6.QtGui import QColor, QPalette

from .logo import RED, WHITE

RED_HOVER = "#B00E28"  # red, 12% darker
RED_PRESSED = "#960C22"  # red, 25% darker
RED_TINT = "#FBEBEE"  # 8% red on white: selected rows
RED_TINT_STRONG = "#F4C6CE"  # 25% red on white: focus rings

INK = "#2B1B1E"  # near-black shade of red, for text
TEXT_MUTED = "#85777A"  # secondary text
BORDER = "#E6E2E3"  # 12% ink on white
BORDER_SOFT = "#EFECED"  # 8% ink
HOVER_BG = "#F6F5F5"  # 4% ink
PAGE = "#FAF9F9"  # 2% ink: page background behind white cards
SWITCH_OFF = "#CDC6C7"  # 25% ink: track of a toggle that is off

STYLESHEET = f"""
QWidget {{
    font-family: "Segoe UI";
    font-size: 10pt;
    color: {INK};
}}
QMainWindow, #central {{
    background: {PAGE};
}}
QDialog, QMessageBox, QInputDialog {{
    background: {WHITE};
}}
QToolTip {{
    background: {INK};
    color: {WHITE};
    border: none;
    padding: 4px 8px;
}}

/* Header ---------------------------------------------------------------- */
#header {{
    background: {WHITE};
    border-bottom: 1px solid {BORDER};
}}
#appTitle {{
    font-size: 13pt;
    font-weight: 600;
}}
#appTagline {{
    color: {TEXT_MUTED};
}}

/* Buttons --------------------------------------------------------------- */
QPushButton {{
    background: {RED};
    color: {WHITE};
    border: 1px solid {RED};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {RED_HOVER};
    border-color: {RED_HOVER};
}}
QPushButton:pressed {{
    background: {RED_PRESSED};
    border-color: {RED_PRESSED};
}}
QPushButton:disabled {{
    background: {BORDER_SOFT};
    border-color: {BORDER_SOFT};
    color: {TEXT_MUTED};
}}
QPushButton[variant="secondary"] {{
    background: {WHITE};
    color: {INK};
    border: 1px solid {BORDER};
}}
QPushButton[variant="secondary"]:hover {{
    background: {HOVER_BG};
    border-color: {TEXT_MUTED};
}}
QPushButton[variant="secondary"]:pressed {{
    background: {BORDER_SOFT};
}}
QPushButton[variant="danger"] {{
    background: {WHITE};
    color: {RED};
    border: 1px solid {BORDER};
}}
QPushButton[variant="danger"]:hover {{
    background: {RED_TINT};
    border-color: {RED_TINT_STRONG};
}}
QPushButton[variant="link"] {{
    background: transparent;
    color: {TEXT_MUTED};
    border: none;
    padding: 4px 8px;
    font-weight: 400;
}}
QPushButton[variant="link"]:hover {{
    color: {RED};
    background: transparent;
}}

/* Notice banner --------------------------------------------------------- */
#notice {{
    background: {RED_TINT};
    border-bottom: 1px solid {RED_TINT_STRONG};
}}

/* Cards ----------------------------------------------------------------- */
#queuePanel, #transcriptList, QPlainTextEdit {{
    background: {WHITE};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}

/* Queue ----------------------------------------------------------------- */
#queueScroll, #queueRows {{
    background: transparent;
    border: none;
}}
#queueRow {{
    border-top: 1px solid {BORDER_SOFT};
}}
#queueFileName {{
    font-weight: 600;
}}
#queueStatus, #queueDetail {{
    color: {TEXT_MUTED};
}}
#queueStatus[state="failed"], #queueDetail[state="failed"] {{
    color: {RED};
}}
#queueStatus[state="failed"] {{
    font-weight: 600;
}}

QProgressBar {{
    background: {BORDER_SOFT};
    border: none;
    border-radius: 2px;
    min-height: 4px;
    max-height: 4px;
}}
QProgressBar::chunk {{
    background: {RED};
    border-radius: 2px;
}}

/* Dashboard ------------------------------------------------------------- */
#sectionTitle {{
    font-size: 9pt;
    font-weight: 600;
    color: {TEXT_MUTED};
    letter-spacing: 1px;
}}
#countLabel, #metaLabel, #emptyHint {{
    color: {TEXT_MUTED};
}}
#transcriptTitle {{
    font-size: 17pt;
    font-weight: 600;
}}
#emptyTitle {{
    font-size: 13pt;
    font-weight: 600;
}}

QLineEdit, QComboBox {{
    background: {WHITE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: {RED};
    selection-color: {WHITE};
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {RED};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox::down-arrow {{
    /* A small triangle made from borders, so no image file is needed. */
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {TEXT_MUTED};
}}
QComboBox QAbstractItemView {{
    background: {WHITE};
    border: 1px solid {BORDER};
    selection-background-color: {RED_TINT};
    selection-color: {INK};
    outline: none;
}}

#transcriptList {{
    padding: 4px;
    outline: none;
}}

QPlainTextEdit {{
    padding: 14px 18px;
    font-size: 11pt;
    selection-background-color: {RED_TINT_STRONG};
    selection-color: {INK};
}}

QSplitter::handle {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    height: 0;
    background: none;
}}
"""


def build_palette():
    """A light palette so native-looking dialogs match the stylesheet, even in Windows dark mode."""
    ink = QColor(INK)
    white = QColor(WHITE)
    muted = QColor(TEXT_MUTED)
    palette = QPalette()
    palette.setColor(QPalette.Window, white)
    palette.setColor(QPalette.WindowText, ink)
    palette.setColor(QPalette.Base, white)
    palette.setColor(QPalette.AlternateBase, QColor(HOVER_BG))
    palette.setColor(QPalette.Text, ink)
    palette.setColor(QPalette.PlaceholderText, muted)
    palette.setColor(QPalette.Button, white)
    palette.setColor(QPalette.ButtonText, ink)
    palette.setColor(QPalette.Highlight, QColor(RED))
    palette.setColor(QPalette.HighlightedText, white)
    palette.setColor(QPalette.ToolTipBase, ink)
    palette.setColor(QPalette.ToolTipText, white)
    palette.setColor(QPalette.Disabled, QPalette.Text, muted)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, muted)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, muted)
    return palette
