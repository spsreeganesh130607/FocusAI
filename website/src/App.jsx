import './App.css'

const navItems = ['Dashboard', 'Features', 'Analytics', 'Pricing']

const stats = [
  { label: 'Focus hours', value: '42h', detail: 'this month' },
  { label: 'Session streak', value: '12 days', detail: 'on track' },
  { label: 'Tasks finished', value: '87%', detail: 'completion rate' },
]

const features = [
  {
    title: 'Smart focus timer',
    text: 'Structure deep work in planned bursts with a clean, distraction-free flow.',
  },
  {
    title: 'Activity insights',
    text: 'Track your attention patterns and spot the habits that help you stay productive.',
  },
  {
    title: 'Mood-aware goals',
    text: 'Adjust your study session rhythm based on energy, work type, and personal pace.',
  },
]

const sessionCards = [
  { title: 'Deep work', label: 'Productive', minutes: '25m', tone: 'productive' },
  { title: 'Review notes', label: 'Neutral', minutes: '15m', tone: 'neutral' },
  { title: 'Inbox check', label: 'Distracting', minutes: '8m', tone: 'distracting' },
]

function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-wrap">
          <div className="brand-mark">F</div>
          <span className="brand-name">FocusAI</span>
        </div>

        <nav className="main-nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <a href="#" key={item}>
              {item}
            </a>
          ))}
        </nav>

        <button className="primary-button" type="button">
          Launch app
        </button>
      </header>

      <main>
        <section className="hero-section">
          <div className="hero-copy">
            <p className="eyebrow">AI-powered study flow</p>
            <h1>Turn focus into a measurable habit.</h1>
            <p className="hero-text">
              FocusAI helps students and professionals plan deep-work sessions,
              monitor attention, and build momentum with smarter, calmer routines.
            </p>

            <div className="cta-row">
              <button className="primary-button" type="button">
                Start a session
              </button>
              <button className="secondary-button" type="button">
                View dashboard
              </button>
            </div>

            <ul className="feature-badges" aria-label="Highlights">
              <li>Smart timer</li>
              <li>Progress insights</li>
              <li>Distraction tracking</li>
            </ul>
          </div>

          <div className="hero-panel" aria-label="FocusAI dashboard preview">
            <div className="panel-topbar">
              <span className="dot green" />
              <span className="dot amber" />
              <span className="dot red" />
            </div>

            <div className="timer-card">
              <div className="timer-meta">
                <span>Current session</span>
                <span className="timer-badge">25 min</span>
              </div>
              <div className="timer-value">19:42</div>
              <div className="progress-bar">
                <span style={{ width: '75%' }} />
              </div>
            </div>

            <div className="mini-grid">
              {sessionCards.map((card) => (
                <div key={card.title} className={`mini-card ${card.tone}`}>
                  <div className="mini-label">{card.label}</div>
                  <div className="mini-title">{card.title}</div>
                  <div className="mini-time">{card.minutes}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="stats-strip" aria-label="Performance stats">
          {stats.map((stat) => (
            <div className="stat-card" key={stat.label}>
              <div className="stat-label">{stat.label}</div>
              <div className="stat-value">{stat.value}</div>
              <div className="stat-detail">{stat.detail}</div>
            </div>
          ))}
        </section>

        <section className="features-section" id="features">
          <div className="section-heading">
            <p className="eyebrow">Why FocusAI</p>
            <h2>Built to keep your best work steady.</h2>
          </div>

          <div className="feature-grid">
            {features.map((feature) => (
              <article className="feature-card" key={feature.title}>
                <div className="feature-icon" aria-hidden="true">
                  ✓
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="preview-section">
          <div className="preview-copy">
            <p className="eyebrow">Daily overview</p>
            <h2>See momentum, not just minutes.</h2>
            <p>
              Built on a desktop study flow, this website version focuses on the
              core experience: layered productivity analytics, calm scheduling, and a
              visual sense of progress over time.
            </p>
          </div>

          <div className="preview-panel">
            <div className="panel-row panel-header">
              <span>Week overview</span>
              <span className="trend">+18%</span>
            </div>

            <div className="bars" aria-label="Analytics bars">
              <span style={{ height: '35%' }} />
              <span style={{ height: '48%' }} />
              <span style={{ height: '62%' }} />
              <span style={{ height: '74%' }} />
              <span style={{ height: '82%' }} />
              <span style={{ height: '91%' }} />
              <span style={{ height: '100%' }} />
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <span>FocusAI</span>
        <span>Study smarter. Stay present.</span>
      </footer>
    </div>
  )
}

export default App
