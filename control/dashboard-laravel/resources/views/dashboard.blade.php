<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Forex AI Control Tower</title>
    <style>
        :root {
            --bg: #eef2f6;
            --panel: #ffffff;
            --panel-2: #f8fafc;
            --ink: #111827;
            --muted: #64748b;
            --line: #d9e1ea;
            --accent: #0d7767;
            --accent-2: #0f5f79;
            --ok-bg: #e8f7f1;
            --ok: #0d7767;
            --warn-bg: #fff6df;
            --warn: #9a6700;
            --bad-bg: #fdecee;
            --bad: #b4232f;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            background: var(--bg);
            color: var(--ink);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        a { color: var(--accent); font-weight: 750; text-decoration: none; }
        h1, h2, h3, p { margin: 0; letter-spacing: 0; }
        h1 { font-size: 26px; }
        h2 { font-size: 16px; }
        h3 { color: #243143; font-size: 14px; margin-bottom: 10px; }
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
            box-shadow: 0 0 0 3px rgba(13, 119, 103, 0.12);
            outline: none;
        }
        .shell {
            display: grid;
            grid-template-columns: 250px minmax(0, 1fr);
            min-height: 100vh;
        }
        .sidebar {
            background: #111827;
            color: #fff;
            display: flex;
            flex-direction: column;
            gap: 18px;
            padding: 22px 16px;
        }
        .brand { align-items: center; display: flex; gap: 12px; }
        .brand-mark {
            align-items: center;
            background: var(--accent);
            border-radius: 8px;
            display: flex;
            font-weight: 850;
            height: 40px;
            justify-content: center;
            width: 40px;
        }
        .brand strong { color: #fff; display: block; }
        .brand span { color: #aebbd0; font-size: 13px; }
        .nav { display: grid; gap: 6px; }
        .nav a {
            border: 1px solid transparent;
            border-radius: 6px;
            color: #cbd5e1;
            padding: 11px 12px;
        }
        .nav a:hover { background: #1f2a3d; border-color: #344256; color: #fff; }
        .sidebar-footer {
            display: grid;
            gap: 8px;
            margin-top: auto;
        }
        .workspace {
            display: grid;
            gap: 18px;
            padding: 24px;
        }
        .topbar, .panel, .metric {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
        }
        .topbar {
            align-items: center;
            display: flex;
            justify-content: space-between;
            min-height: 88px;
            padding: 18px 20px;
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
            font-weight: 760;
            justify-content: center;
            padding: 10px 12px;
        }
        .button.secondary, button.secondary { background: #fff; border-color: #cbd5e1; color: #263241; }
        .button.danger, button.danger { background: #fff; border-color: #f1c6c9; color: var(--bad); }
        .status-grid {
            display: grid;
            gap: 14px;
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }
        .metric {
            align-items: center;
            display: grid;
            min-height: 108px;
            padding: 16px;
        }
        .metric small, .eyebrow {
            color: #69778a;
            font-size: 12px;
            font-weight: 760;
            text-transform: uppercase;
        }
        .metric strong { color: #111827; display: block; font-size: 24px; margin-top: 5px; }
        .metric span { color: var(--muted); display: block; font-size: 13px; margin-top: 4px; }
        .grid-2 { display: grid; gap: 14px; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
        .panel { padding: 18px; }
        .wide { grid-column: 1 / -1; }
        .panel-head {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 16px;
        }
        .badge {
            border-radius: 6px;
            display: inline-flex;
            font-size: 12px;
            font-weight: 800;
            padding: 5px 8px;
            text-transform: uppercase;
        }
        .badge.ok { background: var(--ok-bg); color: var(--ok); }
        .badge.warn { background: var(--warn-bg); color: var(--warn); }
        .badge.bad { background: var(--bad-bg); color: var(--bad); }
        .notice {
            border-radius: 8px;
            margin-bottom: 14px;
            padding: 12px;
        }
        .notice.ok { background: var(--ok-bg); color: var(--ok); }
        .notice.bad { background: var(--bad-bg); color: var(--bad); }
        .login-form {
            display: grid;
            gap: 10px;
            grid-template-columns: minmax(140px, 1fr) minmax(160px, 1fr) minmax(120px, .7fr) auto;
        }
        .data-table { display: grid; gap: 8px; }
        .data-row {
            align-items: center;
            border-bottom: 1px solid #e8edf3;
            display: grid;
            gap: 10px;
            grid-template-columns: 1fr 1fr auto .8fr;
            padding: 10px 0;
        }
        .service-row {
            align-items: center;
            border-bottom: 1px solid #e8edf3;
            display: grid;
            gap: 10px;
            grid-template-columns: 160px auto minmax(0, 1fr);
            padding: 10px 0;
        }
        .chat-list { display: grid; gap: 10px; max-height: 380px; overflow: auto; }
        .chat-item {
            background: var(--panel-2);
            border: 1px solid #e1e8f0;
            border-radius: 8px;
            display: grid;
            gap: 8px;
            padding: 13px;
        }
        .chat-top { display: flex; gap: 10px; justify-content: space-between; }
        .chat-top span { color: var(--muted); font-size: 12px; }
        .credential-summary {
            align-items: center;
            background: var(--panel-2);
            border: 1px solid #e6ecf3;
            border-radius: 8px;
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 18px;
            padding: 12px;
        }
        .credential-section { border-top: 1px solid #e8edf3; padding-top: 18px; }
        .credential-section + .credential-section { margin-top: 20px; }
        .credential-row {
            border: 1px solid var(--line);
            border-radius: 8px;
            display: grid;
            gap: 12px;
            grid-template-columns: minmax(240px, .85fr) minmax(0, 1.7fr);
            margin-top: 10px;
            padding: 12px;
        }
        .credential-row.configured { background: #fbfffd; border-color: #c8e8dd; }
        .credential-row.missing { background: #fffdf8; border-color: #edd8a7; }
        .credential-meta { display: grid; gap: 4px; }
        .credential-meta span, .credential-meta small { color: var(--muted); font-size: 12px; }
        .credential-form {
            align-items: center;
            display: grid;
            gap: 8px;
            grid-template-columns: minmax(170px, 1fr) auto auto auto;
        }
        .generated-secret {
            background: #fff6df;
            border: 1px solid #edd8a7;
            border-radius: 8px;
            display: grid;
            gap: 10px;
            margin-bottom: 16px;
            padding: 12px;
        }
        .secret-copy { display: grid; gap: 8px; grid-template-columns: minmax(0, 1fr) auto; }
        .empty { color: var(--muted); padding: 16px 0; }
        @media (max-width: 1080px) {
            .shell { grid-template-columns: 1fr; }
            .sidebar { position: static; }
            .status-grid, .grid-2, .login-form, .credential-row, .credential-form { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
<main class="shell">
    <aside class="sidebar">
        <div class="brand">
            <div class="brand-mark">FX</div>
            <div><strong>Forex AI</strong><span>Laravel Control Console</span></div>
        </div>
        <nav class="nav">
            <a href="#overview">Overview</a>
            <a href="#credentials">Credentials</a>
            <a href="#health">Health</a>
            <a href="#agents">Agent Theater</a>
        </nav>
        <div class="sidebar-footer">
            <span class="badge ok">{{ $readiness['environment'] ?? 'demo' }}</span>
            <span class="badge ok">{{ $readiness['trading_mode'] ?? 'monitor_only' }}</span>
        </div>
    </aside>

    <section class="workspace">
        <header class="topbar">
            <div>
                <p class="eyebrow">Operations Console</p>
                <h1>Forex AI Control Tower</h1>
                <p>{{ $readiness['environment'] ?? 'demo' }} · {{ $readiness['trading_mode'] ?? 'monitor_only' }} · Laravel primary dashboard</p>
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

        @if(!$authenticated)
            <section class="panel">
                <div class="panel-head">
                    <div>
                        <h2>Secure Login</h2>
                        <p>Use the FastAPI control-plane admin account. Credentials are not stored by Laravel.</p>
                    </div>
                    <span class="badge warn">authentication required</span>
                </div>
                <form class="login-form" method="POST" action="{{ route('login') }}">
                    @csrf
                    <input name="user_id" value="admin" autocomplete="username" aria-label="User ID">
                    <input name="password" type="password" autocomplete="current-password" aria-label="Password">
                    <input name="totp_code" autocomplete="one-time-code" aria-label="2FA code">
                    <button type="submit">Login</button>
                </form>
            </section>
        @endif

        <section id="overview" class="status-grid">
            <div class="metric"><small>System Health</small><strong>{{ $health['status'] ?? 'unknown' }}</strong><span>Control API public health</span></div>
            <div class="metric"><small>Live Automation</small><strong>{{ !empty($health['live_auto_trading']) ? 'enabled' : 'disabled' }}</strong><span>Default safety posture</span></div>
            <div class="metric"><small>Credentials</small><strong>{{ ($credentials['configured_count'] ?? 0) }}/{{ count($credentials['items'] ?? []) }}</strong><span>{{ ($credentials['missing_required'] ?? []) ? 'Required values missing' : 'Required values ready' }}</span></div>
            <div class="metric"><small>Production Live</small><strong>{{ !empty($readiness['live_trading_allowed']) ? 'ready' : 'blocked' }}</strong><span>Approval-gated</span></div>
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

        <section id="credentials" class="panel">
            <div class="panel-head">
                <div>
                    <h2>Credentials Center</h2>
                    <p>Fields are generated from the real FastAPI credential catalog. Secret values are masked unless explicitly revealed.</p>
                </div>
                <span class="badge {{ !empty($credentials['healthy']) ? 'ok' : 'warn' }}">{{ !empty($credentials['healthy']) ? 'ready' : 'attention' }}</span>
            </div>

            @if(session('generated_secret'))
                <div class="generated-secret">
                    <strong>{{ session('generated_secret.name') }}</strong>
                    <p>{{ session('generated_secret.message') }}</p>
                    <div class="secret-copy">
                        <input id="generated-secret" readonly value="{{ session('generated_secret.value') }}">
                        <button class="secondary" type="button" onclick="navigator.clipboard.writeText(document.getElementById('generated-secret').value)">Copy</button>
                    </div>
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
                                $current = (!$item['sensitive'] && !empty($item['configured'])) ? ($item['masked_value'] ?? '') : '';
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
                                    <span>{{ $item['name'] }} · {{ !empty($item['required']) ? 'required' : 'optional' }} · {{ $item['source'] ?? 'missing' }}</span>
                                    <small>{{ $item['validation_status'] ?? 'unknown' }}: {{ $item['validation_message'] ?? '-' }}</small>
                                    @if(!empty($item['restart_hint']))
                                        <small>Apply target: {{ $item['restart_hint'] }}</small>
                                    @endif
                                </div>
                                <div class="credential-form">
                                    <form method="POST" action="{{ route('credentials.update', $item['name']) }}" class="credential-form">
                                        @csrf
                                        @if($fieldType === 'boolean' || $fieldType === 'select')
                                            <select name="value">
                                                <option value="">Not configured</option>
                                                @foreach($options as $option)
                                                    <option value="{{ $option }}" @selected($current === $option)>{{ $option }}</option>
                                                @endforeach
                                            </select>
                                        @else
                                            <input name="value" type="{{ $inputType }}" value="{{ $current }}" autocomplete="off">
                                        @endif
                                        <button type="submit">Save</button>
                                    </form>
                                    @if(!empty($item['generator']))
                                        <form method="POST" action="{{ route('credentials.generate', $item['name']) }}">
                                            @csrf
                                            <button class="secondary" type="submit">Generate</button>
                                        </form>
                                    @endif
                                    @if(!empty($item['configured']))
                                        <form method="POST" action="{{ route('credentials.reveal', $item['name']) }}">
                                            @csrf
                                            <button class="secondary" type="submit">Reveal</button>
                                        </form>
                                    @endif
                                </div>
                            </div>
                        @endforeach
                    </section>
                @endforeach
            @endif
        </section>

        <section id="health" class="panel">
            <div class="panel-head">
                <div><h2>Service Health</h2><p>API, database, monitoring, and credential readiness.</p></div>
                <span class="badge {{ !empty($healthStatus['healthy']) ? 'ok' : 'warn' }}">{{ !empty($healthStatus['healthy']) ? 'healthy' : 'attention' }}</span>
            </div>
            @foreach(($healthStatus['services'] ?? []) as $name => $service)
                <div class="service-row">
                    <strong>{{ $name }}</strong>
                    <span class="badge {{ ($service['status'] ?? '') === 'ok' ? 'ok' : 'warn' }}">{{ $service['status'] ?? 'unknown' }}</span>
                    <span>{{ $service['url'] ?? (!empty($service['required_runtime_secrets_present']) ? 'configured' : '') }}</span>
                </div>
            @endforeach
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
