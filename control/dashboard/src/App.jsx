import React, { useEffect, useState } from 'react';
import { Activity, ShieldCheck, Globe2, RadioTower, ServerCog } from 'lucide-react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const apiBase = import.meta.env.VITE_API_BASE || `${window.location.protocol}//${window.location.hostname}:8000`;

function App() {
  const [health, setHealth] = useState({ status: 'loading', environment: 'demo', trading_mode: 'monitor_only' });
  const [runtime, setRuntime] = useState({ orchestrator_event_log_exists: false });
  const [events, setEvents] = useState([]);
  const [language, setLanguage] = useState('en');

  useEffect(() => {
    fetch(`${apiBase}/health`).then((r) => r.json()).then(setHealth).catch(() => {
      setHealth({ status: 'offline', environment: 'demo', trading_mode: 'monitor_only' });
    });

    const loadRuntime = () => {
      fetch(`${apiBase}/api/v1/system/runtime`).then((r) => r.json()).then(setRuntime).catch(() => {
        setRuntime({ orchestrator_event_log_exists: false });
      });
      fetch(`${apiBase}/api/v1/agent-theater/events?limit=8`).then((r) => r.json()).then((body) => {
        setEvents(body.events || []);
      }).catch(() => setEvents([]));
    };
    loadRuntime();
    const timer = window.setInterval(loadRuntime, 15000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>Forex AI Control Tower</h1>
          <p>{health.environment} · {health.trading_mode}</p>
        </div>
        <label className="language"><Globe2 size={18} /> <select value={language} onChange={(e) => setLanguage(e.target.value)}><option>en</option><option>ms-MY</option><option>auto</option></select></label>
      </header>
      <section className="grid">
        <article><Activity /><h2>System Health</h2><strong>{health.status}</strong></article>
        <article><ShieldCheck /><h2>Risk Status</h2><strong>Execution guarded</strong></article>
        <article><ServerCog /><h2>Orchestrator</h2><strong>{runtime.orchestrator_event_log_exists ? 'running' : 'warming up'}</strong></article>
      </section>
      <section className="theater">
        <div className="section-title">
          <RadioTower size={20} />
          <h2>Agent Theater</h2>
        </div>
        {events.length === 0 ? (
          <p>Waiting for safe orchestrator summaries.</p>
        ) : (
          <div className="events">
            {events.slice().reverse().map((event, index) => (
              <article className="event" key={`${event.timestamp}-${index}`}>
                <div className="event-topline">
                  <strong>{event.agent}</strong>
                  <span>{event.timestamp}</span>
                </div>
                <p>{event.summary}</p>
                <dl>
                  <div><dt>Result</dt><dd>{event.result}</dd></div>
                  <div><dt>Risk</dt><dd>{event.risk_status}</dd></div>
                  <div><dt>Next</dt><dd>{event.next_action}</dd></div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
