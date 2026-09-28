"""Main window: header, transcription queue, and the transcript dashboard."""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, QStandardPaths, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_VERSION
from ..database import Database
from ..formatting import build_text, format_duration
from ..paths import database_path, log_path, models_dir, setup_logging
from ..settings import load_settings, save_settings
from ..transcriber import TranscriptionWorker
from . import style
from .logo import logo_icon, logo_pixmap
from .queue_panel import CANCELLED, DONE, FAILED, FINISHED_STATES, QUEUED, TRANSCRIBING, QueuePanel
from .settings_dialog import SettingsDialog
from .widgets import ToggleSwitch

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4a", ".mp3", ".wav"}
FILE_FILTER = "Videos and audio (*.mp4 *.mkv *.mov *.webm *.avi *.m4a *.mp3 *.wav);;All files (*.*)"
META_ROLE = Qt.UserRole + 1
LANGUAGE_NAMES = {"en": "English"}


def safe_filename(title):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")
    return name[:150] or "transcript"


class TranscriptDelegate(QStyledItemDelegate):
    """Draws each saved transcript as a bold title with a muted date/duration line."""

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), option.fontMetrics.height() * 2 + 26)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        rect = option.rect.adjusted(2, 2, -2, -2)
        if selected or hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(style.RED_TINT if selected else style.HOVER_BG))
            painter.drawRoundedRect(rect, 6, 6)
        if selected:  # red accent bar on the left edge
            painter.setBrush(QColor(style.RED))
            painter.drawRoundedRect(rect.left(), rect.top() + 10, 3, rect.height() - 20, 1.5, 1.5)

        text_rect = rect.adjusted(12, 8, -12, -8)
        title_font = QFont(option.font)
        title_font.setWeight(QFont.DemiBold)
        title_metrics = QFontMetrics(title_font)
        painter.setFont(title_font)
        painter.setPen(QColor(style.RED if selected else style.INK))
        title = title_metrics.elidedText(index.data(Qt.DisplayRole), Qt.ElideRight, text_rect.width())
        painter.drawText(text_rect.left(), text_rect.top() + title_metrics.ascent(), title)

        meta_metrics = QFontMetrics(option.font)
        painter.setFont(option.font)
        painter.setPen(QColor(style.TEXT_MUTED))
        meta = meta_metrics.elidedText(index.data(META_ROLE) or "", Qt.ElideRight, text_rect.width())
        painter.drawText(text_rect.left(), text_rect.bottom() - meta_metrics.descent(), meta)
        painter.restore()


class Job:
    def __init__(self, job_id, path):
        self.id = job_id
        self.path = path
        self.status = QUEUED


class MainWindow(QMainWindow):
    start_job = Signal(int, str, object)  # job id, file path, settings

    def __init__(self, db: Database, settings: dict):
        super().__init__()
        self.db = db
        self.settings = settings
        self.jobs = {}  # job id -> Job, in the order they were added
        self.next_job_id = 1
        self.current_job_id = None
        self.current_transcript_id = None
        self.current_segments = []
        self.last_save_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(logo_icon())
        self.setMinimumSize(900, 600)
        self.resize(1200, 780)
        self.setAcceptDrops(True)

        self._build_ui()
        self._start_worker()
        self.refresh_list()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_notice())

        body = QVBoxLayout()
        body.setContentsMargins(20, 16, 20, 20)
        body.setSpacing(16)
        root.addLayout(body, 1)

        self.queue_panel = QueuePanel()
        self.queue_panel.action_clicked.connect(self._on_queue_action)
        self.queue_panel.clear_finished_clicked.connect(self._clear_finished)
        self.queue_panel.hide()
        body.addWidget(self.queue_panel)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(16)
        splitter.addWidget(self._build_list_side())
        splitter.addWidget(self._build_detail_side())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 860])
        body.addWidget(splitter, 1)

    def _build_header(self):
        header = QFrame()
        header.setObjectName("header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(logo_pixmap(30, self.devicePixelRatioF()))
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        tagline = QLabel("Offline lecture transcription")
        tagline.setObjectName("appTagline")

        add_button = QPushButton("Add Videos")
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(self._choose_files)

        settings_button = QPushButton("Settings")
        settings_button.setProperty("variant", "secondary")
        settings_button.setCursor(Qt.PointingHandCursor)
        settings_button.clicked.connect(self._open_settings)

        layout.addWidget(logo)
        layout.addSpacing(2)
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(tagline)
        layout.addStretch(1)
        layout.addWidget(settings_button)
        layout.addWidget(add_button)
        return header

    def _build_notice(self):
        self.notice_frame = QFrame()
        self.notice_frame.setObjectName("notice")
        layout = QHBoxLayout(self.notice_frame)
        layout.setContentsMargins(20, 8, 12, 8)
        self.notice_label = QLabel()
        self.notice_label.setWordWrap(True)
        dismiss = QPushButton("Dismiss")
        dismiss.setProperty("variant", "link")
        dismiss.setCursor(Qt.PointingHandCursor)
        dismiss.clicked.connect(self.notice_frame.hide)
        layout.addWidget(self.notice_label, 1)
        layout.addWidget(dismiss)
        self.notice_frame.hide()

        self.notice_timer = QTimer(self)
        self.notice_timer.setSingleShot(True)
        self.notice_timer.timeout.connect(self.notice_frame.hide)
        return self.notice_frame

    def _build_list_side(self):
        side = QWidget()
        side.setMinimumWidth(240)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("TRANSCRIPTS")
        title.setObjectName("sectionTitle")
        self.count_label = QLabel()
        self.count_label.setObjectName("countLabel")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.count_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search titles and text…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(200)
        self.search_timer.timeout.connect(self.refresh_list)
        self.search_edit.textChanged.connect(self.search_timer.start)

        self.transcript_list = QListWidget()
        self.transcript_list.setObjectName("transcriptList")
        self.transcript_list.setItemDelegate(TranscriptDelegate(self.transcript_list))
        self.transcript_list.setMouseTracking(True)
        self.transcript_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.transcript_list.currentItemChanged.connect(self._on_selection_changed)

        layout.addLayout(header)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.transcript_list, 1)
        return side

    def _build_detail_side(self):
        self.detail_stack = QStackedWidget()
        self.detail_stack.setMinimumWidth(560)

        # Page 0: empty state.
        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch(1)
        empty_logo = QLabel()
        empty_logo.setPixmap(logo_pixmap(56, self.devicePixelRatioF()))
        empty_logo.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_logo)
        empty_layout.addSpacing(10)
        self.empty_title = QLabel()
        self.empty_title.setObjectName("emptyTitle")
        self.empty_title.setAlignment(Qt.AlignCenter)
        self.empty_hint = QLabel()
        self.empty_hint.setObjectName("emptyHint")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setWordWrap(True)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_hint)
        empty_layout.addStretch(2)
        self.detail_stack.addWidget(empty)

        # Page 1: the selected transcript.
        detail = QWidget()
        layout = QVBoxLayout(detail)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.title_label = QLabel()
        self.title_label.setObjectName("transcriptTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.meta_label = QLabel()
        self.meta_label.setObjectName("metaLabel")
        self.timestamps_check = ToggleSwitch("Include timestamps")
        self.timestamps_check.setChecked(self.settings["include_timestamps"])
        self.timestamps_check.toggled.connect(self._on_timestamps_toggled)
        meta_row = QHBoxLayout()
        meta_row.addWidget(self.meta_label, 1)
        meta_row.addWidget(self.timestamps_check)

        self.copy_button = QPushButton("Copy")
        self.copy_button.setCursor(Qt.PointingHandCursor)
        self.copy_button.clicked.connect(self._copy_plain)
        # Keep the width steady when the text briefly changes to "Copied!".
        self.copy_button.setText("Copied!")
        copied_width = self.copy_button.sizeHint().width()
        self.copy_button.setText("Copy")
        self.copy_button.setMinimumWidth(max(self.copy_button.sizeHint().width(), copied_width))
        download_button = self._secondary_button("Download .txt", self._download_txt)
        rename_button = self._secondary_button("Rename", self._rename)
        delete_button = self._secondary_button("Delete", self._delete)
        delete_button.setProperty("variant", "danger")

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.copy_button)
        actions.addWidget(download_button)
        actions.addStretch(1)
        actions.addWidget(rename_button)
        actions.addWidget(delete_button)

        self.text_view = QPlainTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        layout.addWidget(self.title_label)
        layout.addLayout(meta_row)
        layout.addLayout(actions)
        layout.addWidget(self.text_view, 1)
        self.detail_stack.addWidget(detail)
        return self.detail_stack

    def _secondary_button(self, text, slot):
        button = QPushButton(text)
        button.setProperty("variant", "secondary")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def show_notice(self, message, timeout_ms=15000):
        self.notice_label.setText(message)
        self.notice_frame.show()
        self.notice_timer.start(timeout_ms)

    # -------------------------------------------------------------- worker

    def _start_worker(self):
        self.worker_thread = QThread(self)
        self.worker = TranscriptionWorker(models_dir())
        self.worker.moveToThread(self.worker_thread)
        self.start_job.connect(self.worker.run_job)
        self.worker.status.connect(self._on_job_status)
        self.worker.progress.connect(self._on_job_progress)
        self.worker.finished.connect(self._on_job_finished)
        self.worker.failed.connect(self._on_job_failed)
        self.worker.cancelled.connect(self._on_job_cancelled)
        self.worker.notice.connect(self.show_notice)
        self.worker_thread.start()

    def add_files(self, paths):
        added = 0
        skipped = []
        for path in paths:
            path = os.path.abspath(path)
            if Path(path).suffix.lower() not in SUPPORTED_EXTENSIONS or not os.path.isfile(path):
                skipped.append(Path(path).name)
                continue
            job = Job(self.next_job_id, path)
            self.next_job_id += 1
            self.jobs[job.id] = job
            self.queue_panel.add_row(job.id, path)
            added += 1
        if skipped:
            self.show_notice("Skipped unsupported files: " + ", ".join(skipped))
        if added:
            self._update_queue_visibility()
            self._start_next_job()

    def _choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add videos", "", FILE_FILTER)
        if paths:
            self.add_files(paths)

    def _start_next_job(self):
        if self.current_job_id is not None:
            return
        job = next((j for j in self.jobs.values() if j.status == QUEUED), None)
        if job is None:
            return
        job.status = TRANSCRIBING
        self.current_job_id = job.id
        self.queue_panel.row(job.id).set_state(TRANSCRIBING)
        self.queue_panel.refresh()
        self.worker.cancel_event.clear()
        self.start_job.emit(job.id, job.path, dict(self.settings))

    def _finish_job(self, job_id, status, detail=""):
        job = self.jobs.get(job_id)
        if job is not None:
            job.status = status
            row = self.queue_panel.row(job_id)
            if row is not None:
                row.set_state(status, detail)
            self.queue_panel.refresh()
        if self.current_job_id == job_id:
            self.current_job_id = None
        self._start_next_job()

    def _on_job_status(self, job_id, text):
        row = self.queue_panel.row(job_id)
        if row is not None:
            row.set_activity(text)

    def _on_job_progress(self, job_id, percent):
        row = self.queue_panel.row(job_id)
        if row is not None:
            row.set_progress(percent)

    def _on_job_finished(self, job_id, result):
        job = self.jobs.get(job_id)
        try:
            segments = result["segments"]
            transcript_id = self.db.add_transcript(
                title=Path(job.path).stem,
                source_path=job.path,
                duration=result["duration"],
                language=result["language"],
                model=result["model"],
                segments=segments,
                text=build_text(segments),
            )
        except Exception:
            log.exception("Saving transcript failed")
            self._finish_job(job_id, FAILED, "The transcript couldn't be saved. See the log file for details.")
            return
        self._finish_job(job_id, DONE)
        # Jump to the new transcript unless the user is already reading another one.
        self.refresh_list(select_id=transcript_id if self.current_transcript_id is None else None)

    def _on_job_failed(self, job_id, message):
        self._finish_job(job_id, FAILED, message)

    def _on_job_cancelled(self, job_id):
        self._finish_job(job_id, CANCELLED)

    def _on_queue_action(self, job_id):
        job = self.jobs.get(job_id)
        if job is None:
            return
        if job.status == TRANSCRIBING:
            self.worker.cancel_event.set()
            self.queue_panel.row(job_id).set_cancelling()
        else:  # queued (remove) or finished (dismiss)
            del self.jobs[job_id]
            self.queue_panel.remove_row(job_id)
            self._update_queue_visibility()

    def _clear_finished(self):
        for job_id in [j.id for j in self.jobs.values() if j.status in FINISHED_STATES]:
            del self.jobs[job_id]
            self.queue_panel.remove_row(job_id)
        self._update_queue_visibility()

    def _update_queue_visibility(self):
        self.queue_panel.setVisible(bool(self.jobs))

    # ----------------------------------------------------------- dashboard

    def refresh_list(self, select_id=None):
        if select_id is None:
            select_id = self.current_transcript_id
        query = self.search_edit.text()
        rows = self.db.list_transcripts(query)

        self.transcript_list.blockSignals(True)
        self.transcript_list.clear()
        select_row = 0
        for i, row in enumerate(rows):
            created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
            item = QListWidgetItem(row["title"])
            item.setData(Qt.UserRole, row["id"])
            item.setData(META_ROLE, f"{created:%b %d, %Y}  ·  {format_duration(row['duration'])}")
            item.setToolTip(row["title"])
            self.transcript_list.addItem(item)
            if row["id"] == select_id:
                select_row = i
        self.transcript_list.blockSignals(False)

        total = len(rows)
        self.count_label.setText(f"{total} found" if query.strip() else (str(total) if total else ""))

        if rows:
            self.transcript_list.setCurrentRow(select_row)
            self._on_selection_changed(self.transcript_list.currentItem(), None)
        else:
            self._show_empty_state(bool(query.strip()))

    def _show_empty_state(self, searching):
        self.current_transcript_id = None
        self.current_segments = []
        if searching:
            self.empty_title.setText("No matches")
            self.empty_hint.setText("No transcripts match your search.")
        else:
            self.empty_title.setText("No transcripts yet")
            self.empty_hint.setText(
                "Click “Add Videos” or drop lecture videos onto this window.\n"
                "Transcripts are saved here automatically when they finish."
            )
        self.detail_stack.setCurrentIndex(0)

    def _on_selection_changed(self, current, _previous):
        if current is None:
            return
        transcript_id = current.data(Qt.UserRole)
        row = self.db.get_transcript(transcript_id)
        if row is None:
            return
        self.current_transcript_id = transcript_id
        self.current_segments = self.db.get_segments(transcript_id)

        created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
        meta = [f"{created:%b %d, %Y at %I:%M %p}".replace(" 0", " "), format_duration(row["duration"])]
        if row["language"]:
            meta.append(LANGUAGE_NAMES.get(row["language"], row["language"].upper()))
        if row["model"]:
            meta.append(f"{row['model']} model")
        self.title_label.setText(row["title"])
        self.meta_label.setText("  ·  ".join(meta))
        self._render_text()
        self.detail_stack.setCurrentIndex(1)

    def _render_text(self):
        self.text_view.setPlainText(self._current_text())
        self.text_view.verticalScrollBar().setValue(0)

    def _current_text(self):
        return build_text(self.current_segments, self.timestamps_check.isChecked())

    def _on_timestamps_toggled(self, checked):
        self.settings["include_timestamps"] = checked
        save_settings(self.settings)
        if self.current_transcript_id is not None:
            self._render_text()

    def _flash(self, button, text="Copied!"):
        original = button.text()
        button.setText(text)
        QTimer.singleShot(1500, lambda: button.setText(original))

    def _copy_plain(self):
        if self.current_transcript_id is None or self.copy_button.text() == "Copied!":
            return
        QGuiApplication.clipboard().setText(self._current_text())
        self._flash(self.copy_button)

    def _download_txt(self):
        if self.current_transcript_id is None:
            return
        default = os.path.join(self.last_save_dir, safe_filename(self.title_label.text()) + ".txt")
        path, _ = QFileDialog.getSaveFileName(self, "Save transcript", default, "Text files (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(self._current_text() + "\n")
        except OSError as exc:
            log.exception("Saving .txt failed")
            QMessageBox.warning(self, "Couldn't save file", f"The file couldn't be saved:\n{exc.strerror or exc}")
            return
        self.last_save_dir = os.path.dirname(path)

    def _rename(self):
        if self.current_transcript_id is None:
            return
        title, ok = QInputDialog.getText(self, "Rename transcript", "Title:", text=self.title_label.text())
        title = title.strip()
        if ok and title:
            self.db.rename_transcript(self.current_transcript_id, title)
            self.refresh_list()

    def _delete(self):
        if self.current_transcript_id is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete transcript",
            f"Delete “{self.title_label.text()}”?\n\nThis can't be undone.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if answer == QMessageBox.Yes:
            self.db.delete_transcript(self.current_transcript_id)
            self.current_transcript_id = None
            self.refresh_list()

    def _open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.values()
            save_settings(self.settings)

    # --------------------------------------------------------- drag & drop

    def _dropped_paths(self, event):
        if not event.mimeData().hasUrls():
            return []
        return [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]

    def dragEnterEvent(self, event):
        if any(Path(p).suffix.lower() in SUPPORTED_EXTENSIONS for p in self._dropped_paths(event)):
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = self._dropped_paths(event)
        if paths:
            event.acceptProposedAction()
            self.add_files(paths)

    # -------------------------------------------------------------- closing

    def closeEvent(self, event):
        if self.current_job_id is not None:
            answer = QMessageBox.question(
                self,
                "Transcription in progress",
                "A video is still being transcribed. Quit anyway? Its progress will be lost.",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        save_settings(self.settings)
        self.worker.cancel_event.set()
        self.worker_thread.quit()
        if not self.worker_thread.wait(5000):
            # The worker is stuck inside a long model call; don't hang or crash on exit.
            log.warning("Worker thread did not stop in time; exiting immediately")
            self.db.close()
            logging.shutdown()
            os._exit(0)
        event.accept()


# ------------------------------------------------------------------ startup


def _log_uncaught(exc_type, exc, tb):
    log.critical("Unexpected error", exc_info=(exc_type, exc, tb))
    if QApplication.instance() is not None:
        QMessageBox.warning(
            None,
            APP_NAME,
            f"Something went wrong: {exc}\n\nDetails were written to:\n{log_path()}",
        )


def run(file_args):
    setup_logging()
    log.info("Starting %s %s (Python %s)", APP_NAME, APP_VERSION, sys.version.split()[0])
    sys.excepthook = _log_uncaught

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    if hasattr(app.styleHints(), "setColorScheme"):
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setPalette(style.build_palette())
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(style.STYLESHEET)
    app.setWindowIcon(logo_icon())

    try:
        db = Database(database_path())
    except Exception as exc:
        log.exception("Could not open database")
        QMessageBox.critical(None, APP_NAME, f"The transcript database couldn't be opened:\n{exc}")
        return 1

    window = MainWindow(db, load_settings())
    window.show()
    if file_args:
        window.add_files(file_args)
    code = app.exec()
    db.close()
    log.info("Exiting")
    return code
