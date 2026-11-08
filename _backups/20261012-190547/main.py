import sys
import sqlite3
import threading
from datetime import datetime
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from PySide6.QtCore import QDate, QEasingCurve, QPropertyAnimation, Qt, QSettings, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QProgressBar,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QSpinBox,
    QComboBox,
    QMessageBox,
    QCheckBox,
    QDateEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)

from database.session_db import (
    initialize_database,
    create_session,
    finish_session,
    get_sessions,
)
from database.activity_db import (
    initialize_activity_database,
    add_session_id_column,
    get_session_activities,
)
from screen.focus_monitor import FocusMonitor

DATABASE_PATH = "database/focusai.db"
DEFAULT_SESSION_DURATION_MINUTES = 25
MAX_SESSION_DURATION_MINUTES = 4 * 60 + 59


class FocusAI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusAI")
        self.setMinimumSize(1100, 720)

        self.settings = QSettings("FocusAI", "FocusAI")
        try:
            saved_duration_minutes = int(
                self.settings.value(
                    "session_duration_minutes",
                    DEFAULT_SESSION_DURATION_MINUTES,
                )
            )
        except (TypeError, ValueError):
            saved_duration_minutes = DEFAULT_SESSION_DURATION_MINUTES
        if not 1 <= saved_duration_minutes <= MAX_SESSION_DURATION_MINUTES:
            saved_duration_minutes = DEFAULT_SESSION_DURATION_MINUTES

        self.session_duration = saved_duration_minutes * 60
        self.remaining_seconds = self.session_duration
        self.session_running = False
        self.session_start_time = None
        self.current_session_id = None
        self.dashboard_session_id = None
        self.focus_monitor = None
        self.monitor_thread = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        self.build_ui()

        sessions = get_sessions()
        if sessions:
            self.dashboard_session_id = sessions[0][0]
        self.refresh_dashboard()
        self.show_page(0)

    def build_ui(self):
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root = QHBoxLayout(root_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 30, 22, 24)
        side.setSpacing(10)

        logo = QLabel("FocusAI")
        logo.setObjectName("Logo")
        subtitle = QLabel("Study Assistant")
        subtitle.setObjectName("SidebarSub")
        side.addWidget(logo)
        side.addWidget(subtitle)
        side.addSpacing(28)

        self.nav_buttons = []
        nav_items = [
            ("Dashboard", self.open_dashboard),
            ("Sessions", self.open_sessions),
            ("Analytics", self.open_analytics),
        ]
        for label, handler in nav_items:
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(44)
            button.setFocusPolicy(Qt.StrongFocus)
            button.clicked.connect(handler)
            side.addWidget(button)
            self.nav_buttons.append(button)

        side.addStretch()
        self.status = QLabel("● System Ready")
        self.status.setObjectName("Status")
        side.addWidget(self.status)
        sidebar.setEnabled(True)
        root.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.setObjectName("Pages")
        self.pages.setEnabled(True)
        root.addWidget(self.pages, 1)

        self.build_dashboard_page()
        self.build_sessions_page()
        self.build_analytics_page()

        self.setStyleSheet("""
            QMainWindow { background: #F6F8FC; color: #25334A; font-family: Segoe UI; }
            QWidget { color: #25334A; font-family: Segoe UI; }
            QLabel { background: transparent; border: none; }
            #Pages { background: #F6F8FC; }
            #Sidebar { background: #FFFFFF; border-right: 1px solid #E7ECF3; }
            #Logo { font-size: 28px; font-weight: 750; color: #25334A; }
            #SidebarSub { color: #7D8A9D; font-size: 12px; }
            #Status { color: #348568; font-size: 12px; padding: 8px 0; }
            #Description, #Muted { color: #738196; font-size: 13px; }
            QPushButton { background: #FFFFFF; color: #44536A; border: 1px solid #DCE4EF;
                          border-radius: 9px; padding: 10px 14px; text-align: left; font-size: 14px; }
            QPushButton:hover { background: #F2F6FC; border-color: #B8C9E2; }
            QPushButton:pressed { background: #E8EFF9; }
            QPushButton:checked { background: #EDF3FC; border: 1px solid #D5E2F5; color: #3768B1; }
            QPushButton:disabled { background: #F3F5F8; color: #9AA5B4; border-color: #E5E9EF; }
            #StartButton { background: #4778C7; color: #FFFFFF; border: none; font-size: 15px;
                           font-weight: 700; text-align: center; margin-top: 8px; border-radius: 9px; }
            #StartButton:hover { background: #3D6FBF; }
            #SmallButton { padding: 8px 13px; text-align: center; }
            #Heading { font-size: 28px; font-weight: 700; color: #25334A; }
            #Card { background: #FFFFFF; border: 1px solid #E4EAF2; border-radius: 14px; }
            #Card[tone="productive"] { border-bottom: 3px solid #49A887; }
            #Card[tone="neutral"] { border-bottom: 3px solid #9AA6B5; }
            #Card[tone="distracting"] { border-bottom: 3px solid #E78C83; }
            #CardTitle { color: #758399; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
            #BigScore { font-size: 48px; font-weight: 750; color: #4778C7; padding: 2px; }
            #StatTitle { color: #758399; font-size: 11px; font-weight: 700; }
            #StatValue { font-size: 23px; font-weight: 650; color: #25334A; }
            #SectionTitle { font-size: 17px; font-weight: 650; color: #2C3B53; }
            #Timer { font-size: 30px; font-weight: 750; color: #4778C7; }
            QProgressBar { background: #E9EEF5; color: #52627A; border: none; border-radius: 5px; }
            QProgressBar::chunk { background: #4778C7; border-radius: 5px; }
            #ProductiveBar::chunk { background: #49A887; }
            #NeutralBar::chunk { background: #9AA6B5; }
            #DistractingBar::chunk { background: #E78C83; }
            QSpinBox, QComboBox { background: #FFFFFF; color: #34445B; border: 1px solid #D8E1EC;
                                  border-radius: 9px; padding: 9px 12px; font-size: 14px; }
            QSpinBox:focus, QComboBox:focus { border: 1px solid #4778C7; }
            QSpinBox { selection-background-color: #4778C7; selection-color: #FFFFFF; }
            QSpinBox { padding-right: 38px; }
            QSpinBox::up-button {
                subcontrol-origin: border; subcontrol-position: top right;
                width: 30px; height: 23px; padding: 1px;
                background: #E8EFF8; border: 1px solid #C7D4E5;
                border-top-right-radius: 8px; border-bottom: 1px solid #C7D4E5;
            }
            QSpinBox::down-button {
                subcontrol-origin: border; subcontrol-position: bottom right;
                width: 30px; height: 23px; padding: 1px;
                background: #E8EFF8; border: 1px solid #C7D4E5;
                border-bottom-right-radius: 8px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #DCE8F7; }
            QSpinBox::up-button:pressed, QSpinBox::down-button:pressed { background: #C9DAF0; }
            QComboBox { combobox-popup: 0; }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF; color: #34445B;
                border: 1px solid #D8E1EC; outline: 0;
                selection-background-color: #EDF3FC; selection-color: #3768B1;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item { min-height: 30px; padding: 6px 10px; }
            QComboBox QAbstractItemView::item:hover { background-color: #F2F6FC; color: #25334A; }
            #SettingsHero { background: #EDF3FC; border: 1px solid #DDE8F7; border-radius: 14px; }
            #SettingsIcon { background: #DCE8F8; color: #4778C7; border-radius: 14px; font-size: 34px; font-weight: 700; }
            #SettingsHeroTitle { color: #25334A; font-size: 18px; font-weight: 700; }
            #DurationBadge { background: #EDF3FC; color: #3768B1; border: 1px solid #D8E4F5;
                             border-radius: 10px; padding: 6px 10px; font-size: 11px; font-weight: 700; }
            #PresetHeader { color: #758399; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
            #SettingsHint { background: #F7F9FC; color: #738196; border: 1px solid #E4EAF2;
                            border-radius: 9px; padding: 11px; font-size: 12px; }
            #SettingsSaveButton { background: #4778C7; color: #FFFFFF; border: none; border-radius: 9px;
                                  font-size: 15px; font-weight: 700; text-align: center; }
            #SettingsSaveButton:hover { background: #3D6FBF; }
            #SettingsStatus { color: #348568; font-size: 12px; padding-top: 3px; }
            QListWidget { background: #FFFFFF; color: #34445B; border: 1px solid #E1E7F0;
                          border-radius: 10px; padding: 7px; outline: none; }
            QListWidget::item { padding: 12px; border-radius: 7px; }
            QListWidget::item:hover { background: #F2F6FC; }
            QListWidget::item:selected { background: #EDF3FC; color: #2F5FAD; }
            QTableWidget { background: #FFFFFF; color: #34445B; border: 1px solid #E1E7F0;
                           border-radius: 10px; gridline-color: #EDF1F6; selection-background-color: #EDF3FC;
                           selection-color: #2F5FAD; }
            QHeaderView::section { background: #F7F9FC; color: #758399; border: none;
                                   border-bottom: 1px solid #E4EAF2; padding: 8px; font-weight: 700; }
            QTableWidget::item { padding: 6px; }
            QCheckBox { spacing: 7px; color: #52627A; }
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: #EDF1F6; width: 10px; margin: 2px; border: none; }
            QScrollBar::handle:vertical { background: #C4CFDD; min-height: 28px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #AAB8CA; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)
        arrow_assets = Path(__file__).resolve().parent / "assets"
        self.setStyleSheet(self.styleSheet() + f"""
            QSpinBox::up-arrow {{
                image: url("{(arrow_assets / "spin-up.svg").as_posix()}");
                width: 10px; height: 8px;
            }}
            QSpinBox::down-arrow {{
                image: url("{(arrow_assets / "spin-down.svg").as_posix()}");
                width: 10px; height: 8px;
            }}
        """)

    def make_page(self, title, description=None):
        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 26)
        layout.setSpacing(18)
        heading = QLabel(title)
        heading.setObjectName("Heading")
        layout.addWidget(heading)
        if description:
            label = QLabel(description)
            label.setObjectName("Description")
            label.setWordWrap(True)
            layout.addWidget(label)
        return page, layout

    @staticmethod
    def wrap_page(page):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    def make_card(self, title, value):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 15, 18, 15)
        title_label = QLabel(title.upper())
        title_label.setObjectName("StatTitle")
        value_label = QLabel(value)
        value_label.setObjectName("StatValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def build_dashboard_page(self):
        page, layout = self.make_page(
            "Good to see you 👋",
            "Track your study time and understand where your attention goes."
        )
        header_row = QHBoxLayout()
        header_row.addStretch()
        refresh = QPushButton("↻ Refresh")
        refresh.setObjectName("SmallButton")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.clicked.connect(self.refresh_dashboard)
        header_row.addWidget(refresh)
        layout.insertLayout(1, header_row)

        score_card = QFrame()
        score_card.setObjectName("Card")
        score_card.setMinimumHeight(118)
        score_layout = QVBoxLayout(score_card)
        score_layout.setContentsMargins(24, 18, 24, 18)
        title = QLabel("FOCUS SCORE")
        title.setObjectName("CardTitle")
        self.score = QLabel("0%")
        self.score.setObjectName("BigScore")
        self.score.setAlignment(Qt.AlignCenter)
        self.score_description = QLabel("Start a session to calculate your focus")
        self.score_description.setObjectName("Muted")
        self.score_description.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(title)
        score_layout.addWidget(self.score)
        score_layout.addWidget(self.score_description)
        layout.addWidget(score_card)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.productive_value = self.add_stat_to_grid(
            grid, 0, 0, "Productive", tone="productive"
        )
        self.neutral_value = self.add_stat_to_grid(
            grid, 0, 1, "Neutral", tone="neutral"
        )
        self.distracting_value = self.add_stat_to_grid(
            grid, 0, 2, "Distracting", tone="distracting"
        )
        self.total_value = self.add_stat_to_grid(grid, 0, 3, "Total Time")
        layout.addLayout(grid)

        layout.addWidget(self.build_duration_setup_card())

        session_card = QFrame()
        session_card.setObjectName("Card")
        session_card.setMinimumHeight(142)
        session_layout = QVBoxLayout(session_card)
        session_layout.setContentsMargins(22, 17, 22, 17)
        timer_row = QHBoxLayout()
        timer_title = QLabel("Focus Session")
        timer_title.setObjectName("SectionTitle")
        timer_row.addWidget(timer_title)
        timer_row.addStretch()
        self.timer_label = QLabel(self.format_timer_duration(self.remaining_seconds))
        self.timer_label.setObjectName("Timer")
        timer_row.addWidget(self.timer_label)
        session_layout.addLayout(timer_row)

        self.progress = QProgressBar()
        self.progress.setObjectName("TimerProgress")
        self.progress.setRange(0, self.session_duration)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.timer_progress_animation = self.create_progress_animation(self.progress)
        session_layout.addWidget(self.progress)

        self.start_button = QPushButton("Start Focus Session")
        self.start_button.setObjectName("StartButton")
        self.start_button.setMinimumHeight(48)
        self.start_button.clicked.connect(self.toggle_session)
        session_layout.addWidget(self.start_button)
        self.session_card = session_card
        layout.addWidget(session_card)

        recent_title = QLabel("Recent Sessions")
        recent_title.setObjectName("SectionTitle")
        layout.addWidget(recent_title)
        self.recent_sessions = QListWidget()
        self.recent_sessions.setObjectName("RecentSessions")
        self.recent_sessions.setSpacing(3)
        self.recent_sessions.setMaximumHeight(160)
        self.recent_sessions.itemClicked.connect(self.select_recent_session)
        layout.addWidget(self.recent_sessions)
        layout.addStretch()
        self.pages.addWidget(self.wrap_page(page))

    def build_duration_setup_card(self):
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)

        heading_row = QHBoxLayout()
        heading = QLabel("Session Setup")
        heading.setObjectName("SectionTitle")
        heading_row.addWidget(heading)
        heading_row.addStretch()
        self.current_duration_badge = QLabel(
            f"Applied • {self.format_setting_duration(self.session_duration)}"
        )
        self.current_duration_badge.setObjectName("DurationBadge")
        heading_row.addWidget(self.current_duration_badge)
        card_layout.addLayout(heading_row)

        description = QLabel(
            "Choose a duration for future sessions. Your current selection is shown below."
        )
        description.setObjectName("Muted")
        description.setWordWrap(True)
        card_layout.addWidget(description)

        time_row = QHBoxLayout()
        time_row.setSpacing(12)
        hour_column = QVBoxLayout()
        hour_label = QLabel("HOURS")
        hour_label.setObjectName("PresetHeader")
        hour_column.addWidget(hour_label)
        self.duration_hours = QSpinBox()
        self.duration_hours.setObjectName("DurationHours")
        self.duration_hours.setRange(0, 4)
        self.duration_hours.setValue(self.session_duration // 3600)
        self.duration_hours.setSuffix(" hr")
        self.configure_duration_spinbox(self.duration_hours)
        self.duration_hours.setToolTip(
            "Type a value, use the visible arrows, or scroll over the control."
        )
        hour_column.addWidget(self.duration_hours)
        time_row.addLayout(hour_column, 1)

        minute_column = QVBoxLayout()
        minute_label = QLabel("MINUTES")
        minute_label.setObjectName("PresetHeader")
        minute_column.addWidget(minute_label)
        self.duration_minutes = QSpinBox()
        self.duration_minutes.setObjectName("DurationMinutes")
        self.duration_minutes.setRange(0, 59)
        self.duration_minutes.setValue((self.session_duration % 3600) // 60)
        self.duration_minutes.setSuffix(" min")
        self.configure_duration_spinbox(self.duration_minutes)
        self.duration_minutes.setToolTip(
            "Type a value, use the visible arrows, or scroll over the control."
        )
        minute_column.addWidget(self.duration_minutes)
        time_row.addLayout(minute_column, 1)
        card_layout.addLayout(time_row)

        self.duration_hours.valueChanged.connect(self.update_duration_badge)
        self.duration_minutes.valueChanged.connect(self.update_duration_badge)

        presets_title = QLabel("QUICK PRESETS")
        presets_title.setObjectName("PresetHeader")
        card_layout.addWidget(presets_title)
        presets = QHBoxLayout()
        presets.setSpacing(8)
        self.duration_preset_buttons = []
        for minutes, label in (
            (25, "25 min"),
            (45, "45 min"),
            (60, "1 hour"),
            (90, "1 hour 30 min"),
        ):
            button = QPushButton(label)
            button.setObjectName("SmallButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(partial(self.apply_duration_preset, minutes))
            presets.addWidget(button)
            self.duration_preset_buttons.append(button)
        card_layout.addLayout(presets)

        preview_row = QHBoxLayout()
        preview_title = QLabel("Duration preview")
        preview_title.setObjectName("Muted")
        preview_row.addWidget(preview_title)
        preview_row.addStretch()
        self.duration_preview = QLabel(self.format_setting_duration(self.session_duration))
        self.duration_preview.setObjectName("SectionTitle")
        preview_row.addWidget(self.duration_preview)
        card_layout.addLayout(preview_row)

        self.duration_save_button = QPushButton("Save and apply")
        self.duration_save_button.setObjectName("SettingsSaveButton")
        self.duration_save_button.setMinimumHeight(42)
        self.duration_save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.duration_save_button.clicked.connect(self.save_settings)
        card_layout.addWidget(self.duration_save_button)
        self.settings_message = QLabel(
            f"Saved duration: {self.format_setting_duration(self.session_duration)}"
        )
        self.settings_message.setObjectName("SettingsStatus")
        self.settings_message.setWordWrap(True)
        card_layout.addWidget(self.settings_message)
        return card

    @staticmethod
    def configure_duration_spinbox(spinbox):
        spinbox.setMinimumHeight(48)
        spinbox.setKeyboardTracking(True)
        spinbox.setAccelerated(True)
        spinbox.setWrapping(False)
        spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        spinbox.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        spinbox.lineEdit().setReadOnly(False)

    @staticmethod
    def configure_table(table, headers):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setWordWrap(False)
        table.setMinimumHeight(120)

    def set_analytics_date_filter_enabled(self, enabled):
        self.analytics_date_from.setEnabled(enabled)
        self.analytics_date_to.setEnabled(enabled)
        self.refresh_analytics()

    def add_stat_to_grid(self, grid, row, col, title, tone=None):
        card, value = self.make_card(title, "0s")
        if tone:
            card.setProperty("tone", tone)
        grid.addWidget(card, row, col)
        return value

    @staticmethod
    def create_progress_animation(progress):
        animation = QPropertyAnimation(progress, b"value", progress)
        animation.setDuration(220)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        return animation

    @staticmethod
    def animate_progress(progress, animation, value):
        if animation.state() == QPropertyAnimation.State.Running:
            animation.stop()
        animation.setStartValue(progress.value())
        animation.setEndValue(value)
        animation.start()

    def build_sessions_page(self):
        page, layout = self.make_page(
            "Study Sessions",
            "Choose a session to review its recorded activity. Details are scoped to that session ID."
        )
        content = QHBoxLayout()
        content.setSpacing(16)
        self.sessions_list = QListWidget()
        self.sessions_list.setObjectName("SessionHistory")
        self.sessions_list.setSpacing(4)
        self.sessions_list.setMinimumWidth(270)
        self.sessions_list.itemClicked.connect(self.select_session_from_list)
        content.addWidget(self.sessions_list, 1)

        details = QVBoxLayout()
        self.session_details_title = QLabel("Select a session")
        self.session_details_title.setObjectName("SectionTitle")
        details.addWidget(self.session_details_title)
        self.session_details_empty = QLabel("Select a session to inspect its recorded activities.")
        self.session_details_empty.setObjectName("Muted")
        self.session_details_empty.setWordWrap(True)
        details.addWidget(self.session_details_empty)
        self.session_activity_table = QTableWidget()
        self.configure_table(
            self.session_activity_table,
            ("Timestamp", "Application", "Window / tab title", "URL", "Category", "Duration"),
        )
        details.addWidget(self.session_activity_table, 1)
        content.addLayout(details, 3)
        layout.addLayout(content, 1)

        refresh = QPushButton("Refresh Sessions")
        refresh.clicked.connect(self.refresh_sessions_page)
        layout.addWidget(refresh)
        self.pages.addWidget(self.wrap_page(page))

    def build_analytics_page(self):
        page, layout = self.make_page(
            "Analytics",
            "Explore recorded activity by session, date, application, and category."
        )
        self.analytics_session_label = QLabel("No session selected")
        self.analytics_session_label.setObjectName("SectionTitle")
        layout.addWidget(self.analytics_session_label)

        filters = QGridLayout()
        filters.setHorizontalSpacing(12)
        filters.setVerticalSpacing(8)
        session_label = QLabel("Session")
        session_label.setObjectName("PresetHeader")
        filters.addWidget(session_label, 0, 0)
        self.analytics_session_filter = QComboBox()
        self.analytics_session_filter.addItem("Selected session", "selected")
        self.analytics_session_filter.addItem("All sessions", None)
        filters.addWidget(self.analytics_session_filter, 1, 0)

        application_label = QLabel("Application")
        application_label.setObjectName("PresetHeader")
        filters.addWidget(application_label, 0, 1)
        self.analytics_application_filter = QComboBox()
        filters.addWidget(self.analytics_application_filter, 1, 1)

        category_label = QLabel("Category")
        category_label.setObjectName("PresetHeader")
        filters.addWidget(category_label, 0, 2)
        self.analytics_category_filter = QComboBox()
        filters.addWidget(self.analytics_category_filter, 1, 2)

        date_controls = QHBoxLayout()
        self.analytics_date_filter = QCheckBox("Limit date range")
        self.analytics_date_filter.setChecked(False)
        date_controls.addWidget(self.analytics_date_filter)
        self.analytics_date_from = QDateEdit()
        self.analytics_date_from.setCalendarPopup(True)
        self.analytics_date_from.setDisplayFormat("yyyy-MM-dd")
        self.analytics_date_from.setDate(QDate.currentDate().addDays(-30))
        self.analytics_date_to = QDateEdit()
        self.analytics_date_to.setCalendarPopup(True)
        self.analytics_date_to.setDisplayFormat("yyyy-MM-dd")
        self.analytics_date_to.setDate(QDate.currentDate())
        self.analytics_date_from.setEnabled(False)
        self.analytics_date_to.setEnabled(False)
        date_controls.addWidget(self.analytics_date_from)
        date_controls.addWidget(QLabel("to"))
        date_controls.addWidget(self.analytics_date_to)
        filters.addLayout(date_controls, 1, 3)
        layout.addLayout(filters)

        self.analytics_session_filter.currentIndexChanged.connect(self.refresh_analytics)
        self.analytics_application_filter.currentIndexChanged.connect(self.refresh_analytics)
        self.analytics_category_filter.currentIndexChanged.connect(self.refresh_analytics)
        self.analytics_date_filter.toggled.connect(self.set_analytics_date_filter_enabled)
        self.analytics_date_from.dateChanged.connect(self.refresh_analytics)
        self.analytics_date_to.dateChanged.connect(self.refresh_analytics)

        grid = QGridLayout()
        self.analytics_productive = self.add_stat_to_grid(
            grid, 0, 0, "Productive Time", tone="productive"
        )
        self.analytics_neutral = self.add_stat_to_grid(
            grid, 0, 1, "Neutral Time", tone="neutral"
        )
        self.analytics_distracting = self.add_stat_to_grid(
            grid, 0, 2, "Distracting Time", tone="distracting"
        )
        self.analytics_total = self.add_stat_to_grid(grid, 0, 3, "Total Recorded Time")
        layout.addLayout(grid)
        self.analytics_score = QLabel("Focus score: 0%")
        self.analytics_score.setObjectName("SectionTitle")
        layout.addWidget(self.analytics_score)

        breakdown_title = QLabel("Activity distribution")
        breakdown_title.setObjectName("SectionTitle")
        layout.addWidget(breakdown_title)
        self.analytics_productive_bar = QProgressBar()
        self.analytics_productive_bar.setObjectName("ProductiveBar")
        self.analytics_productive_bar.setFormat("Productive  %p%")
        self.analytics_productive_bar.setTextVisible(True)
        self.analytics_productive_bar.setFixedHeight(27)
        self.analytics_productive_animation = self.create_progress_animation(
            self.analytics_productive_bar
        )
        layout.addWidget(self.analytics_productive_bar)
        self.analytics_neutral_bar = QProgressBar()
        self.analytics_neutral_bar.setObjectName("NeutralBar")
        self.analytics_neutral_bar.setFormat("Neutral  %p%")
        self.analytics_neutral_bar.setTextVisible(True)
        self.analytics_neutral_bar.setFixedHeight(27)
        self.analytics_neutral_animation = self.create_progress_animation(
            self.analytics_neutral_bar
        )
        layout.addWidget(self.analytics_neutral_bar)
        self.analytics_distracting_bar = QProgressBar()
        self.analytics_distracting_bar.setObjectName("DistractingBar")
        self.analytics_distracting_bar.setFormat("Distracting  %p%")
        self.analytics_distracting_bar.setTextVisible(True)
        self.analytics_distracting_bar.setFixedHeight(27)
        self.analytics_distracting_animation = self.create_progress_animation(
            self.analytics_distracting_bar
        )
        layout.addWidget(self.analytics_distracting_bar)

        category_title = QLabel("Category totals")
        category_title.setObjectName("SectionTitle")
        layout.addWidget(category_title)
        self.analytics_category_table = QTableWidget()
        self.configure_table(self.analytics_category_table, ("Category", "Recorded time", "Share"))
        self.analytics_category_table.setMaximumHeight(190)
        layout.addWidget(self.analytics_category_table)

        app_title = QLabel("Application usage")
        app_title.setObjectName("SectionTitle")
        layout.addWidget(app_title)
        self.analytics_application_table = QTableWidget()
        self.configure_table(
            self.analytics_application_table,
            ("Application", "Recorded time", "Share"),
        )
        self.analytics_application_table.setMinimumHeight(130)
        layout.addWidget(self.analytics_application_table)

        comparisons_title = QLabel("Session comparisons")
        comparisons_title.setObjectName("SectionTitle")
        layout.addWidget(comparisons_title)
        self.analytics_session_table = QTableWidget()
        self.configure_table(
            self.analytics_session_table,
            ("Session", "Started", "Session duration", "Recorded activity", "Focus score"),
        )
        self.analytics_session_table.setMinimumHeight(150)
        layout.addWidget(self.analytics_session_table)

        browser_title = QLabel("Browser activity")
        browser_title.setObjectName("SectionTitle")
        layout.addWidget(browser_title)
        self.browser_capture_note = QLabel(
            "Browser URLs are best-effort: the monitor samples the foreground window every "
            "2 seconds and heuristically matches its title against Chromium debugging endpoints "
            "(Opera 9222, Chrome 9223, Edge 9224, Brave 9225). Without a matching endpoint, the "
            "window title may still be recorded but its URL is unavailable. The smallest safe "
            "coverage improvement is to enable the matching endpoint and tighten active-tab "
            "matching; the existing activity schema can represent the result."
        )
        self.browser_capture_note.setObjectName("Muted")
        self.browser_capture_note.setWordWrap(True)
        layout.addWidget(self.browser_capture_note)
        self.browser_empty_label = QLabel("No browser activity recorded for these filters.")
        self.browser_empty_label.setObjectName("Muted")
        self.browser_empty_label.setWordWrap(True)
        layout.addWidget(self.browser_empty_label)
        self.analytics_browser_table = QTableWidget()
        self.configure_table(
            self.analytics_browser_table,
            ("Page / tab title", "Website / URL", "Application", "Category", "Duration", "Share"),
        )
        self.analytics_browser_table.setMinimumHeight(190)
        self.analytics_browser_table.itemSelectionChanged.connect(
            self.show_browser_activity_details
        )
        layout.addWidget(self.analytics_browser_table)
        self.browser_details_label = QLabel("Select a browser activity entry to inspect its records.")
        self.browser_details_label.setObjectName("SectionTitle")
        layout.addWidget(self.browser_details_label)
        self.analytics_browser_details = QTableWidget()
        self.configure_table(
            self.analytics_browser_details,
            ("Activity ID", "Session", "Timestamp", "Application", "Title", "URL", "Category", "Duration"),
        )
        self.analytics_browser_details.setMinimumHeight(130)
        layout.addWidget(self.analytics_browser_details)

        refresh = QPushButton("Refresh Analytics")
        refresh.clicked.connect(self.refresh_analytics)
        layout.addWidget(refresh)
        layout.addStretch()
        self.pages.addWidget(self.wrap_page(page))

    def open_dashboard(self):
        self.show_page(0)

    def open_sessions(self):
        self.show_page(1)

    def open_analytics(self):
        self.show_page(2)

    def show_page(self, index):
        if index < 0 or index >= self.pages.count():
            print(f"Navigation error: invalid page index {index}")
            return
        self.pages.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setCheckable(True)
            button.setChecked(i == index)
        if index == 0:
            self.refresh_dashboard()
        elif index == 1:
            self.refresh_sessions_page()
        elif index == 2:
            self.refresh_analytics()

    def update_duration_badge(self):
        duration_seconds = (self.duration_hours.value() * 60 + self.duration_minutes.value()) * 60
        duration_text = self.format_setting_duration(duration_seconds)
        self.duration_preview.setText(duration_text)
        self.settings_message.setText(f"Selected duration: {duration_text}")

    @staticmethod
    def format_setting_duration(seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes = remainder // 60
        if hours:
            return f"{hours:02d}:{minutes:02d}"
        return f"{minutes:02d} min"

    def apply_duration_preset(self, minutes_total):
        self.duration_hours.setValue(minutes_total // 60)
        self.duration_minutes.setValue(minutes_total % 60)

    def save_settings(self):
        if self.session_running:
            QMessageBox.information(
                self, "Session in progress",
                "Stop the current session before changing its duration."
            )
            return
        duration_seconds = (
            self.duration_hours.value() * 3600
            + self.duration_minutes.value() * 60
        )
        if not 60 <= duration_seconds <= MAX_SESSION_DURATION_MINUTES * 60:
            QMessageBox.warning(
                self, "Invalid duration",
                "Choose a duration between 1 minute and 4 hours 59 minutes."
            )
            return
        total_minutes = duration_seconds // 60
        self.settings.setValue("session_duration_minutes", total_minutes)
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            QMessageBox.warning(
                self, "Settings not saved",
                "FocusAI could not save your duration preference."
            )
            return
        self.session_duration = duration_seconds
        self.remaining_seconds = self.session_duration
        self.progress.setRange(0, self.session_duration)
        self.progress.setValue(0)
        self.update_timer_display()
        self.current_duration_badge.setText(
            f"Applied • {self.format_setting_duration(self.session_duration)}"
        )
        self.settings_message.setText(
            f"Saved. New focus sessions will last "
            f"{self.format_setting_duration(self.session_duration)}."
        )

    def set_duration_controls_enabled(self, enabled):
        self.duration_hours.setEnabled(enabled)
        self.duration_minutes.setEnabled(enabled)
        self.duration_save_button.setEnabled(enabled)
        for button in self.duration_preset_buttons:
            button.setEnabled(enabled)

    def get_activity_stats(self, session_id=None):
        stats = {"PRODUCTIVE": 0, "NEUTRAL": 0, "DISTRACTING": 0}
        if session_id is None:
            return stats
        with sqlite3.connect(DATABASE_PATH) as connection:
            rows = connection.execute("""
                SELECT category, COALESCE(SUM(duration_seconds), 0)
                FROM activities
                WHERE session_id = ?
                GROUP BY category
            """, (session_id,)).fetchall()
        for category, seconds in rows:
            if category in stats:
                stats[category] = int(seconds or 0)
        return stats

    def get_selected_session_id(self):
        if self.session_running and self.current_session_id is not None:
            return self.current_session_id
        return self.dashboard_session_id

    def refresh_dashboard_statistics(self):
        session_id = self.get_selected_session_id()
        stats = self.get_activity_stats(session_id)
        productive = stats["PRODUCTIVE"]
        neutral = stats["NEUTRAL"]
        distracting = stats["DISTRACTING"]
        total = productive + neutral + distracting
        score = round(productive / total * 100) if total else 0

        self.score.setText(f"{score}%")
        self.productive_value.setText(self.format_duration(productive))
        self.neutral_value.setText(self.format_duration(neutral))
        self.distracting_value.setText(self.format_duration(distracting))
        self.total_value.setText(self.format_duration(total))

        if session_id is None:
            message = "Start a session to calculate your focus"
        elif total == 0:
            message = f"Session #{session_id} • No activity recorded yet"
        else:
            result = (
                "Excellent focus" if score >= 80 else
                "Good focus" if score >= 60 else
                "Needs improvement" if score >= 40 else
                "Try to stay focused"
            )
            suffix = "In progress" if self.session_running else "Selected session"
            message = f"Session #{session_id} • {suffix} • {result}"
        self.score_description.setText(message)

    def refresh_dashboard(self):
        self.refresh_dashboard_statistics()
        self.refresh_recent_sessions()

    @staticmethod
    def set_combo_options(combo, options, default_data):
        selected_data = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for label, data in options:
            combo.addItem(label, data)
        index = combo.findData(selected_data)
        if index < 0:
            index = combo.findData(default_data)
        combo.setCurrentIndex(max(index, 0))
        combo.blockSignals(False)

    def get_analytics_session_id(self):
        selection = self.analytics_session_filter.currentData()
        if selection == "selected":
            return self.get_selected_session_id()
        if selection == "__all__":
            return None
        return selection

    def get_analytics_activity_rows(self, session_id, use_date_filter=True):
        clauses = []
        parameters = []
        if session_id is not None:
            clauses.append("session_id = ?")
            parameters.append(session_id)
        if use_date_filter and self.analytics_date_filter.isChecked():
            start_date = self.analytics_date_from.date().toString("yyyy-MM-dd")
            end_date = self.analytics_date_to.date().toString("yyyy-MM-dd")
            start_date, end_date = sorted((start_date, end_date))
            clauses.extend(("substr(timestamp, 1, 10) >= ?", "substr(timestamp, 1, 10) <= ?"))
            parameters.extend((start_date, end_date))

        query = """
            SELECT id, timestamp, application, activity_title, url, category,
                   duration_seconds, session_id
            FROM activities
        """
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC, id DESC"
        with sqlite3.connect(DATABASE_PATH) as connection:
            return connection.execute(query, parameters).fetchall()

    def apply_analytics_application_category_filters(self, rows):
        application = self.analytics_application_filter.currentData()
        category = self.analytics_category_filter.currentData()
        return [
            row for row in rows
            if (application == "__all__" or row[2] == application)
            and (category == "__all__" or row[5] == category)
        ]

    @staticmethod
    def activity_totals_by_category(rows):
        totals = {}
        for row in rows:
            category = str(row[5] or "Unknown")
            totals[category] = totals.get(category, 0) + int(row[6] or 0)
        return totals

    @staticmethod
    def set_table_rows(table, rows):
        table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for column_index, value in enumerate(values):
                table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

    def refresh_analytics(self):
        sessions = get_sessions()
        session_options = [
            ("Selected session", "selected"),
            ("All sessions", "__all__"),
        ]
        session_options.extend(
            (f"Session #{session[0]}", session[0]) for session in sessions
        )
        self.set_combo_options(
            self.analytics_session_filter,
            session_options,
            "selected",
        )
        selection = self.analytics_session_filter.currentData()
        selected_session_id = self.get_analytics_session_id()
        if selection == "selected" and selected_session_id is None:
            base_rows = []
        else:
            base_rows = self.get_analytics_activity_rows(selected_session_id)

        application_options = [("All applications", "__all__")]
        application_options.extend(
            (str(value), value)
            for value in sorted({row[2] for row in base_rows if row[2]})
        )
        category_options = [("All categories", "__all__")]
        category_options.extend(
            (str(value), value)
            for value in sorted({row[5] for row in base_rows if row[5]})
        )
        self.set_combo_options(
            self.analytics_application_filter, application_options, "__all__"
        )
        self.set_combo_options(
            self.analytics_category_filter, category_options, "__all__"
        )
        rows = self.apply_analytics_application_category_filters(base_rows)

        total = sum(int(row[6] or 0) for row in rows)
        category_totals = self.activity_totals_by_category(rows)
        productive = category_totals.get("PRODUCTIVE", 0)
        neutral = category_totals.get("NEUTRAL", 0)
        distracting = category_totals.get("DISTRACTING", 0)
        score = round(productive / total * 100) if total else 0
        if selection == "selected" and selected_session_id is None:
            self.analytics_session_label.setText("No session selected")
        elif selection == "__all__":
            self.analytics_session_label.setText("All sessions")
        else:
            self.analytics_session_label.setText(f"Session #{selected_session_id}")
        self.analytics_productive.setText(self.format_duration(productive))
        self.analytics_neutral.setText(self.format_duration(neutral))
        self.analytics_distracting.setText(self.format_duration(distracting))
        self.analytics_total.setText(self.format_duration(total))
        self.analytics_score.setText(f"Focus score: {score}%")

        for bar in (
            self.analytics_productive_bar,
            self.analytics_neutral_bar,
            self.analytics_distracting_bar,
        ):
            bar.setRange(0, 100)
        self.animate_progress(
            self.analytics_productive_bar,
            self.analytics_productive_animation,
            round(productive / total * 100) if total else 0,
        )
        self.animate_progress(
            self.analytics_neutral_bar,
            self.analytics_neutral_animation,
            round(neutral / total * 100) if total else 0,
        )
        self.animate_progress(
            self.analytics_distracting_bar,
            self.analytics_distracting_animation,
            round(distracting / total * 100) if total else 0,
        )

        category_rows = [
            (name, self.format_duration(seconds), f"{seconds / total * 100:.1f}%" if total else "0.0%")
            for name, seconds in sorted(category_totals.items())
        ]
        self.set_table_rows(self.analytics_category_table, category_rows)
        self.refresh_application_usage(rows, total)

        comparison_rows = self.apply_analytics_application_category_filters(
            self.get_analytics_activity_rows(None)
        )
        self.refresh_session_comparisons(sessions, comparison_rows)
        self.refresh_browser_activity(rows, total)

    def refresh_application_usage(self, rows, total_seconds):
        totals = {}
        for row in rows:
            application = str(row[2] or "Unknown application")
            totals[application] = totals.get(application, 0) + int(row[6] or 0)
        table_rows = [
            (
                application,
                self.format_duration(seconds),
                f"{seconds / total_seconds * 100:.1f}%" if total_seconds else "0.0%",
            )
            for application, seconds in sorted(
                totals.items(), key=lambda entry: (-entry[1], entry[0].casefold())
            )
        ]
        self.set_table_rows(self.analytics_application_table, table_rows)

    def refresh_session_comparisons(self, sessions, activity_rows):
        totals_by_session = {}
        for row in activity_rows:
            session_id = row[7]
            if session_id is None:
                continue
            category_totals = totals_by_session.setdefault(session_id, {})
            category = str(row[5] or "Unknown")
            category_totals[category] = (
                category_totals.get(category, 0) + int(row[6] or 0)
            )

        comparison_rows = []
        for session in sessions:
            session_id, started = session[0], session[1]
            duration = int(session[3] or 0)
            category_totals = totals_by_session.get(session_id, {})
            recorded_total = sum(category_totals.values())
            score = round(
                category_totals.get("PRODUCTIVE", 0) / recorded_total * 100
            ) if recorded_total else 0
            comparison_rows.append(
                (
                    f"Session #{session_id}",
                    str(started).replace("T", " ")[:16],
                    self.format_duration(duration),
                    self.format_duration(recorded_total),
                    f"{score}%",
                )
            )
        self.set_table_rows(self.analytics_session_table, comparison_rows)

    @staticmethod
    def normalize_recorded_url(url):
        url = str(url or "").strip()
        if not url:
            return ""
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        netloc = parts.netloc.lower()
        if scheme == "http" and netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif scheme == "https" and netloc.endswith(":443"):
            netloc = netloc[:-4]
        return urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))

    @staticmethod
    def is_browser_activity(row):
        application = str(row[2] or "").casefold()
        browser_names = {
            "opera.exe", "chrome.exe", "msedge.exe", "brave.exe",
            "opera", "chrome", "msedge", "brave",
        }
        return bool(row[4]) or application in browser_names

    def refresh_browser_activity(self, rows, total_seconds):
        previously_selected = None
        current_item = self.analytics_browser_table.currentItem()
        if current_item is not None:
            selected_row = self.analytics_browser_table.currentRow()
            if 0 <= selected_row < len(getattr(self, "browser_groups", [])):
                previously_selected = self.browser_groups[selected_row]["key"]

        groups = {}
        for row in rows:
            if not self.is_browser_activity(row):
                continue
            application = str(row[2] or "Unknown application")
            title = str(row[3] or "").strip()
            url = str(row[4] or "").strip()
            category = str(row[5] or "Unknown")
            normalized_url = self.normalize_recorded_url(url)
            normalized_title = " ".join(title.casefold().split())
            key = (
                application.casefold(),
                normalized_url,
                normalized_title,
                category.casefold(),
                None if normalized_url else row[0],
            )
            if key not in groups:
                groups[key] = {
                    "key": key,
                    "title": title or "Tab title not captured",
                    "url": normalized_url,
                    "application": application,
                    "category": category,
                    "seconds": 0,
                    "records": [],
                }
            groups[key]["seconds"] += int(row[6] or 0)
            groups[key]["records"].append(row)

        self.browser_groups = sorted(
            groups.values(),
            key=lambda group: (-group["seconds"], group["title"].casefold()),
        )
        self.browser_empty_label.setVisible(not self.browser_groups)
        self.analytics_browser_table.blockSignals(True)
        self.analytics_browser_table.setRowCount(len(self.browser_groups))
        selected_index = -1
        for index, group in enumerate(self.browser_groups):
            share = group["seconds"] / total_seconds * 100 if total_seconds else 0
            values = (
                group["title"],
                group["url"] or "URL not captured",
                group["application"],
                group["category"],
                self.format_duration(group["seconds"]),
                f"{share:.1f}%",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, group["key"])
                self.analytics_browser_table.setItem(index, column, item)
            if group["key"] == previously_selected:
                selected_index = index
        if selected_index >= 0:
            self.analytics_browser_table.selectRow(selected_index)
        self.analytics_browser_table.blockSignals(False)
        if selected_index >= 0:
            self.show_browser_activity_details()
        else:
            self.analytics_browser_details.setRowCount(0)
            self.browser_details_label.setText(
                "Select a browser activity entry to inspect its records."
            )

    def show_browser_activity_details(self):
        row_index = self.analytics_browser_table.currentRow()
        if row_index < 0 or row_index >= len(getattr(self, "browser_groups", [])):
            return
        group = self.browser_groups[row_index]
        records = group["records"]
        self.browser_details_label.setText(
            f"Recorded details for {group['title']} "
            f"({len(records)} matching record{'s' if len(records) != 1 else ''})"
        )
        detail_rows = [
            (
                row[0],
                f"Session #{row[7]}" if row[7] is not None else "No session",
                str(row[1] or "").replace("T", " "),
                row[2] or "Unknown application",
                row[3] or "Tab title not captured",
                row[4] or "URL not captured",
                row[5] or "Unknown",
                self.format_duration(row[6]),
            )
            for row in records
        ]
        self.set_table_rows(self.analytics_browser_details, detail_rows)

    def format_duration(self, seconds):
        seconds = int(seconds or 0)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining = seconds % 60
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {remaining}s"
        return f"{remaining}s"

    def toggle_session(self):
        if self.session_running:
            self.stop_session()
        else:
            self.start_session()

    def start_session(self):
        if self.session_running:
            return
        self.remaining_seconds = self.session_duration
        self.update_timer_display()
        self.progress.setValue(0)
        self.session_start_time = datetime.now()
        self.current_session_id = create_session(self.session_start_time.isoformat())
        self.dashboard_session_id = self.current_session_id
        self.session_running = True
        self.set_duration_controls_enabled(False)
        self.start_button.setText("Stop Focus Session")
        self.status.setText("● Session Active")
        self.refresh_dashboard_statistics()
        self.timer.start(1000)
        self.start_activity_monitor()
        print("\n================================")
        print("Focus session started")
        print(f"Session ID: {self.current_session_id}")
        print("================================")

    def start_activity_monitor(self):
        self.focus_monitor = FocusMonitor(session_id=self.current_session_id)
        self.monitor_thread = threading.Thread(target=self.focus_monitor.start, daemon=True)
        self.monitor_thread.start()

    def stop_session(self):
        if not self.session_running:
            return
        self.timer.stop()
        if self.focus_monitor:
            self.focus_monitor.stop()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        if self.monitor_thread and self.monitor_thread.is_alive():
            print("Warning: activity monitor did not stop within 5 seconds.")

        end_time = datetime.now()
        elapsed_seconds = self.session_duration - self.remaining_seconds
        finish_session(
            self.current_session_id,
            end_time.isoformat(),
            elapsed_seconds,
            "stopped",
        )
        self.dashboard_session_id = self.current_session_id
        score = calculate_session_focus_score(self.current_session_id)

        self.session_running = False
        self.set_duration_controls_enabled(True)
        self.start_button.setText("Start Focus Session")
        self.status.setText("● System Ready")
        self.remaining_seconds = self.session_duration
        self.update_timer_display()
        self.progress.setValue(0)

        print("\n================================")
        print("Focus session stopped")
        print(f"Focus Score: {score}%")
        print("================================")

        self.current_session_id = None
        self.focus_monitor = None
        self.monitor_thread = None
        self.refresh_dashboard()
        self.refresh_analytics()

    def update_timer(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_timer_display()
            if self.session_running:
                self.refresh_dashboard_statistics()
                if self.pages.currentIndex() == 2:
                    self.refresh_analytics()
        else:
            self.stop_session()

    def update_timer_display(self):
        self.timer_label.setText(self.format_timer_duration(self.remaining_seconds))
        if self.session_running:
            self.animate_progress(
                self.progress,
                self.timer_progress_animation,
                self.session_duration - self.remaining_seconds,
            )

    @staticmethod
    def format_timer_duration(seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def refresh_recent_sessions(self):
        self.recent_sessions.clear()
        sessions = get_sessions()
        if not sessions:
            self.recent_sessions.addItem("No sessions found.")
            return
        selected_item = None
        for session in sessions[:5]:
            try:
                session_id, started = session[0], session[1]
                duration = session[3]
                item = QListWidgetItem(
                    f"Session #{session_id}  •  {self.format_duration(duration)}  •  "
                    f"{str(started)[:16].replace('T', ' ')}"
                )
                item.setData(Qt.UserRole, session_id)
                self.recent_sessions.addItem(item)
                if session_id == self.dashboard_session_id:
                    selected_item = item
            except (IndexError, TypeError):
                continue
        if selected_item is not None:
            self.recent_sessions.setCurrentItem(selected_item)

    def refresh_sessions_page(self):
        self.sessions_list.clear()
        sessions = get_sessions()
        if not sessions:
            self.sessions_list.addItem("No sessions found.")
            self.session_activity_table.setRowCount(0)
            self.session_details_title.setText("No session selected")
            self.session_details_empty.setText("No sessions are available yet.")
            return
        selected_item = None
        for session in sessions:
            try:
                session_id = session[0]
                started = str(session[1])
                duration = session[3]
                status = session[4] if len(session) > 4 else "unknown"
                item = QListWidgetItem(
                    f"Session #{session_id}  |  {self.format_duration(duration)}  |  "
                    f"{status}  |  {started[:16].replace('T', ' ')}"
                )
                item.setData(Qt.UserRole, session_id)
                self.sessions_list.addItem(item)
                if session_id == self.dashboard_session_id:
                    selected_item = item
            except (IndexError, TypeError):
                continue
        if selected_item is None and self.sessions_list.count():
            selected_item = self.sessions_list.item(0)
            self.dashboard_session_id = selected_item.data(Qt.UserRole)
        if selected_item is not None:
            self.sessions_list.setCurrentItem(selected_item)
            self.refresh_session_details(selected_item.data(Qt.UserRole))

    def refresh_session_details(self, session_id):
        if session_id is None:
            self.session_details_title.setText("No session selected")
            self.session_details_empty.setText("Select a session to inspect its recorded activities.")
            self.session_activity_table.setRowCount(0)
            return
        activities = get_session_activities(session_id)
        self.session_details_title.setText(f"Recorded activities for Session #{session_id}")
        if not activities:
            self.session_details_empty.setText(
                "No activity was recorded for this session."
            )
            self.session_details_empty.setVisible(True)
            self.session_activity_table.setRowCount(0)
            return

        self.session_details_empty.setText(
            f"{len(activities)} recorded activity entr"
            f"{'y' if len(activities) == 1 else 'ies'} for Session #{session_id}."
        )
        self.session_details_empty.setVisible(True)
        table_rows = [
            (
                str(activity[1] or "").replace("T", " "),
                activity[2] or "Unknown application",
                activity[3] or "Window title not captured",
                activity[4] or "URL not captured",
                activity[5] or "Unknown",
                self.format_duration(activity[6]),
            )
            for activity in activities
        ]
        self.set_table_rows(self.session_activity_table, table_rows)

    def select_recent_session(self, item):
        session_id = item.data(Qt.UserRole)
        if session_id is not None and not self.session_running:
            self.dashboard_session_id = session_id
            self.refresh_dashboard_statistics()
            self.refresh_analytics()

    def select_session_from_list(self, item):
        session_id = item.data(Qt.UserRole)
        if session_id is not None and not self.session_running:
            self.dashboard_session_id = session_id
            self.refresh_session_details(session_id)
            self.refresh_dashboard_statistics()
            self.refresh_recent_sessions()
            self.refresh_analytics()

    def closeEvent(self, event):
        print("\nClosing FocusAI...")
        if self.session_running:
            self.stop_session()
        if self.focus_monitor:
            self.focus_monitor.stop()
        self.timer.stop()
        print("FocusAI closed.")
        event.accept()


def calculate_session_focus_score(session_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute("""
            SELECT category, COALESCE(SUM(duration_seconds), 0)
            FROM activities
            WHERE session_id = ?
            GROUP BY category
        """, (session_id,)).fetchall()

    totals = {"PRODUCTIVE": 0, "NEUTRAL": 0, "DISTRACTING": 0}
    for category, duration in rows:
        if category in totals:
            totals[category] += int(duration or 0)
    total = sum(totals.values())
    return round(totals["PRODUCTIVE"] / total * 100) if total else 0


def main():
    initialize_database()
    initialize_activity_database()
    add_session_id_column()
    app = QApplication(sys.argv)
    window = FocusAI()
    window.show()
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nFocusAI closed.")


if __name__ == "__main__":
    main()
