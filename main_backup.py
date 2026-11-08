import sys
import sqlite3
import threading
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
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
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QSpinBox,
    QMessageBox,
)

from database.session_db import (
    initialize_database,
    create_session,
    finish_session,
    get_sessions,
)
from database.activity_db import initialize_activity_database, add_session_id_column
from screen.focus_monitor import FocusMonitor

DATABASE_PATH = "database/focusai.db"


class FocusAI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusAI")
        self.setMinimumSize(1100, 720)

        self.session_duration = 25 * 60
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
        side.setContentsMargins(22, 28, 22, 22)
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
            ("Settings", self.open_settings),
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
        self.build_settings_page()

        self.setStyleSheet("""
            QMainWindow, QWidget { background: #101114; color: #F5F5F5; font-family: Segoe UI; }
            #Sidebar { background: #17191E; border-right: 1px solid #292C33; }
            #Logo { font-size: 29px; font-weight: 700; }
            #SidebarSub, #Status, #Description, #Muted { color: #969CA8; }
            QPushButton { background: #20232A; border: none; border-radius: 8px;
                          padding: 11px 14px; text-align: left; font-size: 14px; }
            QPushButton:hover { background: #30343D; }
            QPushButton:checked { background: #343943; border: 1px solid #565D6A; }
            #StartButton { background: #FFFFFF; color: #111111; font-size: 15px;
                           font-weight: 600; text-align: center; margin-top: 8px; }
            #StartButton:hover { background: #E8E8E8; }
            #SmallButton { padding: 8px 13px; text-align: center; }
            #Heading { font-size: 28px; font-weight: 700; }
            #Card { background: #191B21; border: 1px solid #292C33; border-radius: 12px; }
            #CardTitle { color: #858B97; font-size: 12px; font-weight: 700; letter-spacing: 1px; }
            #BigScore { font-size: 54px; font-weight: 700; padding: 2px; }
            #StatTitle { color: #858B97; font-size: 11px; font-weight: 700; }
            #StatValue { font-size: 23px; font-weight: 600; }
            #SectionTitle { font-size: 17px; font-weight: 600; }
            #Timer { font-size: 30px; font-weight: 700; }
            QProgressBar { background: #292C33; border: none; border-radius: 4px; }
            QProgressBar::chunk { background: #FFFFFF; border-radius: 4px; }
            QListWidget, QSpinBox { background: #191B21; border: 1px solid #292C33;
                                    border-radius: 8px; padding: 7px; }
            QListWidget::item { padding: 10px; border-radius: 6px; }
            QListWidget::item:selected { background: #343943; }
        """)

    def make_page(self, title, description=None):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 30, 36, 30)
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
        header = layout.itemAt(1).layout() if layout.count() > 1 else None
        # Header row with a manual refresh action.
        header_row = QHBoxLayout()
        header_row.addStretch()
        refresh = QPushButton("↻ Refresh")
        refresh.setObjectName("SmallButton")
        refresh.clicked.connect(self.refresh_dashboard)
        header_row.addWidget(refresh)
        layout.insertLayout(1, header_row)

        score_card = QFrame()
        score_card.setObjectName("Card")
        score_layout = QVBoxLayout(score_card)
        score_layout.setContentsMargins(25, 20, 25, 20)
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
        grid.setSpacing(14)
        self.productive_value = self.add_stat_to_grid(grid, 0, 0, "Productive")
        self.neutral_value = self.add_stat_to_grid(grid, 0, 1, "Neutral")
        self.distracting_value = self.add_stat_to_grid(grid, 0, 2, "Distracting")
        self.total_value = self.add_stat_to_grid(grid, 0, 3, "Total Time")
        layout.addLayout(grid)

        session_card = QFrame()
        session_card.setObjectName("Card")
        session_layout = QVBoxLayout(session_card)
        session_layout.setContentsMargins(25, 20, 25, 20)
        timer_row = QHBoxLayout()
        timer_title = QLabel("Focus Session")
        timer_title.setObjectName("SectionTitle")
        timer_row.addWidget(timer_title)
        timer_row.addStretch()
        self.timer_label = QLabel("25:00")
        self.timer_label.setObjectName("Timer")
        timer_row.addWidget(self.timer_label)
        session_layout.addLayout(timer_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, self.session_duration)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        session_layout.addWidget(self.progress)

        self.start_button = QPushButton("Start Focus Session")
        self.start_button.setObjectName("StartButton")
        self.start_button.setMinimumHeight(48)
        self.start_button.clicked.connect(self.toggle_session)
        session_layout.addWidget(self.start_button)
        layout.addWidget(session_card)

        recent_title = QLabel("Recent Sessions")
        recent_title.setObjectName("SectionTitle")
        layout.addWidget(recent_title)
        self.recent_sessions = QListWidget()
        self.recent_sessions.setMaximumHeight(145)
        self.recent_sessions.itemClicked.connect(self.select_recent_session)
        layout.addWidget(self.recent_sessions)
        layout.addStretch()
        self.pages.addWidget(page)

    def add_stat_to_grid(self, grid, row, col, title):
        card, value = self.make_card(title, "0s")
        grid.addWidget(card, row, col)
        return value

    def build_sessions_page(self):
        page, layout = self.make_page(
            "Study Sessions",
            "Select a session to view its statistics on the dashboard."
        )
        self.sessions_list = QListWidget()
        self.sessions_list.itemClicked.connect(self.select_session_from_list)
        layout.addWidget(self.sessions_list, 1)
        refresh = QPushButton("Refresh Sessions")
        refresh.clicked.connect(self.refresh_sessions_page)
        layout.addWidget(refresh)
        self.pages.addWidget(page)

    def build_analytics_page(self):
        page, layout = self.make_page(
            "Analytics",
            "Activity breakdown for the selected dashboard session."
        )
        self.analytics_session_label = QLabel("No session selected")
        self.analytics_session_label.setObjectName("SectionTitle")
        layout.addWidget(self.analytics_session_label)
        grid = QGridLayout()
        self.analytics_productive = self.add_stat_to_grid(grid, 0, 0, "Productive Time")
        self.analytics_neutral = self.add_stat_to_grid(grid, 0, 1, "Neutral Time")
        self.analytics_distracting = self.add_stat_to_grid(grid, 0, 2, "Distracting Time")
        self.analytics_total = self.add_stat_to_grid(grid, 0, 3, "Total Recorded Time")
        layout.addLayout(grid)
        self.analytics_score = QLabel("Focus score: 0%")
        self.analytics_score.setObjectName("SectionTitle")
        layout.addWidget(self.analytics_score)
        refresh = QPushButton("Refresh Analytics")
        refresh.clicked.connect(self.refresh_analytics)
        layout.addWidget(refresh)
        layout.addStretch()
        self.pages.addWidget(page)

    def build_settings_page(self):
        page, layout = self.make_page(
            "Settings",
            "Choose the length of your next focus session. Changes apply to future sessions."
        )
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 22)
        label = QLabel("Focus session duration (minutes)")
        label.setObjectName("SectionTitle")
        card_layout.addWidget(label)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 180)
        self.duration_spin.setValue(max(1, self.session_duration // 60))
        self.duration_spin.setSuffix(" min")
        self.duration_spin.setMinimumHeight(42)
        card_layout.addWidget(self.duration_spin)
        save = QPushButton("Save Settings")
        save.clicked.connect(self.save_settings)
        card_layout.addWidget(save)
        self.settings_message = QLabel("Default duration: 25 minutes")
        self.settings_message.setObjectName("Muted")
        card_layout.addWidget(self.settings_message)
        layout.addWidget(card)
        layout.addStretch()
        self.pages.addWidget(page)

    def open_dashboard(self):
        self.show_page(0)

    def open_sessions(self):
        self.show_page(1)

    def open_analytics(self):
        self.show_page(2)

    def open_settings(self):
        self.show_page(3)

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

    def save_settings(self):
        if self.session_running:
            QMessageBox.information(
                self, "Session in progress",
                "Stop the current session before changing its duration."
            )
            return
        self.session_duration = self.duration_spin.value() * 60
        self.remaining_seconds = self.session_duration
        self.progress.setRange(0, self.session_duration)
        self.progress.setValue(0)
        self.update_timer_display()
        self.settings_message.setText(
            f"Saved. New focus sessions will last {self.duration_spin.value()} minutes."
        )

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

    def refresh_analytics(self):
        session_id = self.get_selected_session_id()
        stats = self.get_activity_stats(session_id)
        total = sum(stats.values())
        score = round(stats["PRODUCTIVE"] / total * 100) if total else 0
        self.analytics_session_label.setText(
            f"Session #{session_id}" if session_id is not None else "No session selected"
        )
        self.analytics_productive.setText(self.format_duration(stats["PRODUCTIVE"]))
        self.analytics_neutral.setText(self.format_duration(stats["NEUTRAL"]))
        self.analytics_distracting.setText(self.format_duration(stats["DISTRACTING"]))
        self.analytics_total.setText(self.format_duration(total))
        self.analytics_score.setText(f"Focus score: {score}%")

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
                elapsed = self.session_duration - self.remaining_seconds
                self.progress.setValue(elapsed)
                self.refresh_dashboard_statistics()
                if self.pages.currentIndex() == 2:
                    self.refresh_analytics()
        else:
            self.stop_session()

    def update_timer_display(self):
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")
        if self.session_running:
            self.progress.setValue(self.session_duration - self.remaining_seconds)

    def refresh_recent_sessions(self):
        self.recent_sessions.clear()
        sessions = get_sessions()
        if not sessions:
            self.recent_sessions.addItem("No sessions found.")
            return
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
            except (IndexError, TypeError):
                continue

    def refresh_sessions_page(self):
        self.sessions_list.clear()
        sessions = get_sessions()
        if not sessions:
            self.sessions_list.addItem("No sessions found.")
            return
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
            except (IndexError, TypeError):
                continue

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
            self.show_page(0)

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
