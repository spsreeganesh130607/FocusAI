# FocusAI

AI-powered study assistant for Windows.

## Dashboard

The Dashboard contains the session focus summary, duration setup, countdown, and recent
sessions. Duration preferences are saved with `QSettings` and apply to future sessions;
recorded session durations and activity history remain in SQLite.

## Sessions and analytics

Sessions shows the activity rows recorded for the selected session, including the
application, window or tab title, category, timestamp, duration, and URL when available.
Analytics includes category totals, application usage, session comparisons, and
browser-activity records. Filters use the existing SQLite session IDs, timestamps,
applications, and categories.

Browser URL collection is best-effort. The monitor samples the foreground window every
two seconds and optionally reads Chromium debugging endpoints (Opera on port 9222,
Chrome on 9223, Edge on 9224, Brave on 9225) to match a page title and URL. Without a
matching endpoint, it can record a browser window title without a URL; Analytics marks
uncaptured titles and URLs rather than inferring them.

## Run

From the project root, start the application with:

```powershell
.\venv\Scripts\python.exe .\main.py
```