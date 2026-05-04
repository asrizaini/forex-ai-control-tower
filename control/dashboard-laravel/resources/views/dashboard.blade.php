<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Forex AI Control Tower</title>
    <style>
        :root {
            --bg: #f3f6fa;
            --surface: #ffffff;
            --surface-soft: #f8fafc;
            --ink: #111827;
            --muted: #64748b;
            --line: #d8e1ec;
            --line-strong: #c6d3e1;
            --nav: #121a27;
            --nav-soft: #1d293a;
            --accent: #087568;
            --accent-dark: #075d55;
            --blue: #0f5f79;
            --ok-bg: #e7f7ef;
            --ok: #0a7657;
            --warn-bg: #fff6df;
            --warn: #946200;
            --bad-bg: #fdebed;
            --bad: #b4232f;
        }
        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body {
            margin: 0;
            background: var(--bg);
            color: var(--ink);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        a { color: var(--accent); font-weight: 760; text-decoration: none; }
        h1, h2, h3, p { margin: 0; letter-spacing: 0; }
        h1 { font-size: 27px; line-height: 1.2; }
        h2 { font-size: 17px; line-height: 1.3; }
        h3 { font-size: 14px; line-height: 1.3; }
        p { color: var(--muted); line-height: 1.45; }
        button, input, select, textarea { font: inherit; }
        input, select, textarea {
            background: #fff;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            color: #162032;
            min-width: 0;
            padding: 10px 11px;
            width: 100%;
        }
        input:focus, select:focus, textarea:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(8, 117, 104, .13);
            outline: none;
        }
        label { color: #334155; display: grid; font-size: 12px; font-weight: 780; gap: 6px; }
        .shell {
            display: grid;
            grid-template-columns: 264px minmax(0, 1fr);
            min-height: 100vh;
        }
        .sidebar {
            background: var(--nav);
            color: #fff;
            display: flex;
            flex-direction: column;
            gap: 20px;
            padding: 22px 16px;
        }
        .brand { align-items: center; display: flex; gap: 12px; }
        .brand-mark {
            align-items: center;
            background: var(--accent);
            border-radius: 8px;
            display: flex;
            font-weight: 850;
            height: 42px;
            justify-content: center;
            width: 42px;
        }
        .brand strong { color: #fff; display: block; }
        .brand span { color: #aebbd0; display: block; font-size: 13px; margin-top: 2px; }
        .nav { display: grid; gap: 6px; }
        .nav a {
            border: 1px solid transparent;
            border-radius: 6px;
            color: #cbd5e1;
            padding: 11px 12px;
        }
        .nav a:hover { background: var(--nav-soft); border-color: #344256; color: #fff; }
        .side-status {
            border-top: 1px solid #2b374a;
            display: grid;
            gap: 9px;
            margin-top: auto;
            padding-top: 16px;
        }
        .workspace { display: grid; gap: 18px; padding: 24px; }
        .topbar, .panel, .metric, .credential-row {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
        }
        .topbar {
            align-items: center;
            display: flex;
            gap: 18px;
            justify-content: space-between;
            min-height: 96px;
            padding: 20px;
        }
        .actions { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; }
        .button, button {
            align-items: center;
            background: var(--accent);
            border: 1px solid var(--accent);
            border-radius: 6px;
            color: #fff;
            cursor: pointer;
            display: inline-flex;
            font-weight: 780;
            justify-content: center;
            min-height: 39px;
            padding: 9px 12px;
            white-space: nowrap;
        }
        .button:hover, button:hover { background: var(--accent-dark); border-color: var(--accent-dark); }
        .button.secondary, button.secondary { background: #fff; border-color: #cbd5e1; color: #263241; }
        .button.secondary:hover, button.secondary:hover { background: #f8fafc; border-color: #9fb0c4; }
        .button.danger, button.danger { background: #fff; border-color: #f1c6c9; color: var(--bad); }
        .button.danger:hover, button.danger:hover { background: var(--bad-bg); border-color: #e39ba1; }
        .button.small, button.small { min-height: 34px; padding: 7px 10px; }
        .notice {
            border-radius: 8px;
            padding: 12px 14px;
        }
        .notice.ok { background: var(--ok-bg); color: var(--ok); }
        .notice.bad { background: var(--bad-bg); color: var(--bad); }
        .notice.warn { background: var(--warn-bg); color: var(--warn); }
        .badge {
            border-radius: 6px;
            display: inline-flex;
            font-size: 12px;
            font-weight: 820;
            padding: 5px 8px;
            text-transform: uppercase;
            width: fit-content;
        }
        .badge.ok { background: var(--ok-bg); color: var(--ok); }
        .badge.warn { background: var(--warn-bg); color: var(--warn); }
        .badge.bad { background: var(--bad-bg); color: var(--bad); }
        .eyebrow {
            color: #69778a;
            font-size: 12px;
            font-weight: 790;
            text-transform: uppercase;
        }
        .status-grid {
            display: grid;
            gap: 14px;
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }
        .metric {
            display: grid;
            gap: 5px;
            min-height: 112px;
            padding: 16px;
        }
        .metric strong { color: #111827; display: block; font-size: 26px; line-height: 1.1; }
        .metric span { color: var(--muted); display: block; font-size: 13px; }
        .grid-2 { display: grid; gap: 14px; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
        .panel { padding: 18px; }
        .panel-head {
            align-items: flex-start;
            display: flex;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 16px;
        }
        .login-form, .password-form {
            display: grid;
            gap: 10px;
            grid-template-columns: minmax(140px, 1fr) minmax(180px, 1fr) minmax(150px, .8fr) auto;
        }
        .password-form { grid-template-columns: minmax(180px, 1fr) minmax(180px, 1fr) auto; }
        .data-table { display: grid; gap: 8px; }
        .data-row, .service-row {
            align-items: center;
            border-bottom: 1px solid #e8edf3;
            display: grid;
            gap: 10px;
            padding: 10px 0;
        }
        .data-row { grid-template-columns: 1fr 1fr auto .8fr; }
        .service-row { grid-template-columns: 170px auto minmax(0, 1fr); }
        .empty { color: var(--muted); padding: 16px 0; }
        .security-panel {
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
        }
        .credential-summary {
            align-items: center;
            background: var(--surface-soft);
            border: 1px solid #e6ecf3;
            border-radius: 8px;
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 18px;
            padding: 12px;
        }
        .pending-secret {
            background: #fffaf0;
            border: 1px solid #e9cf92;
            border-radius: 8px;
            display: grid;
            gap: 12px;
            margin-bottom: 16px;
            padding: 14px;
        }
        .pending-grid {
            display: grid;
            gap: 10px;
            grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
        }
        .secret-line {
            display: grid;
            gap: 8px;
            grid-template-columns: minmax(0, 1fr) auto;
        }
        .credential-section {
            border-top: 1px solid #e8edf3;
            display: grid;
            gap: 10px;
            padding-top: 18px;
        }
        .credential-section + .credential-section { margin-top: 20px; }
        .credential-row {
            display: grid;
            gap: 14px;
            grid-template-columns: minmax(250px, .95fr) minmax(240px, .8fr) minmax(320px, 1.15fr);
            padding: 14px;
        }
        .credential-row.configured { border-color: #bee5d9; }
        .credential-row.missing { border-color: #ecd6a4; }
        .credential-meta { display: grid; gap: 5px; }
        .credential-meta span, .credential-meta small, .current-value small {
            color: var(--muted);
            font-size: 12px;
        }
        .current-value {
            align-content: start;
            display: grid;
            gap: 6px;
        }
        .masked-value {
            background: var(--surface-soft);
            border: 1px solid #e1e8f0;
            border-radius: 6px;
            color: #334155;
            min-height: 39px;
            overflow-wrap: anywhere;
            padding: 10px 11px;
        }
        .credential-actions {
            display: grid;
            gap: 9px;
        }
        .credential-update {
            display: grid;
            gap: 8px;
            grid-template-columns: minmax(0, 1fr) auto;
        }
        .credential-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .chat-list { display: grid; gap: 10px; max-height: 410px; overflow: auto; }
        .chat-item {
            background: var(--surface-soft);
            border: 1px solid #e1e8f0;
            border-radius: 8px;
            display: grid;
            gap: 8px;
            padding: 13px;
        }
        .chat-top { display: flex; gap: 10px; justify-content: space-between; }
        .chat-top span { color: var(--muted); font-size: 12px; }
        @media (max-width: 1180px) {
            .status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .grid-2, .credential-row, .pending-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 820px) {
            .shell { grid-template-columns: 1fr; }
            .sidebar { position: static; }
            .workspace { padding: 16px; }
            .topbar, .panel-head { align-items: stretch; flex-direction: column; }
            .status-grid, .login-form, .password-form, .data-row, .service-row, .credential-update { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
@php
    $pending = session('pending_generated_credential');
    $revealed = session('generated_secret');
@endphp
<main class="shell">
    <aside class="sidebar">
        <div class="brand">
            <div class="brand-mark">FX</div>
            <div>
                <strong>Forex AI</strong>
                <span>Control Tower Console</span>
            </div>
        </div>
        <nav class="nav">
            <a href="#overview">Overview</a>
            <a href="#security">Admin Security</a>
            <a href="#credentials">Credentials Center</a>
            <a href="#health">Service Health</a>
            <a href="#agents">Agent Theater</a>
        </nav>
        <div class="side-status">
            <span class="badge ok">{{ $readiness['environment'] ?? 'demo' }}</span>
            <span class="badge ok">{{ $readiness['trading_mode'] ?? 'monitor_only' }}</span>
            <span class="badge {{ !empty($authenticated) ? 'ok' : 'warn' }}">{{ !empty($authenticated) ? 'authenticated' : 'login required' }}</span>
        </div>
    </aside>

    <section class="workspace">
        <header class="topbar">
            <div>
                <p class="eyebrow">Enterprise Operations Console</p>
                <h1>Forex AI Control Tower</h1>
                <p>{{ $readiness['environment'] ?? 'demo' }} environment · {{ $readiness['trading_mode'] ?? 'monitor_only' }} trading mode · Laravel primary dashboard</p>
            </div>
            <div class="actions">
                <a class="button secondary" href="{{ $links['docs'] }}" target="_blank" rel="noreferrer">API Docs</a>
                <a class="button secondary" href="{{ $links['grafana'] }}" target="_blank" rel="noreferrer">Grafana</a>
                @if($authenticated)
                    <form method="POST" action="{{ route('logout') }}">
                        @csrf
                        <button class="danger" type="submit">Logout</button>
                    </form>
                @endif
            </div>
        </header>

        @if(session('status'))
            <div class="notice ok">{{ session('status') }}</div>
        @endif
        @if(session('error'))
            <div class="notice bad">{{ session('error') }}</div>
        @endif
        @if($errors->any())
            <div class="notice bad">{{ $errors->first() }}</div>
        @endif

        @if(!$authenticated)
            <section class="panel">
                <div class="panel-head">
                    <div>
                        <h2>Secure Login</h2>
                        <p>Use the FastAPI control-plane admin account. Laravel stores only your authenticated session token.</p>
                    </div>
                    <span class="badge warn">authentication required</span>
                </div>
                <form class="login-form" method="POST" action="{{ route('login') }}">
                    @csrf
                    <input name="user_id" value="admin" autocomplete="username" aria-label="User ID">
                    <input name="password" type="password" autocomplete="current-password" aria-label="Password">
                    <input name="totp_code" autocomplete="one-time-code" aria-label="2FA code" placeholder="2FA code if enabled">
                    <button type="submit">Login</button>
                </form>
            </section>
        @endif

        <section id="overview" class="status-grid">
            <div class="metric">
                <span class="eyebrow">System Health</span>
                <strong>{{ $health['status'] ?? 'unknown' }}</strong>
                <span>Control API public health</span>
            </div>
            <div class="metric">
                <span class="eyebrow">Live Automation</span>
                <strong>{{ !empty($health['live_auto_trading']) ? 'enabled' : 'disabled' }}</strong>
                <span>Default safety posture</span>
            </div>
            <div class="metric">
                <span class="eyebrow">Credentials</span>
                <strong>{{ ($credentials['configured_count'] ?? 0) }}/{{ count($credentials['items'] ?? []) }}</strong>
                <span>{{ ($credentials['missing_required'] ?? []) ? 'Required values missing' : 'Required values ready' }}</span>
            </div>
            <div class="metric">
                <span class="eyebrow">Production Live</span>
                <strong>{{ !empty($readiness['live_trading_allowed']) ? 'ready' : 'blocked' }}</strong>
                <span>Approval-gated and risk-controlled</span>
            </div>
        </section>

        <section class="grid-2">
            <article class="panel">
                <div class="panel-head"><h2>MT5 Account</h2><span class="badge ok">demo guarded</span></div>
                @php
                    $account = $accounts[0] ?? null;
                @endphp
                @if($account)
                    <div class="data-table">
                        <div class="data-row"><strong>Account</strong><span>{{ $account['login_masked'] ?? '-' }}</span><span></span><span>{{ $account['server'] ?? '-' }}</span></div>
                        <div class="data-row"><strong>Equity</strong><span>{{ $account['equity'] ?? '-' }} {{ $account['currency'] ?? '' }}</span><span></span><span>DD {{ $account['drawdown_pct'] ?? 0 }}%</span></div>
                        <div class="data-row"><strong>Positions</strong><span>{{ $account['positions_count'] ?? 0 }}</span><span></span><span>{{ $account['risk_mode'] ?? 'monitor_only' }}</span></div>
                    </div>
                @else
                    <p class="empty">Waiting for account telemetry.</p>
                @endif
            </article>
            <article class="panel">
                <div class="panel-head"><h2>Market Feed</h2><span class="badge {{ count($market) ? 'ok' : 'warn' }}">{{ count($market) }} symbols</span></div>
                <div class="data-table">
                    @forelse($market as $item)
                        <div class="data-row">
                            <strong>{{ $item['symbol'] ?? '-' }}</strong>
                            <span>{{ $item['trend'] ?? '-' }}</span>
                            <span class="badge {{ !empty($item['feed_fresh']) ? 'ok' : 'warn' }}">{{ !empty($item['feed_fresh']) ? 'fresh' : 'stale' }}</span>
                            <span>{{ $item['rates_count'] ?? 0 }} candles</span>
                        </div>
                    @empty
                        <p class="empty">No market snapshots available.</p>
                    @endforelse
                </div>
            </article>
        </section>

        <section id="security" class="panel security-panel">
            <div class="panel-head">
                <div>
                    <h2>Admin Security</h2>
                    <p>Change the active control-plane admin password from the dashboard. Password values are sent only to the authenticated API endpoint.</p>
                </div>
                <span class="badge {{ $authenticated ? 'ok' : 'warn' }}">{{ $authenticated ? 'available' : 'login required' }}</span>
            </div>
            @if($authenticated)
                <form class="password-form" method="POST" action="{{ route('password.update') }}">
                    @csrf
                    <label>New admin password
                        <input name="password" type="password" autocomplete="new-password" minlength="12" required>
                    </label>
                    <label>Confirm password
                        <input name="password_confirmation" type="password" autocomplete="new-password" minlength="12" required>
                    </label>
                    <button type="submit">Change Password</button>
                </form>
            @else
                <p class="empty">Login to change the admin password.</p>
            @endif
        </section>

        <section id="credentials" class="panel">
            <div class="panel-head">
                <div>
                    <h2>Credentials Center</h2>
                    <p>Each field uses the real credential catalog. Current secret values stay masked; new values are saved only when you click Save or Apply Generated.</p>
                </div>
                <span class="badge {{ !empty($credentials['healthy']) ? 'ok' : 'warn' }}">{{ !empty($credentials['healthy']) ? 'ready' : 'attention' }}</span>
            </div>

            @if($pending)
                <div class="pending-secret">
                    <div class="panel-head">
                        <div>
                            <h3>Generated Value Pending Approval</h3>
                            <p>{{ $pending['message'] }}</p>
                        </div>
                        <span class="badge warn">not applied</span>
                    </div>
                    <div class="pending-grid">
                        <label>Current {{ $pending['label'] ?? $pending['name'] }}
                            <div class="masked-value">{{ $pending['current'] ?? 'not configured' }}</div>
                        </label>
                        <label>Generated {{ $pending['label'] ?? $pending['name'] }}
                            <div class="secret-line">
                                <input id="pending-generated-secret" readonly value="{{ $pending['value'] }}" autocomplete="off">
                                <button class="secondary" type="button" onclick="navigator.clipboard.writeText(document.getElementById('pending-generated-secret').value)">Copy</button>
                            </div>
                        </label>
                    </div>
                    <div class="credential-buttons">
                        <form method="POST" action="{{ route('credentials.apply-generated', $pending['name']) }}">
                            @csrf
                            <button type="submit">Apply Generated</button>
                        </form>
                        <form method="POST" action="{{ route('credentials.discard-generated') }}">
                            @csrf
                            <button class="secondary" type="submit">Discard</button>
                        </form>
                    </div>
                </div>
            @endif

            @if($revealed)
                <div class="pending-secret">
                    <div class="panel-head">
                        <div>
                            <h3>Secret Revealed For This Session</h3>
                            <p>{{ $revealed['message'] }}</p>
                        </div>
                        <span class="badge warn">audited</span>
                    </div>
                    <label>{{ $revealed['name'] }}
                        <div class="secret-line">
                            <input id="revealed-secret" readonly value="{{ $revealed['value'] }}" autocomplete="off">
                            <button class="secondary" type="button" onclick="navigator.clipboard.writeText(document.getElementById('revealed-secret').value)">Copy</button>
                        </div>
                    </label>
                </div>
            @endif

            @if(!$authenticated)
                <p class="empty">Login to configure credentials.</p>
            @else
                <div class="credential-summary">
                    <span class="badge {{ !empty($credentials['healthy']) ? 'ok' : 'warn' }}">{{ !empty($credentials['healthy']) ? 'healthy' : 'needs input' }}</span>
                    <span>{{ $credentials['configured_count'] ?? 0 }} configured</span>
                    <span>{{ count($credentials['missing_required'] ?? []) }} required missing</span>
                    <span>{{ count($credentials['invalid'] ?? []) }} invalid</span>
                </div>

                @foreach($credentialGroups as $category => $items)
                    <section class="credential-section">
                        <h3>{{ $category }}</h3>
                        @foreach($items as $item)
                            @php
                                $fieldType = $item['field_type'] ?? 'text';
                                $options = $item['options'] ?? [];
                                $currentForEdit = (!$item['sensitive'] && !empty($item['configured'])) ? ($item['masked_value'] ?? '') : '';
                                $currentLabel = !empty($item['configured']) ? ($item['masked_value'] ?? 'configured') : 'not configured';
                                $inputType = match ($fieldType) {
                                    'email' => 'email',
                                    'number' => 'number',
                                    'date' => 'date',
                                    default => $item['sensitive'] ? 'password' : 'text',
                                };
                            @endphp
                            <div class="credential-row {{ !empty($item['configured']) ? 'configured' : 'missing' }}">
                                <div class="credential-meta">
                                    <strong>{{ $item['label'] }}</strong>
                                    <span>{{ $item['name'] }} · {{ !empty($item['required']) ? 'required' : 'optional' }}</span>
                                    <small>{{ $item['validation_status'] ?? 'unknown' }}: {{ $item['validation_message'] ?? '-' }}</small>
                                    @if(!empty($item['restart_hint']))
                                        <small>Apply target: {{ $item['restart_hint'] }}</small>
                                    @endif
                                </div>
                                <div class="current-value">
                                    <small>Current value</small>
                                    <div class="masked-value">{{ $currentLabel }}</div>
                                    <span class="badge {{ !empty($item['configured']) ? 'ok' : 'warn' }}">{{ !empty($item['configured']) ? ($item['source'] ?? 'configured') : 'missing' }}</span>
                                </div>
                                <div class="credential-actions">
                                    <form method="POST" action="{{ route('credentials.update', $item['name']) }}" class="credential-update">
                                        @csrf
                                        @if($fieldType === 'boolean' || $fieldType === 'select')
                                            <select name="value" aria-label="New value for {{ $item['name'] }}">
                                                <option value="">Not configured</option>
                                                @foreach($options as $option)
                                                    <option value="{{ $option }}" @selected($currentForEdit === $option)>{{ $option }}</option>
                                                @endforeach
                                            </select>
                                        @else
                                            <input name="value" type="{{ $inputType }}" value="{{ $currentForEdit }}" placeholder="{{ !empty($item['sensitive']) ? 'Enter replacement value' : 'Enter value' }}" autocomplete="off" aria-label="New value for {{ $item['name'] }}">
                                        @endif
                                        <button type="submit">Save</button>
                                    </form>
                                    <div class="credential-buttons">
                                        @if(!empty($item['generator']))
                                            <form method="POST" action="{{ route('credentials.generate', $item['name']) }}">
                                                @csrf
                                                <button class="secondary small" type="submit">Generate</button>
                                            </form>
                                        @endif
                                        @if(!empty($item['configured']))
                                            <form method="POST" action="{{ route('credentials.reveal', $item['name']) }}">
                                                @csrf
                                                <button class="secondary small" type="submit">Reveal Current</button>
                                            </form>
                                        @endif
                                    </div>
                                </div>
                            </div>
                        @endforeach
                    </section>
                @endforeach
            @endif
        </section>

        <section id="health" class="panel">
            <div class="panel-head">
                <div><h2>Service Health</h2><p>API, database, monitoring, credential readiness, and required services.</p></div>
                <span class="badge {{ !empty($healthStatus['healthy']) ? 'ok' : 'warn' }}">{{ !empty($healthStatus['healthy']) ? 'healthy' : 'attention' }}</span>
            </div>
            @forelse(($healthStatus['services'] ?? []) as $name => $service)
                <div class="service-row">
                    <strong>{{ $name }}</strong>
                    <span class="badge {{ ($service['status'] ?? '') === 'ok' ? 'ok' : 'warn' }}">{{ $service['status'] ?? 'unknown' }}</span>
                    <span>{{ $service['url'] ?? (!empty($service['required_runtime_secrets_present']) ? 'configured' : '') }}</span>
                </div>
            @empty
                <p class="empty">Service health feed unavailable.</p>
            @endforelse
        </section>

        <section id="agents" class="panel">
            <div class="panel-head"><h2>Agent Theater</h2><span class="badge ok">safe summaries only</span></div>
            <div class="chat-list">
                @forelse(($agentEvents['events'] ?? []) as $event)
                    <div class="chat-item">
                        <div class="chat-top"><strong>{{ $event['agent'] ?? 'Agent' }}</strong><span>{{ $event['stream'] ?? 'Live Chat View' }} · {{ $event['timestamp'] ?? '' }}</span></div>
                        <p>{{ $event['display']['summary'] ?? $event['summary'] ?? '-' }}</p>
                    </div>
                @empty
                    <p class="empty">Waiting for Agent Theater events.</p>
                @endforelse
            </div>
        </section>
    </section>
</main>
</body>
</html>
