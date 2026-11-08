"""FocusAI foreground activity monitor.

Run from the FocusAI project root with:
    python -m screen.focus_monitor

Browser URLs are read from Chromium DevTools endpoints when the browser was
started with a remote-debugging port. If no endpoint is available, the monitor
still classifies recognizable sites from the foreground window title.
"""

import json
import threading
import urllib.request
from datetime import datetime

import psutil
import win32gui
import win32process

from database.activity_db import initialize_activity_database, save_activity


class FocusMonitor:
    # Start browsers with these ports to enable URL-level detection.
    # Opera is the only endpoint configured in the user's current setup.
    BROWSER_DEBUG_URLS = {
        "opera.exe": "http://localhost:9222/json",
        "chrome.exe": "http://localhost:9223/json",
        "msedge.exe": "http://localhost:9224/json",
        "brave.exe": "http://localhost:9225/json",
    }

    EDUCATIONAL_KEYWORDS = (
        "leetcode", "dsa", "data structure", "algorithm", "programming",
        "python", "java", "c++", "machine learning", "artificial intelligence",
        "computer science", "tutorial", "course", "lecture", "study", "exam",
        "placement", "coding", "striver", "geeksforgeeks", "w3schools",
    )

    PRODUCTIVE_DOMAINS = (
        "leetcode.com", "takeuforward.org", "vtop.vitap.ac.in", "wadhwani",
        "github.com", "chatgpt.com", "geeksforgeeks.org", "w3schools.com",
        "stackoverflow.com", "developer.mozilla.org",
    )
    DISTRACTING_DOMAINS = (
        "hotstar.com", "instagram.com", "whatsapp.com", "steampowered.com",
        "netflix.com", "primevideo.com", "twitch.tv",
    )

    def __init__(self, session_id=None):
        self.session_id = session_id
        self.current_activity = None
        self.activity_start_time = None
        self.stop_event = threading.Event()
        self.final_activity_saved = False

    # -------------------- Foreground application --------------------
    def get_foreground_application(self):
        window = win32gui.GetForegroundWindow()
        if not window:
            return None

        title = win32gui.GetWindowText(window) or "(Untitled window)"
        _, process_id = win32process.GetWindowThreadProcessId(window)
        try:
            process_name = psutil.Process(process_id).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            process_name = "Unknown"

        return {"process": process_name, "title": title}

    # -------------------- Browser pages / titles --------------------
    def get_browser_pages(self, process_name):
        debug_url = self.BROWSER_DEBUG_URLS.get(process_name.lower())
        if not debug_url:
            return []
        try:
            request = urllib.request.Request(
                debug_url, headers={"User-Agent": "FocusAI/1.0"}
            )
            with urllib.request.urlopen(request, timeout=0.6) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, ValueError, TimeoutError):
            return []
        except Exception:
            # Browser debugging is optional; a missing endpoint must not stop monitoring.
            return []

    @staticmethod
    def normalize_title(title):
        title = (title or "").lower().strip()
        for ending in (
            " - opera", " – opera", " | opera", " - google chrome",
            " - microsoft edge", " - brave",
        ):
            if title.endswith(ending):
                title = title[:-len(ending)].strip()
        return title

    def find_browser_page(self, window_title, pages):
        normalized_window = self.normalize_title(window_title)
        candidates = []
        for page in pages:
            if page.get("type") != "page":
                continue
            title = page.get("title", "")
            url = page.get("url", "")
            if not title or not url:
                continue
            normalized_page = self.normalize_title(title)
            if normalized_page == normalized_window:
                return {"title": title, "url": url}
            if normalized_page and (
                normalized_page in normalized_window
                or normalized_window in normalized_page
            ):
                candidates.append({"title": title, "url": url})

        if candidates:
            # Prefer the closest-length match instead of an unrelated long title.
            candidates.sort(
                key=lambda item: abs(
                    len(self.normalize_title(item["title"])) - len(normalized_window)
                )
            )
            return candidates[0]
        return None

    # -------------------- Activity classification --------------------
    def classify_browser(self, title, url=""):
        title_lower = (title or "").lower()
        url_lower = (url or "").lower()

        if any(domain in url_lower for domain in self.PRODUCTIVE_DOMAINS):
            return "PRODUCTIVE"
        if any(domain in url_lower for domain in self.DISTRACTING_DOMAINS):
            return "DISTRACTING"

        # Fallback when remote debugging is not enabled or a page cannot be matched.
        combined = f"{title_lower} {url_lower}"
        if any(site in combined for site in (
            "instagram", "whatsapp", "hotstar", "netflix", "prime video",
            "steam store", "twitch",
        )):
            return "DISTRACTING"
        if any(site in combined for site in (
            "leetcode", "take u forward", "takeuforward", "vtop", "wadhwani",
            "github", "chatgpt", "geeksforgeeks", "w3schools", "stackoverflow",
            "developer.mozilla",
        )):
            return "PRODUCTIVE"

        if "youtube" in combined or "youtu.be" in combined:
            if any(keyword in title_lower for keyword in self.EDUCATIONAL_KEYWORDS):
                return "PRODUCTIVE"
            return "NEUTRAL"

        # Email is intentionally neutral; unknown sites are neutral by default.
        return "NEUTRAL"

    @staticmethod
    def classify_windows(process):
        process = (process or "").lower()
        productive = {
            "code.exe", "powerpnt.exe", "winword.exe", "excel.exe",
            "acrord32.exe", "sumatrapdf.exe", "onenote.exe",
        }
        distracting = {"steam.exe", "discord.exe", "whatsapp.exe"}
        if process in productive:
            return "PRODUCTIVE"
        if process in distracting:
            return "DISTRACTING"
        return "NEUTRAL"

    def get_current_activity(self):
        foreground = self.get_foreground_application()
        if not foreground:
            return None

        process = foreground["process"]
        window_title = foreground["title"]
        process_lower = process.lower()

        # Do not count the FocusAI dashboard itself as study or distraction time.
        if process_lower in {"python.exe", "pythonw.exe"} and "focusai" in window_title.lower():
            return None

        if process_lower in self.BROWSER_DEBUG_URLS:
            pages = self.get_browser_pages(process_lower)
            page = self.find_browser_page(window_title, pages)
            if page:
                title, url = page["title"], page["url"]
            else:
                title, url = window_title, ""
            return {
                "application": process,
                "title": title,
                "url": url,
                "category": self.classify_browser(title, url),
            }

        return {
            "application": process,
            "title": window_title,
            "url": "",
            "category": self.classify_windows(process),
        }

    # -------------------- Duration tracking / database --------------------
    @staticmethod
    def get_activity_key(activity):
        return (
            activity["application"], activity["title"],
            activity["url"], activity["category"],
        )

    def save_completed_activity(self):
        if self.final_activity_saved or self.current_activity is None or self.activity_start_time is None:
            return

        duration_seconds = int((datetime.now() - self.activity_start_time).total_seconds())
        if duration_seconds <= 0:
            self.final_activity_saved = True
            return

        activity = self.current_activity
        save_activity(
            activity["application"], activity["title"], activity["url"],
            activity["category"], duration_seconds, self.session_id,
        )
        print(f"Duration: {duration_seconds} seconds")
        print(f"Session ID: {self.session_id}")
        print("Saved duration to database.")
        self.final_activity_saved = True

    def clear_current_activity(self):
        """Save the activity before pausing on an ignored/untitled window."""
        if self.current_activity is not None:
            self.save_completed_activity()
        self.current_activity = None
        self.activity_start_time = None
        self.final_activity_saved = False

    def handle_activity_change(self, activity):
        if self.stop_event.is_set():
            return
        if activity is None:
            self.clear_current_activity()
            return

        new_key = self.get_activity_key(activity)
        old_key = self.get_activity_key(self.current_activity) if self.current_activity else None
        if new_key == old_key:
            return

        if self.current_activity is not None:
            self.save_completed_activity()

        self.current_activity = activity
        self.activity_start_time = datetime.now()
        self.final_activity_saved = False
        self.print_activity(activity)

    @staticmethod
    def print_activity(activity):
        print("-----------------------------------")
        print(f"Application: {activity['application']}")
        print(f"Activity: {activity['title']}")
        if activity["url"]:
            print(f"URL: {activity['url']}")
        print(f"Category: {activity['category']}")
        print("Activity started.")

    def stop(self):
        # Ask the worker loop to stop. The worker's finally block performs the
        # final save, so the database write completes in one thread only.
        self.stop_event.set()
        print("Activity monitor stop requested.")

    def start(self):
        print("FocusAI Activity Monitor Started")
        print("Duration tracking enabled.")
        print(f"Session ID: {self.session_id}")
        print("Browser URL detection requires the relevant debug port; title fallback remains enabled.")
        print("-----------------------------------")
        try:
            while not self.stop_event.is_set():
                activity = self.get_current_activity()
                self.handle_activity_change(activity)
                self.stop_event.wait(2)
        finally:
            if self.current_activity is not None:
                self.save_completed_activity()
            self.current_activity = None
            self.activity_start_time = None
            print("FocusAI Activity Monitor Stopped")


if __name__ == "__main__":
    initialize_activity_database()
    monitor = FocusMonitor()
    try:
        monitor.start()
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()
