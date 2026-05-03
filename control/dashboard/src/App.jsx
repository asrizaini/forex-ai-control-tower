import React, { useEffect, useState } from 'react';
import { Activity, MessageCircle, Send, ShieldCheck, Globe2, RadioTower, ServerCog } from 'lucide-react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const apiBase = import.meta.env.VITE_API_BASE || `${window.location.protocol}//${window.location.hostname}:8000`;
const wsBase = apiBase.replace(/^http/, 'ws');

function App() {
  const [health, setHealth] = useState({ status: 'loading', environment: 'demo', trading_mode: 'monitor_only' });
  const [runtime, setRuntime] = useState({ orchestrator_event_log_exists: false });
  const [events, setEvents] = useState([]);
  const [language, setLanguage] = useState('en');
  const [chatMessage, setChatMessage] = useState('');
  const [chatStatus, setChatStatus] = useState('Ready for safe status questions.');

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
    const ws = new WebSocket(`${wsBase}/ws/v1/agent-theater`);
    ws.onmessage = (message) => {
      const event = JSON.parse(message.data);
      setEvents((current) => [...current.slice(-40), event]);
    };
    return () => {
      window.clearInterval(timer);
      ws.close();
    };
  }, []);

  const sendChat = async (event) => {
    event.preventDefault();
    const message = chatMessage.trim();
    if (!message) return;
    setChatStatus('Sending to Orchestrator...');
    setChatMessage('');
    try {
      const response = await fetch(`${apiBase}/api/v1/agent-theater/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, language, session_id: 'dashboard-operator' }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Chat request failed');
      setChatStatus(body.next_action || 'Orchestrator replied in Agent Theater.');
    } catch (error) {
      setChatStatus(error.message || 'Unable to reach Orchestrator chat.');
    }
  };

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
        <div className="theater-layout">
          <div className="operator-chat">
            <div className="operator-heading">
              <MessageCircle size={20} />
              <h3>Talk To Orchestrator</h3>
            </div>
            <div className="operator-presets">
              {['System status?', 'What is blocking demo trading?', 'What should we wire next?'].map((prompt) => (
                <button type="button" key={prompt} onClick={() => setChatMessage(prompt)}>{prompt}</button>
              ))}
            </div>
            <form onSubmit={sendChat} className="chat-form">
              <textarea
                value={chatMessage}
                onChange={(event) => setChatMessage(event.target.value)}
                placeholder="Ask the Orchestrator about status, risk, MT5 bridge, strategies, notifications, or agents."
                rows={5}
              />
              <button type="submit" aria-label="Send message to Orchestrator"><Send size={18} /> Send</button>
            </form>
            <p className="chat-status">{chatStatus}</p>
          </div>
          {events.length === 0 ? (
            <p>Waiting for safe orchestrator summaries.</p>
          ) : (
            <div className="chat-room">
              {events.slice().reverse().map((event, index) => (
                <article className={`message ${event.agent === 'Operator' ? 'operator-message' : ''}`} key={`${event.timestamp}-${index}`}>
                  <div className="message-topline">
                    <strong>{event.agent}</strong>
                    <span>{event.stream} · {event.timestamp}</span>
                  </div>
                  <p>{event.summary}</p>
                  <div className="message-meta">
                    <span>{event.result}</span>
                    <span>{event.risk_status}</span>
                    <span>{event.next_action}</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
