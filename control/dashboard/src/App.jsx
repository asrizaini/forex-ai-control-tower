import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Clipboard,
  Eye,
  EyeOff,
  Gauge,
  Globe2,
  KeyRound,
  LayoutDashboard,
  Lock,
  LogOut,
  MessageCircle,
  RadioTower,
  RefreshCw,
  Send,
  ServerCog,
  Settings2,
  ShieldCheck,
  Users,
  WalletCards,
} from 'lucide-react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const apiBase = import.meta.env.VITE_API_BASE || `${window.location.protocol}//${window.location.hostname}:8000`;
const wsBase = apiBase.replace(/^http/, 'ws');

const fallbackDashboardText = {
  title: 'Forex AI Control Tower',
  system_health: 'System Health',
  risk_status: 'Risk Status',
  orchestrator: 'Orchestrator',
  secret_manager: 'Secret Manager',
  agent_catalog: 'Agent Catalog',
  workflow_engine: 'Workflow Engine',
  mt5_demo_account: 'MT5 Demo Account',
  market_snapshot: 'Market Snapshot',
  control_plane: 'Control Plane',
  agent_theater: 'Agent Theater',
  talk_to_orchestrator: 'Talk To Orchestrator',
  send: 'Send',
};

const navItems = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'credentials', label: 'Credentials', icon: KeyRound },
  { id: 'control', label: 'Control Plane', icon: Settings2 },
  { id: 'theater', label: 'Agent Theater', icon: RadioTower },
  { id: 'health', label: 'Health', icon: Gauge },
];

function StatusBadge({ status = 'unknown', tone }) {
  const computed = tone || (['ok', 'healthy', 'running', 'active', 'configured'].includes(String(status).toLowerCase()) ? 'good' : 'warn');
  return <span className={`status-badge ${computed}`}>{status}</span>;
}

function MetricCard({ icon: Icon, label, value, detail, tone = 'good' }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon ${tone}`}><Icon size={20} /></div>
      <div>
        <p className="eyebrow">{label}</p>
        <strong>{value}</strong>
        {detail && <span>{detail}</span>}
      </div>
    </article>
  );
}

function App() {
  const [activeView, setActiveView] = useState('overview');
  const [health, setHealth] = useState({ status: 'loading', environment: 'demo', trading_mode: 'monitor_only', live_auto_trading: false });
  const [healthStatus, setHealthStatus] = useState({ healthy: false, services: {} });
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
  const [credentialStatus, setCredentialStatus] = useState({ items: [], missing_required: [], invalid: [], healthy: false });
  const [credentialInputs, setCredentialInputs] = useState({});
  const [visibleSecrets, setVisibleSecrets] = useState({});
  const [operatorStatus, setOperatorStatus] = useState('Authentication required.');
  const [newUser, setNewUser] = useState({ user_id: '', email: '', role: 'viewer', language: 'en' });
  const [newPermission, setNewPermission] = useState({ user_id: '', permission: 'dashboard:read', account_id: '', strategy_id: '' });
  const [newServiceKey, setNewServiceKey] = useState({ name: '', permissions: 'telemetry:write' });
  const [newTask, setNewTask] = useState({ assigned_agent: 'Orchestrator Agent', task_type: 'operator_request', request: '' });
  const [language, setLanguage] = useState('en');
  const [dashboardText, setDashboardText] = useState(fallbackDashboardText);
  const [chatMessage, setChatMessage] = useState('');
  const [chatStatus, setChatStatus] = useState('Ready for safe status questions.');
  const [oneTimeSecret, setOneTimeSecret] = useState(null);

  const authHeaders = () => token ? { Authorization: `Bearer ${token}` } : {};

  const loadPublicRuntime = async () => {
    try {
      const body = await fetch(`${apiBase}/health`).then((r) => r.json());
      setHealth(body);
    } catch {
      setHealth({ status: 'offline', environment: 'demo', trading_mode: 'monitor_only', live_auto_trading: false });
    }
  };

  const loadRuntime = async () => {
    await loadPublicRuntime();
    const requests = [
      fetch(`${apiBase}/api/v1/system/runtime`).then((r) => r.json()).then(setRuntime).catch(() => setRuntime({ orchestrator_event_log_exists: false })),
      fetch(`${apiBase}/api/v1/system/secret-manager/status`).then((r) => r.json()).then(setSecretStatus).catch(() => setSecretStatus({ active_provider: 'unknown', required_runtime_secrets_present: false })),
      fetch(`${apiBase}/api/v1/system/health/status`).then((r) => r.json()).then(setHealthStatus).catch(() => setHealthStatus({ healthy: false, services: {} })),
      fetch(`${apiBase}/api/v1/telemetry/market/latest?limit=6`).then((r) => r.json()).then(setMarketSnapshots).catch(() => setMarketSnapshots([])),
      fetch(`${apiBase}/api/v1/telemetry/accounts/latest?limit=1`).then((r) => r.json()).then(setAccountSnapshots).catch(() => setAccountSnapshots([])),
    ];
    await Promise.all(requests);
  };

  const loadTheater = async () => {
    const streamParam = selectedTheaterMode !== 'All Rooms' ? `&stream=${encodeURIComponent(selectedTheaterMode)}` : '';
    try {
      const body = await fetch(`${apiBase}/api/v1/agent-theater/events?limit=18&language=${encodeURIComponent(language)}${streamParam}`).then((r) => r.json());
      setEvents(body.events || []);
      setTheaterModes(body.modes || []);
    } catch {
      setEvents([]);
    }
  };

  const loadOperatorData = async () => {
    if (!token) return;
    const getJson = async (path, fallback) => {
      const response = await fetch(`${apiBase}${path}`, { headers: authHeaders() });
      if (response.status === 401 || response.status === 403) {
        logout();
        throw new Error('Session expired. Login again.');
      }
      if (!response.ok) return fallback;
      return response.json();
    };
    try {
      const [users, permissions, audit, tasks, serviceKeys, states, catalog, credentials] = await Promise.all([
        getJson('/api/v1/users/records', []),
        getJson('/api/v1/permissions', []),
        getJson('/api/v1/audit/logs', []),
        getJson('/api/v1/agents/tasks', []),
        getJson('/api/v1/service-keys', []),
        getJson('/api/v1/agents/states', []),
        getJson('/api/v1/agents/catalog', { agents: [] }),
        getJson('/api/v1/credentials/status', { items: [] }),
      ]);
      setOperatorData({ users, permissions, audit, tasks, serviceKeys, states, catalog: catalog.agents || [] });
      setCredentialStatus(credentials);
      setOperatorStatus('Control-plane data loaded.');
    } catch (error) {
      setOperatorStatus(error.message || 'Unable to load operator data.');
    }
  };

  useEffect(() => {
    fetch(`${apiBase}/api/v1/localization/locales/${encodeURIComponent(language)}/dashboard`)
      .then((r) => r.json())
      .then((body) => setDashboardText({ ...fallbackDashboardText, ...(body.messages || {}) }))
      .catch(() => setDashboardText(fallbackDashboardText));
  }, [language]);

  useEffect(() => {
    loadRuntime();
    loadTheater();
    const timer = window.setInterval(() => {
      loadRuntime();
      loadTheater();
    }, 15000);
    const ws = new WebSocket(`${wsBase}/ws/v1/agent-theater?language=${encodeURIComponent(language)}`);
    ws.onmessage = (message) => {
      const event = JSON.parse(message.data);
      if (selectedTheaterMode !== 'All Rooms' && event.stream !== selectedTheaterMode) return;
      setEvents((current) => [...current.slice(-50), event]);
    };
    ws.onerror = () => setChatStatus('Live feed reconnecting. REST refresh remains active.');
    return () => {
      window.clearInterval(timer);
      ws.close();
    };
  }, [language, selectedTheaterMode]);

  useEffect(() => {
    if (token) loadOperatorData();
  }, [token]);

  const credentialGroups = useMemo(() => {
    return (credentialStatus.items || []).reduce((groups, item) => {
      const key = item.category || 'Other';
      groups[key] = groups[key] || [];
      groups[key].push(item);
      return groups;
    }, {});
  }, [credentialStatus.items]);

  const serviceRows = Object.entries(healthStatus.services || {});
  const account = accountSnapshots[0];
  const configuredCount = (credentialStatus.items || []).filter((item) => item.configured).length;
  const missingRequired = credentialStatus.missing_required?.length || 0;

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

  const logout = () => {
    window.localStorage.removeItem('fx_access_token');
    window.localStorage.removeItem('fx_refresh_token');
    setToken('');
    setOperatorStatus('Logged out.');
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

  const saveCredential = async (name) => {
    const value = credentialInputs[name];
    if (value === undefined) {
      setOperatorStatus('Enter a value or generate one first.');
      return;
    }
    try {
      const response = await fetch(`${apiBase}/api/v1/credentials/${encodeURIComponent(name)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ value }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Credential save failed');
      setCredentialInputs((current) => ({ ...current, [name]: '' }));
      setOperatorStatus(`${name} saved. Secret value was not logged.`);
      await loadOperatorData();
    } catch (error) {
      setOperatorStatus(error.message || 'Credential save failed.');
    }
  };

  const generateCredential = async (name) => {
    try {
      const response = await fetch(`${apiBase}/api/v1/credentials/${encodeURIComponent(name)}/generate`, {
        method: 'POST',
        headers: { ...authHeaders() },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Credential generation failed');
      setCredentialInputs((current) => ({ ...current, [name]: payload.value }));
      setVisibleSecrets((current) => ({ ...current, [name]: true }));
      setOperatorStatus(`${name} generated. Save it when ready.`);
    } catch (error) {
      setOperatorStatus(error.message || 'Credential generation failed.');
    }
  };

  const revealCredential = async (name) => {
    try {
      const response = await fetch(`${apiBase}/api/v1/credentials/${encodeURIComponent(name)}/reveal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ confirm: true }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Credential reveal failed');
      setCredentialInputs((current) => ({ ...current, [name]: payload.value || '' }));
      setVisibleSecrets((current) => ({ ...current, [name]: true }));
      setOperatorStatus(`${name} revealed for this browser session. Audit record created.`);
    } catch (error) {
      setOperatorStatus(error.message || 'Credential reveal failed.');
    }
  };

  const copyCredential = async (name) => {
    const value = credentialInputs[name];
    if (!value) {
      setOperatorStatus('Nothing to copy. Reveal or generate the value first.');
      return;
    }
    await navigator.clipboard.writeText(value);
    setOperatorStatus(`${name} copied to clipboard.`);
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
      await loadTheater();
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
      await loadTheater();
    } catch (error) {
      setChatStatus(error.message || 'Unable to activate room.');
    }
  };

  if (!token) {
    return (
      <main className="login-shell">
        <section className="login-panel">
          <div className="brand-mark"><ShieldCheck size={30} /></div>
          <p className="eyebrow">Secure Operations Console</p>
          <h1>{dashboardText.title}</h1>
          <p className="login-copy">Authentication is required before viewing control-plane configuration, credentials, Agent Theater controls, or operational records.</p>
          <form className="login-card" onSubmit={doLogin}>
            <label>User ID<input value={login.user_id} onChange={(event) => setLogin({ ...login, user_id: event.target.value })} /></label>
            <label>Password<input type="password" value={login.password} onChange={(event) => setLogin({ ...login, password: event.target.value })} /></label>
            <label>2FA code<input value={login.totp_code} onChange={(event) => setLogin({ ...login, totp_code: event.target.value })} placeholder="Optional" /></label>
            <button type="submit"><Lock size={17} /> Login</button>
          </form>
          <p className="form-status">{operatorStatus}</p>
        </section>
        <aside className="login-status">
          <div className="topbar-actions">
            <label className="language"><Globe2 size={17} /><select value={language} onChange={(e) => setLanguage(e.target.value)}><option>en</option><option>ms-MY</option><option>auto</option></select></label>
            <button type="button" className="ghost-button" onClick={loadPublicRuntime}><RefreshCw size={16} /> Refresh</button>
          </div>
          <MetricCard icon={Activity} label="Public API" value={health.status} detail={`${health.environment} / ${health.trading_mode}`} tone={health.status === 'ok' ? 'good' : 'warn'} />
          <MetricCard icon={ShieldCheck} label="Live Automation" value={health.live_auto_trading ? 'enabled' : 'disabled'} detail="Safety default remains guarded" tone={health.live_auto_trading ? 'bad' : 'good'} />
        </aside>
      </main>
    );
  }

  return (
    <main className="console-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark"><ShieldCheck size={24} /></div>
          <div>
            <strong>Forex AI</strong>
            <span>Control Tower</span>
          </div>
        </div>
        <nav>
          {navItems.map(({ id, label, icon: Icon }) => (
            <button className={activeView === id ? 'active' : ''} type="button" key={id} onClick={() => setActiveView(id)}>
              <Icon size={18} /> {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <StatusBadge status={health.environment} tone="neutral" />
          <StatusBadge status={health.trading_mode} tone="good" />
        </div>
      </aside>

      <section className="workspace">
        <header className="console-topbar">
          <div>
            <p className="eyebrow">Operations Console</p>
            <h1>{dashboardText.title}</h1>
          </div>
          <div className="topbar-actions">
            <label className="language"><Globe2 size={17} /><select value={language} onChange={(e) => setLanguage(e.target.value)}><option>en</option><option>ms-MY</option><option>auto</option></select></label>
            <button type="button" className="ghost-button" onClick={() => { loadRuntime(); loadOperatorData(); loadTheater(); }}><RefreshCw size={16} /> Refresh</button>
            <button type="button" className="danger-button" onClick={logout}><LogOut size={16} /> Logout</button>
          </div>
        </header>

        <section className="status-strip">
          <MetricCard icon={Activity} label={dashboardText.system_health} value={health.status} detail={healthStatus.healthy ? 'Core services healthy' : 'Review health page'} tone={health.status === 'ok' ? 'good' : 'warn'} />
          <MetricCard icon={ShieldCheck} label={dashboardText.risk_status} value="Guarded" detail={health.live_auto_trading ? 'Live automation enabled' : 'Live automation disabled'} tone={health.live_auto_trading ? 'bad' : 'good'} />
          <MetricCard icon={ServerCog} label={dashboardText.orchestrator} value={runtime.orchestrator_event_log_exists ? 'Running' : 'Warming up'} detail={`${operatorData.catalog.length || 0} registered agents`} tone="good" />
          <MetricCard icon={KeyRound} label="Credential Readiness" value={credentialStatus.healthy ? 'Ready' : `${missingRequired} missing`} detail={`${configuredCount}/${credentialStatus.items?.length || 0} configured`} tone={credentialStatus.healthy ? 'good' : 'warn'} />
        </section>

        {activeView === 'overview' && (
          <section className="view-grid">
            <article className="panel account-panel">
              <div className="panel-heading"><WalletCards size={18} /><h2>{dashboardText.mt5_demo_account}</h2></div>
              {account ? (
                <div className="account-grid">
                  <span>Account<strong>{account.login_masked}</strong></span>
                  <span>Server<strong>{account.server}</strong></span>
                  <span>Equity<strong>{account.equity} {account.currency}</strong></span>
                  <span>Drawdown<strong>{account.drawdown_pct}%</strong></span>
                  <span>Positions<strong>{account.positions_count}</strong></span>
                  <span>Mode<strong>{account.risk_mode}</strong></span>
                </div>
              ) : <p>Waiting for account telemetry.</p>}
            </article>
            <article className="panel">
              <div className="panel-heading"><Activity size={18} /><h2>{dashboardText.market_snapshot}</h2></div>
              <div className="data-table">
                {marketSnapshots.length ? marketSnapshots.map((snapshot) => (
                  <div className="data-row" key={`${snapshot.symbol}-${snapshot.id}`}>
                    <strong>{snapshot.symbol}</strong>
                    <span>{snapshot.trend}</span>
                    <StatusBadge status={snapshot.feed_fresh ? 'fresh' : 'stale'} tone={snapshot.feed_fresh ? 'good' : 'warn'} />
                    <span>{snapshot.rates_count} candles</span>
                  </div>
                )) : <p>Waiting for market telemetry.</p>}
              </div>
            </article>
            <article className="panel wide-panel">
              <div className="panel-heading"><RadioTower size={18} /><h2>Recent Agent Theater</h2></div>
              <div className="compact-feed">
                {events.slice(-6).reverse().map((event, index) => (
                  <div className="feed-line" key={`${event.timestamp}-${index}`}>
                    <strong>{event.agent}</strong>
                    <span>{event.display?.summary || event.summary}</span>
                  </div>
                ))}
              </div>
            </article>
          </section>
        )}

        {activeView === 'credentials' && (
          <section className="panel">
            <div className="panel-heading spread">
              <div><h2><KeyRound size={18} /> Credentials Center</h2><p>Encrypted storage on fx-control. Normal responses remain masked.</p></div>
              <button type="button" className="primary-button" onClick={loadOperatorData}><RefreshCw size={16} /> Refresh Status</button>
            </div>
            <div className="credential-summary">
              <StatusBadge status={credentialStatus.healthy ? 'ready' : 'attention'} tone={credentialStatus.healthy ? 'good' : 'warn'} />
              <span>{configuredCount} configured</span>
              <span>{missingRequired} required missing</span>
              <span>{credentialStatus.invalid?.length || 0} invalid</span>
            </div>
            {Object.entries(credentialGroups).map(([group, items]) => (
              <section className="credential-section" key={group}>
                <h3>{group}</h3>
                <div className="credential-grid">
                  {items.map((item) => {
                    const visible = visibleSecrets[item.name];
                    const inputValue = credentialInputs[item.name] ?? '';
                    return (
                      <div className={`credential-row ${item.configured ? 'configured' : 'missing'}`} key={item.name}>
                        <div className="credential-meta">
                          <strong>{item.label}</strong>
                          <span>{item.required ? 'Required' : 'Optional'} · {item.source}</span>
                          <small>{item.validation_status}: {item.validation_message}</small>
                        </div>
                        <div className="credential-value">
                          <input
                            type={item.sensitive && !visible ? 'password' : 'text'}
                            placeholder={item.configured ? item.masked_value : item.placeholder || item.name}
                            value={inputValue}
                            onChange={(event) => setCredentialInputs((current) => ({ ...current, [item.name]: event.target.value }))}
                          />
                          <button type="button" title="Show or hide" onClick={() => setVisibleSecrets((current) => ({ ...current, [item.name]: !current[item.name] }))}>{visible ? <EyeOff size={15} /> : <Eye size={15} />}</button>
                          <button type="button" title="Copy current field value" onClick={() => copyCredential(item.name)}><Clipboard size={15} /></button>
                          {item.generator && <button type="button" onClick={() => generateCredential(item.name)}>Generate</button>}
                          {item.configured && <button type="button" onClick={() => revealCredential(item.name)}>Reveal</button>}
                          <button type="button" className="primary-button" onClick={() => saveCredential(item.name)}>Save</button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
            <p className="form-status">{operatorStatus}</p>
          </section>
        )}

        {activeView === 'control' && (
          <section className="control-layout">
            <article className="panel">
              <div className="panel-heading"><Users size={18} /><h2>Users</h2></div>
              <form className="compact-form" onSubmit={(event) => { event.preventDefault(); postAdmin('/api/v1/users/records', newUser, 'User created.'); }}>
                <input placeholder="user_id" value={newUser.user_id} onChange={(event) => setNewUser({ ...newUser, user_id: event.target.value })} />
                <input placeholder="email" value={newUser.email} onChange={(event) => setNewUser({ ...newUser, email: event.target.value })} />
                <select value={newUser.role} onChange={(event) => setNewUser({ ...newUser, role: event.target.value })}>
                  <option>viewer</option><option>extended_user</option><option>account_manager</option><option>strategy_admin</option><option>super_admin</option>
                </select>
                <button type="submit" className="primary-button">Create User</button>
              </form>
              <div className="mini-list">{operatorData.users.slice(0, 8).map((user) => <span key={user.user_id}>{user.user_id} · {user.role}</span>)}</div>
            </article>
            <article className="panel">
              <div className="panel-heading"><ShieldCheck size={18} /><h2>RBAC</h2></div>
              <form className="compact-form" onSubmit={(event) => {
                event.preventDefault();
                postAdmin('/api/v1/permissions', { ...newPermission, account_id: newPermission.account_id || null, strategy_id: newPermission.strategy_id || null }, 'Permission assigned.');
              }}>
                <input placeholder="user_id" value={newPermission.user_id} onChange={(event) => setNewPermission({ ...newPermission, user_id: event.target.value })} />
                <input placeholder="permission" value={newPermission.permission} onChange={(event) => setNewPermission({ ...newPermission, permission: event.target.value })} />
                <input placeholder="account_id optional" value={newPermission.account_id} onChange={(event) => setNewPermission({ ...newPermission, account_id: event.target.value })} />
                <button type="submit" className="primary-button">Assign Permission</button>
              </form>
              <div className="mini-list">{operatorData.permissions.slice(0, 8).map((item) => <span key={item.id}>{item.user_id} · {item.permission}</span>)}</div>
            </article>
            <article className="panel">
              <div className="panel-heading"><KeyRound size={18} /><h2>Service API Keys</h2></div>
              <form className="compact-form" onSubmit={async (event) => {
                event.preventDefault();
                const created = await postAdmin('/api/v1/service-keys', { name: newServiceKey.name, permissions: newServiceKey.permissions.split(',').map((item) => item.trim()).filter(Boolean) }, 'Service key created. Copy it now; it will not be shown again.');
                if (created?.api_key) setOneTimeSecret({ label: created.name || newServiceKey.name, value: created.api_key });
              }}>
                <input placeholder="key name" value={newServiceKey.name} onChange={(event) => setNewServiceKey({ ...newServiceKey, name: event.target.value })} />
                <input placeholder="permissions comma-separated" value={newServiceKey.permissions} onChange={(event) => setNewServiceKey({ ...newServiceKey, permissions: event.target.value })} />
                <button type="submit" className="primary-button">Create Key</button>
              </form>
              {oneTimeSecret && <div className="one-time-secret"><strong>{oneTimeSecret.label}</strong><input readOnly value={oneTimeSecret.value} /><button type="button" onClick={() => navigator.clipboard.writeText(oneTimeSecret.value)}>Copy</button></div>}
              <div className="mini-list">{operatorData.serviceKeys.slice(0, 8).map((item) => <span key={item.key_id}>{item.name} · {item.enabled ? 'enabled' : 'disabled'}</span>)}</div>
            </article>
            <article className="panel">
              <div className="panel-heading"><ServerCog size={18} /><h2>Agent Task Queue</h2></div>
              <form className="compact-form" onSubmit={(event) => {
                event.preventDefault();
                postAdmin('/api/v1/agents/tasks', { assigned_agent: newTask.assigned_agent, task_type: newTask.task_type, request_json: { request: newTask.request } }, 'Agent task queued.');
              }}>
                <input value={newTask.assigned_agent} onChange={(event) => setNewTask({ ...newTask, assigned_agent: event.target.value })} />
                <input value={newTask.task_type} onChange={(event) => setNewTask({ ...newTask, task_type: event.target.value })} />
                <input placeholder="request" value={newTask.request} onChange={(event) => setNewTask({ ...newTask, request: event.target.value })} />
                <button type="submit" className="primary-button">Queue Task</button>
              </form>
              <div className="mini-list">{operatorData.tasks.slice(0, 8).map((task) => <span key={task.task_id}>{task.assigned_agent} · {task.status}</span>)}</div>
            </article>
            <article className="panel wide-panel">
              <div className="panel-heading"><Activity size={18} /><h2>Audit Trail</h2></div>
              <div className="mini-list audit-list">{operatorData.audit.slice(0, 12).map((item) => <span key={item.id}>{item.actor} · {item.action} · {item.resource_type}:{item.resource_id}</span>)}</div>
            </article>
          </section>
        )}

        {activeView === 'theater' && (
          <section className="theater-layout">
            <article className="panel operator-chat">
              <div className="panel-heading"><MessageCircle size={18} /><h2>{dashboardText.talk_to_orchestrator}</h2></div>
              <label className="field-label">Room<select value={selectedTheaterMode} onChange={(event) => setSelectedTheaterMode(event.target.value)}><option>All Rooms</option>{theaterModes.map((mode) => <option key={mode}>{mode}</option>)}</select></label>
              <div className="operator-presets">
                {['System status?', 'Debate the safest next step.', 'Open the System Improvement Room.'].map((prompt) => <button type="button" key={prompt} onClick={() => setChatMessage(prompt)}>{prompt}</button>)}
                <button type="button" onClick={seedTheaterRoom}>Activate Room</button>
              </div>
              <form onSubmit={sendChat} className="chat-form">
                <textarea value={chatMessage} onChange={(event) => setChatMessage(event.target.value)} placeholder="Ask the Orchestrator about risk, MT5 bridge, strategies, notifications, or agents." rows={6} />
                <button type="submit" className="primary-button"><Send size={18} /> {dashboardText.send}</button>
              </form>
              <p className="form-status">{chatStatus}</p>
            </article>
            <article className="panel chat-room-panel">
              <div className="panel-heading spread"><h2>Live AI Trading Room</h2><StatusBadge status={selectedTheaterMode} tone="neutral" /></div>
              <div className="chat-room">
                {events.length ? events.slice().reverse().map((event, index) => (
                  <article className={`message ${event.agent === 'Operator' ? 'operator-message' : ''}`} key={`${event.timestamp}-${index}`}>
                    <div className="message-topline"><strong>{event.agent}</strong><span>{event.stream} · {event.timestamp}</span></div>
                    <p>{event.display?.summary || event.summary}</p>
                    <div className="message-meta"><span>{event.result}</span><span>{event.display?.risk_status || event.risk_status}</span><span>{event.display?.next_action || event.next_action}</span></div>
                  </article>
                )) : <p>Waiting for safe orchestrator summaries.</p>}
              </div>
            </article>
          </section>
        )}

        {activeView === 'health' && (
          <section className="panel">
            <div className="panel-heading spread"><div><h2><Gauge size={18} /> Service Health</h2><p>Source: `/api/v1/system/health/status` and Prometheus-facing API metrics.</p></div><StatusBadge status={healthStatus.healthy ? 'healthy' : 'attention'} tone={healthStatus.healthy ? 'good' : 'warn'} /></div>
            <div className="health-grid">
              {serviceRows.map(([name, details]) => (
                <div className="health-row" key={name}>
                  <strong>{name}</strong>
                  <StatusBadge status={details.status || 'unknown'} tone={details.status === 'ok' ? 'good' : 'warn'} />
                  <span>{details.url || details.required_runtime_secrets_present === true ? 'configured' : ''}</span>
                </div>
              ))}
            </div>
            {!healthStatus.healthy && <div className="warning-box"><AlertTriangle size={18} /> Review service readiness before enabling any new trading workflow.</div>}
          </section>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
