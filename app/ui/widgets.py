"""Small custom widgets, drawn in code so no image files are needed."""

from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QCheckBox, QLabel, QSizePolicy

from . import style


class ElidedLabel(QLabel):
    """A single-line label that shortens long text with an ellipsis instead of growing."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)

    def paintEvent(self, event):
        painter = QPainter(self)
        elided = self.fontMetrics().elidedText(self.text(), Qt.ElideMiddle, self.width())
        painter.drawText(self.rect(), Qt.AlignLeft | Qt.AlignVCenter, elided)


class ToggleSwitch(QCheckBox):
    """A pill-shaped on/off switch with a text label to its right."""

    TRACK_WIDTH = 36
    TRACK_HEIGHT = 20
    GAP = 10

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        metrics = self.fontMetrics()
        width = self.TRACK_WIDTH + self.GAP + metrics.horizontalAdvance(self.text()) + 2
        return QSize(width, max(self.TRACK_HEIGHT, metrics.height()) + 4)

    def minimumSizeHint(self):
        return self.sizeHint()

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        on = self.isChecked()
        top = (self.height() - self.TRACK_HEIGHT) / 2

        track = QRectF(0.5, top + 0.5, self.TRACK_WIDTH - 1, self.TRACK_HEIGHT - 1)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(style.RED if on else style.SWITCH_OFF))
        painter.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        knob_size = self.TRACK_HEIGHT - 6
        knob_left = self.TRACK_WIDTH - knob_size - 3 if on else 3
        painter.setBrush(QColor(style.WHITE))
        painter.drawEllipse(QRectF(knob_left, top + 3, knob_size, knob_size))

        painter.setPen(QColor(style.INK))
        text_left = self.TRACK_WIDTH + self.GAP
        painter.drawText(
            QRect(text_left, 0, self.width() - text_left, self.height()),
            Qt.AlignLeft | Qt.AlignVCenter,
            self.text(),
        )
