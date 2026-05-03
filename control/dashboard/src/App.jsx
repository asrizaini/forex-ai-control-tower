import React, { useEffect, useState } from 'react';
import { Activity, MessageCircle, Send, ShieldCheck, Globe2, RadioTower, ServerCog } from 'lucide-react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const apiBase = import.meta.env.VITE_API_BASE || `${window.location.protocol}//${window.location.hostname}:8000`;
const wsBase = apiBase.replace(/^http/, 'ws');

function App() {
  const [health, setHealth] = useState({ status: 'loading', environment: 'demo', trading_mode: 'monitor_only' });
  const [runtime, setRuntime] = useState({ orchestrator_event_log_exists: false });
  const [secretStatus, setSecretStatus] = useState({ active_provider: 'env', required_runtime_secrets_present: false });
  const [events, setEvents] = useState([]);
  const [theaterModes, setTheaterModes] = useState([]);
  const [selectedTheaterMode, setSelectedTheaterMode] = useState('All Rooms');
  const [marketSnapshots, setMarketSnapshots] = useState([]);
  const [accountSnapshots, setAccountSnapshots] = useState([]);
  const [token, setToken] = useState(window.localStorage.getItem('fx_access_token') || '');
  const [login, setLogin] = useState({ user_id: 'admin', password: '', totp_code: '' });
  const [operatorData, setOperatorData] = useState({ users: [], permissions: [], audit: [], tasks: [], serviceKeys: [], states: [], catalog: [] });
  const [operatorStatus, setOperatorStatus] = useState('Login to unlock admin control-plane panels.');
  const [newUser, setNewUser] = useState({ user_id: '', email: '', role: 'viewer', language: 'en' });
  const [newPermission, setNewPermission] = useState({ user_id: '', permission: 'dashboard:read', account_id: '', strategy_id: '' });
  const [newServiceKey, setNewServiceKey] = useState({ name: '', permissions: 'telemetry:write' });
  const [newTask, setNewTask] = useState({ assigned_agent: 'Orchestrator Agent', task_type: 'operator_request', request: '' });
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
      fetch(`${apiBase}/api/v1/system/secret-manager/status`).then((r) => r.json()).then(setSecretStatus).catch(() => {
        setSecretStatus({ active_provider: 'unknown', required_runtime_secrets_present: false });
      });
      const streamParam = selectedTheaterMode !== 'All Rooms' ? `&stream=${encodeURIComponent(selectedTheaterMode)}` : '';
      fetch(`${apiBase}/api/v1/agent-theater/events?limit=12&language=${encodeURIComponent(language)}${streamParam}`).then((r) => r.json()).then((body) => {
        setEvents(body.events || []);
        setTheaterModes(body.modes || []);
      }).catch(() => setEvents([]));
      fetch(`${apiBase}/api/v1/telemetry/market/latest?limit=4`).then((r) => r.json()).then(setMarketSnapshots).catch(() => setMarketSnapshots([]));
      fetch(`${apiBase}/api/v1/telemetry/accounts/latest?limit=1`).then((r) => r.json()).then(setAccountSnapshots).catch(() => setAccountSnapshots([]));
    };
    loadRuntime();
    const timer = window.setInterval(loadRuntime, 15000);
    const ws = new WebSocket(`${wsBase}/ws/v1/agent-theater?language=${encodeURIComponent(language)}`);
    ws.onmessage = (message) => {
      const event = JSON.parse(message.data);
      if (selectedTheaterMode !== 'All Rooms' && event.stream !== selectedTheaterMode) return;
      setEvents((current) => [...current.slice(-40), event]);
    };
    return () => {
      window.clearInterval(timer);
      ws.close();
    };
  }, [language, selectedTheaterMode]);

  useEffect(() => {
    if (!token) return;
    loadOperatorData();
  }, [token]);

  const authHeaders = () => token ? { Authorization: `Bearer ${token}` } : {};

  const loadOperatorData = async () => {
    try {
      const [users, permissions, audit, tasks, serviceKeys, states, catalog] = await Promise.all([
        fetch(`${apiBase}/api/v1/users/records`, { headers: authHeaders() }).then((r) => r.json()),
        fetch(`${apiBase}/api/v1/permissions`, { headers: authHeaders() }).then((r) => r.json()),
        fetch(`${apiBase}/api/v1/audit/logs`, { headers: authHeaders() }).then((r) => r.ok ? r.json() : []),
        fetch(`${apiBase}/api/v1/agents/tasks`, { headers: authHeaders() }).then((r) => r.json()),
        fetch(`${apiBase}/api/v1/service-keys`, { headers: authHeaders() }).then((r) => r.ok ? r.json() : []),
        fetch(`${apiBase}/api/v1/agents/states`, { headers: authHeaders() }).then((r) => r.json()),
        fetch(`${apiBase}/api/v1/agents/catalog`, { headers: authHeaders() }).then((r) => r.json()),
      ]);
      setOperatorData({ users, permissions, audit, tasks, serviceKeys, states, catalog: catalog.agents || [] });
      setOperatorStatus('Control-plane data loaded.');
    } catch (error) {
      setOperatorStatus(error.message || 'Unable to load operator data.');
    }
  };

  const doLogin = async (event) => {
    event.preventDefault();
    setOperatorStatus('Logging in...');
    try {
      const response = await fetch(`${apiBase}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: login.user_id, password: login.password, totp_code: login.totp_code || null }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Login failed');
      window.localStorage.setItem('fx_access_token', body.access_token);
      if (body.refresh_token) window.localStorage.setItem('fx_refresh_token', body.refresh_token);
      setToken(body.access_token);
      setLogin((current) => ({ ...current, password: '', totp_code: '' }));
      setOperatorStatus('Logged in.');
    } catch (error) {
      setOperatorStatus(error.message || 'Login failed.');
    }
  };

  const postAdmin = async (path, body, success) => {
    try {
      const response = await fetch(`${apiBase}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Request failed');
      setOperatorStatus(success || 'Saved.');
      await loadOperatorData();
      return payload;
    } catch (error) {
      setOperatorStatus(error.message || 'Request failed.');
      return null;
    }
  };

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

  const seedTheaterRoom = async () => {
    if (selectedTheaterMode === 'All Rooms') {
      setChatStatus('Choose a room first, then I can seed its safe status message.');
      return;
    }
    try {
      const response = await fetch(`${apiBase}/api/v1/agent-theater/rooms/${encodeURIComponent(selectedTheaterMode)}/seed`, {
        method: 'POST',
        headers: { ...authHeaders() },
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Unable to activate room');
      setChatStatus(`${selectedTheaterMode} is active.`);
    } catch (error) {
      setChatStatus(error.message || 'Unable to activate room.');
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
      <section className="grid">
        <article><ShieldCheck /><h2>Secret Manager</h2><strong>{secretStatus.active_provider}</strong><p>{secretStatus.required_runtime_secrets_present ? 'Required runtime secrets present' : 'Missing required runtime secret'}</p></article>
        <article><ServerCog /><h2>Agent Catalog</h2><strong>{operatorData.catalog.length || 'login required'}</strong><p>Registered governed agents</p></article>
        <article><Activity /><h2>Workflow Engine</h2><strong>{operatorData.states.length ? 'active' : 'running'}</strong><p>DB-backed task processing</p></article>
      </section>
      <section className="telemetry-grid">
        <article>
          <h2>MT5 Demo Account</h2>
          {accountSnapshots[0] ? (
            <div className="telemetry-list">
              <span>Account <strong>{accountSnapshots[0].login_masked}</strong></span>
              <span>Server <strong>{accountSnapshots[0].server}</strong></span>
              <span>Equity <strong>{accountSnapshots[0].equity} {accountSnapshots[0].currency}</strong></span>
              <span>Drawdown <strong>{accountSnapshots[0].drawdown_pct}%</strong></span>
              <span>Positions <strong>{accountSnapshots[0].positions_count}</strong></span>
              <span>Mode <strong>{accountSnapshots[0].risk_mode}</strong></span>
            </div>
          ) : <p>Waiting for account telemetry.</p>}
        </article>
        <article>
          <h2>Market Snapshot</h2>
          {marketSnapshots.length ? (
            <div className="market-table">
              {marketSnapshots.map((snapshot) => (
                <div className="market-row" key={`${snapshot.symbol}-${snapshot.id}`}>
                  <strong>{snapshot.symbol}</strong>
                  <span>{snapshot.trend}</span>
                  <span>{snapshot.feed_fresh ? 'fresh' : 'stale'}</span>
                  <span>{snapshot.rates_count} candles</span>
                </div>
              ))}
            </div>
          ) : <p>Waiting for market telemetry.</p>}
        </article>
      </section>
      <section className="admin-panel">
        <div className="section-title">
          <ShieldCheck size={20} />
          <h2>Control Plane</h2>
        </div>
        {!token ? (
          <form className="admin-login" onSubmit={doLogin}>
            <input value={login.user_id} onChange={(event) => setLogin({ ...login, user_id: event.target.value })} placeholder="User ID" />
            <input type="password" value={login.password} onChange={(event) => setLogin({ ...login, password: event.target.value })} placeholder="Password" />
            <input value={login.totp_code} onChange={(event) => setLogin({ ...login, totp_code: event.target.value })} placeholder="2FA code if enabled" />
            <button type="submit">Login</button>
          </form>
        ) : (
          <div className="admin-actions">
            <button type="button" onClick={loadOperatorData}>Refresh Control Plane</button>
            <button type="button" onClick={() => { window.localStorage.removeItem('fx_access_token'); setToken(''); }}>Logout</button>
          </div>
        )}
        <p className="chat-status">{operatorStatus}</p>
        {token && (
          <div className="admin-grid">
            <article>
              <h2>Users</h2>
              <form className="compact-form" onSubmit={(event) => {
                event.preventDefault();
                postAdmin('/api/v1/users/records', newUser, 'User created.');
              }}>
                <input placeholder="user_id" value={newUser.user_id} onChange={(event) => setNewUser({ ...newUser, user_id: event.target.value })} />
                <input placeholder="email" value={newUser.email} onChange={(event) => setNewUser({ ...newUser, email: event.target.value })} />
                <select value={newUser.role} onChange={(event) => setNewUser({ ...newUser, role: event.target.value })}>
                  <option>viewer</option><option>extended_user</option><option>account_manager</option><option>strategy_admin</option><option>super_admin</option>
                </select>
                <button type="submit">Create User</button>
              </form>
              <div className="mini-list">{operatorData.users.slice(0, 6).map((user) => <span key={user.user_id}>{user.user_id} · {user.role}</span>)}</div>
            </article>
            <article>
              <h2>RBAC</h2>
              <form className="compact-form" onSubmit={(event) => {
                event.preventDefault();
                postAdmin('/api/v1/permissions', { ...newPermission, account_id: newPermission.account_id || null, strategy_id: newPermission.strategy_id || null }, 'Permission assigned.');
              }}>
                <input placeholder="user_id" value={newPermission.user_id} onChange={(event) => setNewPermission({ ...newPermission, user_id: event.target.value })} />
                <input placeholder="permission" value={newPermission.permission} onChange={(event) => setNewPermission({ ...newPermission, permission: event.target.value })} />
                <input placeholder="account_id optional" value={newPermission.account_id} onChange={(event) => setNewPermission({ ...newPermission, account_id: event.target.value })} />
                <button type="submit">Assign Permission</button>
              </form>
              <div className="mini-list">{operatorData.permissions.slice(0, 6).map((item) => <span key={item.id}>{item.user_id} · {item.permission}</span>)}</div>
            </article>
            <article>
              <h2>Service API Keys</h2>
              <form className="compact-form" onSubmit={async (event) => {
                event.preventDefault();
                const created = await postAdmin('/api/v1/service-keys', { name: newServiceKey.name, permissions: newServiceKey.permissions.split(',').map((item) => item.trim()).filter(Boolean) }, 'Service key created. Copy it now from the response modal if needed.');
                if (created?.api_key) window.alert(`Service key created. Store it now; it will not be shown again.\\n${created.api_key}`);
              }}>
                <input placeholder="key name" value={newServiceKey.name} onChange={(event) => setNewServiceKey({ ...newServiceKey, name: event.target.value })} />
                <input placeholder="permissions comma-separated" value={newServiceKey.permissions} onChange={(event) => setNewServiceKey({ ...newServiceKey, permissions: event.target.value })} />
                <button type="submit">Create Key</button>
              </form>
              <div className="mini-list">{operatorData.serviceKeys.slice(0, 6).map((item) => <span key={item.key_id}>{item.name} · {item.enabled ? 'enabled' : 'disabled'}</span>)}</div>
            </article>
            <article>
              <h2>Agent Task Queue</h2>
              <form className="compact-form" onSubmit={(event) => {
                event.preventDefault();
                postAdmin('/api/v1/agents/tasks', { assigned_agent: newTask.assigned_agent, task_type: newTask.task_type, request_json: { request: newTask.request } }, 'Agent task queued.');
              }}>
                <input value={newTask.assigned_agent} onChange={(event) => setNewTask({ ...newTask, assigned_agent: event.target.value })} />
                <input value={newTask.task_type} onChange={(event) => setNewTask({ ...newTask, task_type: event.target.value })} />
                <input placeholder="request" value={newTask.request} onChange={(event) => setNewTask({ ...newTask, request: event.target.value })} />
                <button type="submit">Queue Task</button>
              </form>
              <div className="mini-list">{operatorData.tasks.slice(0, 6).map((task) => <span key={task.task_id}>{task.assigned_agent} · {task.status}</span>)}</div>
            </article>
            <article>
              <h2>Agent States</h2>
              <div className="mini-list">{operatorData.states.slice(0, 8).map((state) => <span key={state.agent_name}>{state.agent_name} · {state.status}</span>)}</div>
            </article>
            <article className="wide-card">
              <h2>Audit Trail</h2>
              <div className="mini-list audit-list">{operatorData.audit.slice(0, 10).map((item) => <span key={item.id}>{item.actor} · {item.action} · {item.resource_type}:{item.resource_id}</span>)}</div>
            </article>
          </div>
        )}
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
            <label className="room-select">
              Room
              <select value={selectedTheaterMode} onChange={(event) => setSelectedTheaterMode(event.target.value)}>
                <option>All Rooms</option>
                {theaterModes.map((mode) => <option key={mode}>{mode}</option>)}
              </select>
            </label>
            <div className="operator-presets">
              {['System status?', 'Debate the safest next step.', 'Open the System Improvement Room.'].map((prompt) => (
                <button type="button" key={prompt} onClick={() => setChatMessage(prompt)}>{prompt}</button>
              ))}
              <button type="button" onClick={seedTheaterRoom}>Activate Room</button>
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
                  <p>{event.display?.summary || event.summary}</p>
                  <div className="message-meta">
                    <span>{event.result}</span>
                    <span>{event.display?.risk_status || event.risk_status}</span>
                    <span>{event.display?.next_action || event.next_action}</span>
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
