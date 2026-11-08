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

## Settings

The Settings tab provides five built-in themes, optional local motivational reminders,
and delayed prompts to classify activities the monitor cannot confidently identify.
Preferences and learned classifications are stored in a small JSON file under the
current user's local application-data directory; the existing SQLite database is not
used for these settings. The monitor communicates activity transitions to the GUI
through a Qt signal, and reminders/classification prompts are non-modal.

Unknown-activity answers are saved for the matching website domain or exact application
window identity. They apply to subsequent monitored time and future sessions only;
previous activity rows and historical statistics are not rewritten. Saved identities
can be updated or removed in Settings.

## Run

From the project root, start the desktop application with:

```powershell
.\venv\Scripts\python.exe .\main.py
```

## Website app

The React website in `website/` includes a working focus timer with selectable durations,
pause/resume and early finish controls, a recent-session log, and statistics/charts
calculated from sessions stored in the browser's local storage.
Session length can be set using separate hour and minute fields, up to 24 hours total.

```powershell
cd website
npm install
npm run dev -- --host 0.0.0.0
```

To create a production build:

```powershell
cd website
npm run build
```

The website's data stays in the current browser and does not sync with the Windows
application or other browsers. A hosted browser app cannot monitor other desktop
applications; use the Windows app for foreground-application activity tracking.

The site is deployed from `main` to GitHub Pages by the workflow in
`.github/workflows/deploy.yml`.