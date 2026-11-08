import psutil
import time
import win32gui
import win32process


class ActivityMonitor:

    def __init__(self):
        self.running = False

    def get_foreground_application(self):

        # Get the window currently in focus
        window = win32gui.GetForegroundWindow()

        if not window:
            return "Unknown"

        # Get the process ID of that window
        _, process_id = win32process.GetWindowThreadProcessId(
            window
        )

        try:
            process = psutil.Process(process_id)

            process_name = process.name()

            window_title = win32gui.GetWindowText(window)

            return process_name, window_title

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied
        ):
            return "Unknown", ""

    def start_monitoring(self):

        self.running = True

        print("Foreground Activity Monitor Started")
        print("-----------------------------------")

        while self.running:

            process_name, window_title = (
                self.get_foreground_application()
            )

            print(
                f"Application: {process_name}"
            )

            print(
                f"Window: {window_title}"
            )

            print("-----------------------------------")

            time.sleep(3)

    def stop_monitoring(self):

        self.running = False

        print(
            "Foreground Activity Monitor Stopped"
        )


if __name__ == "__main__":

    monitor = ActivityMonitor()

    try:

        monitor.start_monitoring()

    except KeyboardInterrupt:

        monitor.stop_monitoring()