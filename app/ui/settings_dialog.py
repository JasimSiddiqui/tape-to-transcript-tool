"""Settings dialog: model size, language and device."""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..paths import data_dir, models_dir
from ..settings import DEVICES, LANGUAGES, MODEL_SIZES
from ..transcriber import cuda_device_count, is_model_downloaded


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self._settings = dict(settings)

        self.model_combo = QComboBox()
        for value, label in MODEL_SIZES:
            if is_model_downloaded(models_dir(), value):
                label += "  (downloaded)"
            self.model_combo.addItem(label, value)
        self._select(self.model_combo, settings["model_size"])

        self.language_combo = QComboBox()
        for value, label in LANGUAGES:
            self.language_combo.addItem(label, value)
        self._select(self.language_combo, settings["language"])

        self.device_combo = QComboBox()
        for value, label in DEVICES:
            self.device_combo.addItem(label, value)
        self._select(self.device_combo, settings["device"])

        model_hint = self._hint(
            "Larger models are more accurate but slower. Each size is downloaded once, "
            "the first time you use it; after that everything works offline."
        )
        if cuda_device_count() > 0:
            gpu_text = "An NVIDIA GPU was detected. Auto will use it if the CUDA libraries are installed."
        else:
            gpu_text = "No NVIDIA GPU detected, so transcription will run on the CPU."
        device_hint = self._hint(gpu_text)

        form = QFormLayout()
        form.setVerticalSpacing(6)
        form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.addRow("Model size", self.model_combo)
        form.addRow("", model_hint)
        form.addRow("Language", self.language_combo)
        form.addRow("Device", self.device_combo)
        form.addRow("", device_hint)

        folder_label = self._hint(f"Data folder: {data_dir()}")
        folder_button = QPushButton("Open data folder")
        folder_button.setProperty("variant", "link")
        folder_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir()))))

        cancel_button = QPushButton("Cancel")
        cancel_button.setProperty("variant", "secondary")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("Save")
        save_button.setDefault(True)
        save_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(folder_button)
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addWidget(self._hint("Changes apply to the next file that starts transcribing."))
        layout.addWidget(folder_label)
        layout.addLayout(buttons)

    @staticmethod
    def _hint(text):
        label = QLabel(text)
        label.setObjectName("metaLabel")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _select(combo, value):
        index = combo.findData(value)
        combo.setCurrentIndex(max(index, 0))

    def values(self):
        settings = dict(self._settings)
        settings["model_size"] = self.model_combo.currentData()
        settings["language"] = self.language_combo.currentData()
        settings["device"] = self.device_combo.currentData()
        return settings
