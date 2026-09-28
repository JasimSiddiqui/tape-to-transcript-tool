"""The transcription queue: one row per added file."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .widgets import ElidedLabel

QUEUED = "Queued"
TRANSCRIBING = "Transcribing"
DONE = "Done"
FAILED = "Failed"
CANCELLED = "Cancelled"
FINISHED_STATES = (DONE, FAILED, CANCELLED)
MAX_ROWS_HEIGHT = 180


class QueueRow(QFrame):
    action_clicked = Signal(int)  # job id

    def __init__(self, job_id, path, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.state = QUEUED
        self.activity = QUEUED
        self.setObjectName("queueRow")

        self.name_label = ElidedLabel(Path(path).name)
        self.name_label.setObjectName("queueFileName")
        self.name_label.setToolTip(path)

        self.status_label = QLabel(QUEUED)
        self.status_label.setObjectName("queueStatus")

        self.action_button = QPushButton("Remove")
        self.action_button.setProperty("variant", "link")
        self.action_button.setCursor(Qt.PointingHandCursor)
        self.action_button.clicked.connect(lambda: self.action_clicked.emit(self.job_id))

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.detail_label = QLabel()
        self.detail_label.setObjectName("queueDetail")
        self.detail_label.setWordWrap(True)
        self.detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.detail_label.hide()

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self.name_label, 1)
        top.addWidget(self.status_label)
        top.addWidget(self.action_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 8, 10)
        layout.setSpacing(6)
        layout.addLayout(top)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.detail_label)

    def set_state(self, state, detail=""):
        self.state = state
        self.activity = state
        self.status_label.setText(state)
        for label in (self.status_label, self.detail_label):
            label.setProperty("state", "failed" if state == FAILED else "")
            label.style().unpolish(label)
            label.style().polish(label)

        self.action_button.setEnabled(True)
        if state == QUEUED:
            self.action_button.setText("Remove")
        elif state == TRANSCRIBING:
            self.action_button.setText("Cancel")
        else:
            self.action_button.setText("Dismiss")

        self.progress_bar.setVisible(state in (QUEUED, TRANSCRIBING))
        if state == DONE:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
        self.detail_label.setText(detail)
        self.detail_label.setVisible(bool(detail))

    def set_activity(self, text):
        """Sub-status while transcribing, e.g. 'Downloading model…'."""
        if self.state == TRANSCRIBING:
            self.activity = text
            self._show_activity()

    def set_progress(self, percent):
        if percent < 0:
            self.progress_bar.setRange(0, 0)  # animated "busy" bar
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)
        self._show_activity()

    def _show_activity(self):
        if self.state != TRANSCRIBING:
            return
        text = self.activity
        if text == TRANSCRIBING and self.progress_bar.maximum() > 0:
            text = f"{TRANSCRIBING} {self.progress_bar.value()}%"
        self.status_label.setText(text)

    def set_cancelling(self):
        self.status_label.setText("Cancelling…")
        self.action_button.setEnabled(False)


class QueuePanel(QFrame):
    """Card listing queued/active/finished files. Hidden by the window when empty."""

    action_clicked = Signal(int)  # job id
    clear_finished_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("queuePanel")
        self.rows = {}

        title = QLabel("QUEUE")
        title.setObjectName("sectionTitle")
        self.count_label = QLabel()
        self.count_label.setObjectName("countLabel")
        self.clear_button = QPushButton("Clear finished")
        self.clear_button.setProperty("variant", "link")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_finished_clicked)

        header = QHBoxLayout()
        header.setContentsMargins(14, 10, 8, 6)
        header.addWidget(title)
        header.addSpacing(8)
        header.addWidget(self.count_label)
        header.addStretch(1)
        header.addWidget(self.clear_button)

        self.rows_widget = QWidget()
        self.rows_widget.setObjectName("queueRows")
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.rows_layout.addStretch(1)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("queueScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.rows_widget)
        self.scroll.viewport().setAutoFillBackground(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self.scroll)

    def add_row(self, job_id, path):
        row = QueueRow(job_id, path)
        row.action_clicked.connect(self.action_clicked)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        self.rows[job_id] = row
        self._update_summary()
        return row

    def remove_row(self, job_id):
        row = self.rows.pop(job_id, None)
        if row is not None:
            row.setParent(None)
            row.deleteLater()
        self._update_summary()

    def row(self, job_id):
        return self.rows.get(job_id)

    def refresh(self):
        self._update_summary()

    def _update_summary(self):
        states = [row.state for row in self.rows.values()]
        waiting = sum(1 for s in states if s in (QUEUED, TRANSCRIBING))
        finished = len(states) - waiting
        parts = []
        if waiting:
            parts.append(f"{waiting} in progress" if waiting == 1 else f"{waiting} remaining")
        if finished:
            parts.append(f"{finished} finished")
        self.count_label.setText(" · ".join(parts))
        self.clear_button.setVisible(finished > 0)

        # Grow with the rows, up to about three of them, then scroll.
        width = self.scroll.viewport().width()
        total = sum(
            row.heightForWidth(width) if row.hasHeightForWidth() else row.sizeHint().height()
            for row in self.rows.values()
        )
        self.scroll.setFixedHeight(min(max(total, 1), MAX_ROWS_HEIGHT))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_summary()  # wrapped error messages change height with the width
