import React, { useEffect, useState } from 'react';
import { Activity, ShieldCheck, Globe2, RadioTower } from 'lucide-react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

function App() {
  const [health, setHealth] = useState({ status: 'loading', environment: 'demo', trading_mode: 'monitor_only' });
  const [language, setLanguage] = useState('en');

  useEffect(() => {
    fetch(`${apiBase}/health`).then((r) => r.json()).then(setHealth).catch(() => {
      setHealth({ status: 'offline', environment: 'demo', trading_mode: 'monitor_only' });
    });
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
        <article><RadioTower /><h2>Agent Theater</h2><strong>Safe summaries only</strong></article>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
