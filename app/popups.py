"""Non-modal FocusAI reminders and activity classification prompts."""

from functools import partial

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

ACTIVITY_CATEGORIES = ("PRODUCTIVE", "NEUTRAL", "DISTRACTING")


class FocusPopup(QDialog):
    classification_selected = Signal(str)

    def __init__(self, title, message, parent=None, classification_prompt=False):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setModal(False)
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(message_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        if classification_prompt:
            for category in ACTIVITY_CATEGORIES:
                button = QPushButton(category.title())
                button.setObjectName("PrimaryButton")
                button.clicked.connect(partial(self.choose, category))
                buttons.addWidget(button)
        close_button = QPushButton("Dismiss" if classification_prompt else "Close")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def choose(self, category):
        self.classification_selected.emit(category)
        self.accept()
