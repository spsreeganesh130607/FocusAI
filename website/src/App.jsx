import { useCallback, useEffect, useState } from 'react'
import './App.css'

const SESSION_STORAGE_KEY = 'focusai.web.sessions'
const TIMER_STORAGE_KEY = 'focusai.web.activeTimer'
const DURATION_OPTIONS = [15, 25, 45, 60]
const CATEGORY_OPTIONS = ['Deep work', 'Study', 'Reading', 'Writing', 'Other']
const INITIAL_NOW = Date.now()

function isValidSession(session) {
  return (
    session &&
    typeof session.id === 'string' &&
    typeof session.task === 'string' &&
    typeof session.category === 'string' &&
    Number.isFinite(session.durationSeconds) &&
    session.durationSeconds > 0 &&
    typeof session.startedAt === 'string' &&
    Number.isFinite(Date.parse(session.startedAt))
  )
}

function loadSavedState() {
  try {
    const sessions = JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY) || '[]')
    const activeTimer = JSON.parse(localStorage.getItem(TIMER_STORAGE_KEY) || 'null')

    return {
      sessions: Array.isArray(sessions) ? sessions.filter(isValidSession) : [],
      activeTimer:
        activeTimer &&
        Number.isFinite(activeTimer.durationSeconds) &&
        Number.isFinite(activeTimer.remainingSeconds) &&
        typeof activeTimer.startedAt === 'string'
          ? activeTimer
          : null,
      storageWarning: '',
    }
  } catch (error) {
    console.error('Could not read FocusAI data from browser storage.', error)
    return {
      sessions: [],
      activeTimer: null,
      storageWarning: 'Saved browser data could not be read. New sessions may not persist.',
    }
  }
}

function formatTime(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function formatDuration(totalSeconds) {
  if (totalSeconds > 0 && totalSeconds < 60) return `${totalSeconds}s`
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  if (hours === 0) return `${minutes}m`
  if (minutes === 0) return `${hours}h`
  return `${hours}h ${minutes}m`
}

function dateKey(isoDate) {
  const date = new Date(isoDate)
  return Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86_400_000
}

function getWeekDays(timestamp) {
  const currentDate = new Date(timestamp)
  currentDate.setHours(0, 0, 0, 0)
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(currentDate)
    date.setDate(date.getDate() - (6 - index))
    const day = dateKey(date)
    return {
      day,
      label: date.toLocaleDateString(undefined, { weekday: 'short' }),
    }
  })
}

function formatSessionDate(isoDate) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(Date.parse(isoDate))
}

function App() {
  const [initialState] = useState(loadSavedState)
  const [sessions, setSessions] = useState(initialState.sessions)
  const [timer, setTimer] = useState(initialState.activeTimer)
  const [durationMinutes, setDurationMinutes] = useState(25)
  const [task, setTask] = useState('')
  const [category, setCategory] = useState(CATEGORY_OPTIONS[0])
  const [now, setNow] = useState(INITIAL_NOW)
  const [notice, setNotice] = useState('')
  const [storageWarning, setStorageWarning] = useState(initialState.storageWarning)

  const timerRunning = Boolean(timer?.endsAt)
  const remainingSeconds = timerRunning
    ? Math.max(0, Math.ceil((timer.endsAt - now) / 1000))
    : timer?.remainingSeconds ?? durationMinutes * 60
  const timerProgress = timer
    ? Math.min(
        100,
        Math.max(
          0,
          ((timer.durationSeconds - remainingSeconds) / timer.durationSeconds) * 100,
        ),
      )
    : 0

  useEffect(() => {
    try {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions))
    } catch (error) {
      console.error('Could not save FocusAI sessions in browser storage.', error)
      window.setTimeout(
        () => setStorageWarning('Browser storage is unavailable. Your sessions may not persist.'),
        0,
      )
    }
  }, [sessions])

  useEffect(() => {
    try {
      if (timer) {
        localStorage.setItem(TIMER_STORAGE_KEY, JSON.stringify(timer))
      } else {
        localStorage.removeItem(TIMER_STORAGE_KEY)
      }
    } catch (error) {
      console.error('Could not save the active FocusAI timer in browser storage.', error)
      window.setTimeout(
        () => setStorageWarning('Browser storage is unavailable. Your timer may not survive a refresh.'),
        0,
      )
    }
  }, [timer])

  useEffect(() => {
    if (!timerRunning) return undefined
    const intervalId = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(intervalId)
  }, [timerRunning])

  const finishSession = useCallback((completed) => {
    if (!timer) return

    const remaining = timer.endsAt
      ? Math.max(0, Math.ceil((timer.endsAt - Date.now()) / 1000))
      : timer.remainingSeconds
    const elapsedSeconds = Math.max(0, timer.durationSeconds - remaining)

    if (elapsedSeconds > 0) {
      const savedSession = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        task: timer.task,
        category: timer.category,
        durationSeconds: elapsedSeconds,
        startedAt: timer.startedAt,
        completed: completed && remaining === 0,
      }
      setSessions((savedSessions) => [savedSession, ...savedSessions].slice(0, 500))
      setNotice(
        completed && remaining === 0
          ? 'Session complete. Nice work!'
          : `Session saved (${formatDuration(elapsedSeconds)}).`,
      )
    } else {
      setNotice('Session ended before any focus time was recorded.')
    }

    setTimer(null)
    setNow(Date.now())
  }, [timer])

  useEffect(() => {
    if (!timerRunning || remainingSeconds !== 0) return undefined
    const timeoutId = window.setTimeout(() => finishSession(true), 0)
    return () => window.clearTimeout(timeoutId)
  }, [timerRunning, remainingSeconds, finishSession])

  function startSession() {
    if (timer) return
    const totalSeconds = durationMinutes * 60
    setNotice('')
    setTimer({
      durationSeconds: totalSeconds,
      remainingSeconds: totalSeconds,
      endsAt: Date.now() + totalSeconds * 1000,
      task: task.trim() || 'Focus session',
      category,
      startedAt: new Date().toISOString(),
    })
    setNow(Date.now())
  }

  function pauseSession() {
    if (!timer?.endsAt) return
    const remaining = Math.max(0, Math.ceil((timer.endsAt - Date.now()) / 1000))
    setTimer({ ...timer, endsAt: null, remainingSeconds: remaining })
    setNow(Date.now())
  }

  function resumeSession() {
    if (!timer || timer.endsAt || timer.remainingSeconds <= 0) return
    setTimer({
      ...timer,
      endsAt: Date.now() + timer.remainingSeconds * 1000,
    })
    setNow(Date.now())
  }

  function jumpTo(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }

  const todayKey = dateKey(now)
  const todaySessions = sessions.filter(
    (session) => dateKey(session.startedAt) === todayKey,
  )
  const todayFocusSeconds = todaySessions.reduce(
    (total, session) => total + session.durationSeconds,
    0,
  )
  const totalFocusSeconds = sessions.reduce(
    (total, session) => total + session.durationSeconds,
    0,
  )

  const activeDays = new Set(sessions.map((session) => dateKey(session.startedAt)))
  let streakCursor = todayKey
  if (!activeDays.has(streakCursor)) streakCursor -= 1
  let streak = 0
  while (activeDays.has(streakCursor)) {
    streak += 1
    streakCursor -= 1
  }

  const weekDays = getWeekDays(now)
  const weeklyActivity = weekDays.map((day) => {
    const seconds = sessions
      .filter((session) => dateKey(session.startedAt) === day.day)
      .reduce((total, session) => total + session.durationSeconds, 0)
    return {
      date: day.day,
      seconds,
      label: day.label,
    }
  })
  const maxDailySeconds = Math.max(...weeklyActivity.map((day) => day.seconds), 1)

  const stats = [
    { label: 'Focus time', value: formatDuration(totalFocusSeconds), detail: 'saved on this browser' },
    { label: 'Sessions today', value: String(todaySessions.length), detail: formatDuration(todayFocusSeconds) + ' focused today' },
    { label: 'Current streak', value: `${streak} ${streak === 1 ? 'day' : 'days'}`, detail: streak ? 'consecutive active days' : 'start a session today' },
  ]

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand-wrap" href="#dashboard" aria-label="FocusAI home">
          <span className="brand-mark">F</span>
          <span className="brand-name">FocusAI</span>
        </a>

        <nav className="main-nav" aria-label="Main navigation">
          <a href="#dashboard">Timer</a>
          <a href="#features">Features</a>
          <a href="#analytics">Analytics</a>
          <a href="#history">Sessions</a>
        </nav>

        <button className="primary-button" type="button" onClick={() => jumpTo('dashboard')}>
          {timer ? 'Return to timer' : 'Start focusing'}
        </button>
      </header>

      <main>
        <section className="hero-section" id="dashboard">
          <div className="hero-copy">
            <p className="eyebrow">Your personal focus space</p>
            <h1>Turn focus into a measurable habit.</h1>
            <p className="hero-text">
              Start a timed work session, pause when you need to, and build a
              history of the time you actually focused.
            </p>

            <div className="cta-row">
              <button
                className="primary-button"
                type="button"
                onClick={() => (timer ? jumpTo('timer') : startSession())}
              >
                {timer ? 'View active session' : 'Start a session'}
              </button>
              <button className="secondary-button" type="button" onClick={() => jumpTo('analytics')}>
                View my progress
              </button>
            </div>

            <ul className="feature-badges" aria-label="Highlights">
              <li>Real countdown timer</li>
              <li>Pause and resume</li>
              <li>Progress saved locally</li>
            </ul>
          </div>

          <section className="hero-panel" id="timer" aria-label="Focus session timer">
            <div className="panel-topbar">
              <span className={`dot ${timerRunning ? 'green' : 'amber'}`} />
              <span className="timer-status">{timerRunning ? 'Session running' : timer ? 'Session paused' : 'Ready when you are'}</span>
            </div>

            <div className="timer-card">
              {!timer ? (
                <div className="session-setup">
                  <label htmlFor="task-name">What are you working on?</label>
                  <input
                    id="task-name"
                    maxLength={80}
                    onChange={(event) => setTask(event.target.value)}
                    placeholder="e.g. Read chapter 4"
                    value={task}
                  />
                  <div className="setup-row">
                    <div>
                      <label htmlFor="session-category">Category</label>
                      <select
                        id="session-category"
                        onChange={(event) => setCategory(event.target.value)}
                        value={category}
                      >
                        {CATEGORY_OPTIONS.map((option) => (
                          <option key={option} value={option}>{option}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label htmlFor="session-duration">Duration</label>
                      <select
                        id="session-duration"
                        onChange={(event) => setDurationMinutes(Number(event.target.value))}
                        value={durationMinutes}
                      >
                        {DURATION_OPTIONS.map((minutes) => (
                          <option key={minutes} value={minutes}>{minutes} minutes</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <div className="timer-meta">
                    <span>{timer.task}</span>
                    <span className="timer-badge">{timer.category}</span>
                  </div>
                  <p className="timer-subtitle">
                    {timerRunning ? 'Time to focus' : 'Paused'} · {Math.ceil(timer.durationSeconds / 60)} min session
                  </p>
                </>
              )}
              <div className="timer-value" aria-live="off">{formatTime(remainingSeconds)}</div>
              <div
                className="progress-bar"
                role="progressbar"
                aria-label="Session progress"
                aria-valuemin="0"
                aria-valuemax="100"
                aria-valuenow={Math.round(timerProgress)}
              >
                <span style={{ width: `${timerProgress}%` }} />
              </div>
              <div className="timer-actions">
                {!timer ? (
                  <button className="primary-button full-button" type="button" onClick={startSession}>
                    Start timer
                  </button>
                ) : timerRunning ? (
                  <button className="secondary-button" type="button" onClick={pauseSession}>
                    Pause
                  </button>
                ) : (
                  <button className="primary-button" type="button" onClick={resumeSession}>
                    Resume
                  </button>
                )}
                {timer && (
                  <button className="end-button" type="button" onClick={() => finishSession(false)}>
                    End session
                  </button>
                )}
              </div>
              {notice && <p className="notice" role="status">{notice}</p>}
            </div>

            <p className="storage-note">
              Sessions are saved in this browser only. They are separate from the Windows app’s data.
            </p>
          </section>
        </section>

        {storageWarning && <p className="storage-warning" role="alert">{storageWarning}</p>}

        <section className="stats-strip" id="analytics" aria-label="Your focus statistics">
          {stats.map((stat) => (
            <article className="stat-card" key={stat.label}>
              <div className="stat-label">{stat.label}</div>
              <div className="stat-value">{stat.value}</div>
              <div className="stat-detail">{stat.detail}</div>
            </article>
          ))}
        </section>

        <section className="preview-section analytics-section">
          <div className="preview-copy">
            <p className="eyebrow">Your last seven days</p>
            <h2>See momentum, one session at a time.</h2>
            <p>These bars use the focus sessions you have saved in this browser. No sample numbers are shown.</p>
          </div>

          <div className="preview-panel">
            <div className="panel-row panel-header">
              <span>Focus time by day</span>
              <span className="trend">{formatDuration(weeklyActivity.reduce((sum, day) => sum + day.seconds, 0))}</span>
            </div>
            <div className="bars" aria-label="Focus time for the last seven days">
              {weeklyActivity.map((day) => (
                <div className="bar-column" key={day.date} title={`${day.label}: ${formatDuration(day.seconds)}`}>
                  <span
                    className="activity-bar"
                    style={{ height: `${day.seconds ? Math.max(5, (day.seconds / maxDailySeconds) * 100) : 0}%` }}
                  />
                  <span className="bar-label">{day.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="features-section" id="features">
          <div className="section-heading">
            <p className="eyebrow">Simple by design</p>
            <h2>A calmer way to stay on task.</h2>
          </div>

          <div className="feature-grid">
            <article className="feature-card">
              <div className="feature-icon" aria-hidden="true">◷</div>
              <h3>A timer you control</h3>
              <p>Pick a focus interval, pause when needed, and save the time you actually spent.</p>
            </article>
            <article className="feature-card">
              <div className="feature-icon" aria-hidden="true">↗</div>
              <h3>Progress from your sessions</h3>
              <p>Your stats and weekly chart update from sessions saved in this browser.</p>
            </article>
            <article className="feature-card">
              <div className="feature-icon" aria-hidden="true">⌂</div>
              <h3>Private to your browser</h3>
              <p>No account or server is connected. Your browser storage stays separate from the desktop app.</p>
            </article>
          </div>
        </section>

        <section className="history-section" id="history">
          <div className="section-heading history-heading">
            <div>
              <p className="eyebrow">Your log</p>
              <h2>Recent sessions</h2>
            </div>
            {sessions.length > 0 && (
              <button
                className="end-button"
                type="button"
                onClick={() => {
                  if (window.confirm('Clear all sessions saved in this browser? This cannot be undone.')) {
                    setSessions([])
                    setNotice('Browser session history cleared.')
                  }
                }}
              >
                Clear history
              </button>
            )}
          </div>
          {sessions.length === 0 ? (
            <div className="empty-history">
              <p>No sessions yet. Start a timer to record your first focus session.</p>
            </div>
          ) : (
            <div className="history-list">
              {sessions.slice(0, 8).map((session) => (
                <article className="history-item" key={session.id}>
                  <div className="history-main">
                    <strong>{session.task}</strong>
                    <span>{session.category} · {formatSessionDate(session.startedAt)}</span>
                  </div>
                  <div className="history-duration">
                    <strong>{formatDuration(session.durationSeconds)}</strong>
                    <span>{session.completed ? 'Completed' : 'Ended early'}</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>

      <footer className="site-footer">
        <span>FocusAI</span>
        <span>Focus sessions and statistics are stored locally in this browser.</span>
      </footer>
    </div>
  )
}

export default App
