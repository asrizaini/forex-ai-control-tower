<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ $title ?? 'Forex AI Control Tower' }}</title>
    <style>
        :root { --bg:#060d16; --bg-soft:#0a1320; --surface:#0f1a2b; --surface-2:#132034; --soft:#0c1726; --ink:#e6eef9; --muted:#8ca3be; --line:#22344b; --line-soft:#1a2b3f; --nav:#0a1422; --nav2:#122035; --accent:#20c9ae; --accent-soft:#183b36; --ok:#5fdeb3; --warn:#ffcf70; --bad:#ff6f86; --okbg:#123728; --warnbg:#3a2d12; --badbg:#3f1522; }
        *{box-sizing:border-box}
        body{margin:0;background:radial-gradient(circle at top right,#0e1b2e 0%,var(--bg) 45%);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
        a{color:var(--accent);font-weight:760;text-decoration:none}
        h1,h2,h3,p{margin:0;letter-spacing:0}
        h1{font-size:30px;line-height:1.2}
        h2{font-size:21px;line-height:1.25}
        h3{font-size:14px}
        p{color:var(--muted);line-height:1.45}
        input,select,textarea,button{font:inherit}
        input,select,textarea{background:#0b1422;border:1px solid #2a3f5b;border-radius:10px;color:#e8eef6;padding:10px 11px;width:100%}
        textarea{min-height:92px}
        input:focus,select:focus,textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(32,201,174,.18);outline:none}
        label{color:#b8c7d9;display:grid;font-size:12px;font-weight:760;gap:6px}
        .shell{display:grid;grid-template-columns:290px minmax(0,1fr);min-height:100vh}
        .sidebar{background:linear-gradient(180deg,#081321 0%,#070f1a 100%);border-right:1px solid var(--line-soft);color:#fff;display:flex;flex-direction:column;gap:18px;height:100vh;overflow:auto;padding:22px 16px;position:sticky;top:0}
        .brand{align-items:center;display:flex;gap:12px;padding:2px 4px 6px}
        .brand-mark{align-items:center;background:linear-gradient(135deg,var(--accent) 0%,#17b096 100%);border-radius:10px;display:flex;font-weight:860;height:42px;justify-content:center;width:42px}
        .brand span{color:#9fb1c7;display:block;font-size:13px}
        .nav-group{display:grid;gap:6px}
        .nav-accordion{border:1px solid #1f3146;border-radius:10px;overflow:hidden}
        .nav-accordion + .nav-accordion{margin-top:8px}
        .nav-accordion summary{align-items:center;background:#0b1829;color:#89a2bf;cursor:pointer;display:flex;font-size:11px;font-weight:800;justify-content:space-between;letter-spacing:.05em;list-style:none;padding:10px 12px;text-transform:uppercase}
        .nav-accordion summary::-webkit-details-marker{display:none}
        .nav-accordion[open] summary{background:#102036;color:#b7c8dc}
        .nav-accordion summary::after{content:'+';font-size:14px;line-height:1}
        .nav-accordion[open] summary::after{content:'-'}
        .nav{display:grid;gap:4px}
        .nav-accordion .nav{padding:8px}
        .nav a{border:1px solid transparent;border-radius:10px;color:#c7d6e8;padding:10px 12px}
        .nav a.active,.nav a:hover{background:var(--nav2);border-color:#2e465f;color:#fff}
        .side-status{border-top:1px solid #233346;display:flex;flex-wrap:wrap;gap:8px;margin-top:auto;padding-top:16px}
        .workspace{display:grid;gap:16px;grid-auto-rows:min-content;margin:0 auto;max-width:1650px;padding:22px 28px;width:100%}
        .topbar,.panel,.metric,.step-card{background:rgba(15,26,43,.86);backdrop-filter:blur(4px);border:1px solid var(--line);border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,.2)}
        .topbar{align-items:flex-start;display:flex;gap:16px;justify-content:space-between;padding:16px 20px}
        .topbar p{margin-top:4px}
        .header-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
        .actions{align-items:center;display:flex;flex-wrap:wrap;gap:9px}
        .refresh-box{align-items:center;display:flex;gap:8px}
        .refresh-box select{min-width:128px;padding:7px 9px}
        .refresh-state{color:var(--muted);font-size:12px}
        .button,button{align-items:center;background:linear-gradient(135deg,#1fd1b5 0%,#19b89f 100%);border:1px solid #26cdb2;border-radius:10px;color:#05110f;cursor:pointer;display:inline-flex;font-weight:800;justify-content:center;min-height:38px;padding:8px 12px;white-space:nowrap}
        .button.secondary,button.secondary{background:#122136;border-color:#2f4763;color:#dbe8f5}
        .button.danger,button.danger{background:#27131b;border-color:#6c3340;color:var(--bad)}
        .button.small,button.small{font-size:12px;min-height:32px;padding:6px 9px}
        .badge{border-radius:999px;display:inline-flex;font-size:11px;font-weight:820;letter-spacing:.02em;padding:5px 9px;text-transform:uppercase;width:fit-content}
        .badge[data-tip]{position:relative}
        .badge[data-tip]:hover::after{background:#0e1f34;border:1px solid #2b425c;border-radius:8px;color:#d8e6f6;content:attr(data-tip);font-size:11px;font-weight:600;left:0;line-height:1.3;max-width:260px;padding:8px 9px;position:absolute;text-transform:none;top:125%;white-space:normal;z-index:40}
        .ok{background:var(--okbg);color:var(--ok)}
        .warn{background:var(--warnbg);color:var(--warn)}
        .bad{background:var(--badbg);color:var(--bad)}
        .muted{color:var(--muted)}
        .eyebrow{color:#6f86a2;font-size:11px;font-weight:790;text-transform:uppercase}
        .notice{border-radius:10px;padding:12px 14px}
        .notice.ok{background:var(--okbg);color:var(--ok)}
        .notice.bad{background:var(--badbg);color:var(--bad)}
        .notice.warn{background:var(--warnbg);color:var(--warn)}
        .grid-2{display:grid;gap:14px;grid-template-columns:repeat(2,minmax(0,1fr))}
        .grid-3{display:grid;gap:14px;grid-template-columns:repeat(3,minmax(0,1fr))}
        .grid-4{display:grid;gap:14px;grid-template-columns:repeat(4,minmax(0,1fr))}
        .panel{padding:18px}
        .panel-head{align-items:flex-start;display:flex;gap:12px;justify-content:space-between;margin-bottom:14px}
        .metric{display:grid;gap:5px;min-height:112px;padding:16px;position:relative;transition:transform .15s ease, border-color .15s ease, box-shadow .15s ease}
        .metric:hover{border-color:#2d4b6a;box-shadow:0 10px 26px rgba(0,0,0,.26);transform:translateY(-1px)}
        .metric.status-ok{border-color:#295744;background:linear-gradient(180deg,rgba(19,58,45,.45) 0%,rgba(15,26,43,.9) 72%)}
        .metric.status-warn{border-color:#685026;background:linear-gradient(180deg,rgba(60,42,17,.45) 0%,rgba(15,26,43,.9) 72%)}
        .metric.status-bad{border-color:#663345;background:linear-gradient(180deg,rgba(62,24,36,.45) 0%,rgba(15,26,43,.9) 72%)}
        .metric strong{font-size:30px;line-height:1.1}
        .table-wrap{overflow:auto}
        .table{display:grid;gap:0;min-width:700px}
        .row{align-items:center;border-bottom:1px solid #21344a;display:grid;gap:10px;padding:11px 0;transition:background-color .12s ease}
        .table .row:hover{background:rgba(20,34,53,.35)}
        .row > *{min-width:0}
        .row.cols-2{grid-template-columns:1fr 1fr}
        .row.cols-3{grid-template-columns:1fr 1fr auto}
        .row.cols-4{grid-template-columns:1fr 1fr 1fr auto}
        .row.cols-5{grid-template-columns:1.2fr .8fr .8fr .8fr auto}
        .form-grid{display:grid;gap:10px;grid-template-columns:repeat(3,minmax(0,1fr)) auto}
        .stack{display:grid;gap:12px}
        .empty{color:var(--muted);padding:18px 0}
        .legend{display:grid;gap:8px;grid-template-columns:repeat(4,minmax(0,1fr));margin-top:8px}
        .legend-item{background:#0d1a2b;border:1px solid #22344b;border-radius:10px;padding:8px 10px}
        .legend-item p{font-size:12px}
        .masked{background:var(--soft);border:1px solid #29394d;border-radius:10px;overflow-wrap:anywhere;padding:10px 11px}
        .login-form{display:grid;gap:10px;grid-template-columns:minmax(140px,1fr) minmax(180px,1fr) minmax(150px,.8fr) auto}
        .login-only{grid-template-columns:1fr}
        .login-only .workspace{align-content:center;justify-self:center;max-width:860px;width:100%}
        .login-only .sidebar,.login-only .topbar{display:none}
        .section-tabs{display:flex;flex-wrap:wrap;gap:8px}
        .section-tabs a{background:#142033;border:1px solid #2d4058;border-radius:8px;color:#cbd8e6;padding:8px 10px}
        .section-tabs a.active{background:#17483f;color:#dffcf6}
        .workflow-strip{display:grid;gap:12px;grid-template-columns:repeat(4,minmax(0,1fr))}
        .step-card{display:grid;gap:8px;padding:14px}
        .step-number{color:#6f86a2;font-size:11px;font-weight:800;letter-spacing:.05em;text-transform:uppercase}
        .step-title{font-size:16px;font-weight:820}
        .step-actions{display:flex;flex-wrap:wrap;gap:8px}
        @media(max-width:1420px){.workflow-strip{grid-template-columns:repeat(2,minmax(0,1fr))}}
        @media(max-width:1180px){.grid-4{grid-template-columns:repeat(2,minmax(0,1fr))}.grid-3,.grid-2,.form-grid,.legend{grid-template-columns:1fr}.row,.row.cols-2,.row.cols-3,.row.cols-4,.row.cols-5{grid-template-columns:1fr}.table{min-width:0}}
        @media(max-width:900px){.shell{grid-template-columns:1fr}.sidebar{height:auto;position:static}.workspace{padding:14px}.topbar,.panel-head{align-items:stretch;flex-direction:column}.login-form{grid-template-columns:1fr}}
    </style>
</head>
<body>
@php
    $navGroups = [
        'Operate' => [
            ['overview','Overview','dashboard.overview'],
            ['trading-pairs','Trading Pairs','dashboard.trading-pairs'],
            ['pair-summary','Pair Summary','dashboard.pair-summary'],
            ['signals','Signals','dashboard.signals'],
            ['risk-validation','Risk Validation','dashboard.risk-validation'],
        ],
        'Analysis' => [
            ['strategy','Strategy','dashboard.strategy'],
            ['technical','Technical Analysis','dashboard.technical'],
            ['fundamental','Fundamental Analysis','dashboard.fundamental'],
            ['candle-analysis','Candle Analysis','dashboard.candle-analysis'],
            ['trend-analysis','Trend Analysis','dashboard.trend-analysis'],
            ['testing','Testing / Backtesting','dashboard.testing'],
        ],
        'Data & Governance' => [
            ['credentials','Credentials','dashboard.credentials'],
            ['data-sources','Data Sources','dashboard.data-sources'],
            ['calendar','Economic Calendar','dashboard.calendar'],
            ['news','News','dashboard.news'],
            ['alert-rules','Alert Rules','dashboard.alert-rules'],
            ['workers','Workers / Agents','dashboard.workers'],
        ],
        'Visibility' => [
            ['agent-theater','Agent Theater','dashboard.agent-theater'],
            ['orchestrator-console','Orchestrator Console','dashboard.orchestrator-console'],
            ['openclaw','OpenClaw Gateway','dashboard.openclaw'],
            ['monitoring','Grafana / Monitoring','dashboard.monitoring'],
            ['api-status','API Status','dashboard.api-status'],
            ['logs','Logs & Audit','dashboard.logs'],
            ['settings','Settings','dashboard.settings'],
        ],
    ];
@endphp
<main class="shell {{ ($active ?? '') === 'login' ? 'login-only' : '' }}">
    <aside class="sidebar">
        <div class="brand"><div class="brand-mark">FX</div><div><strong>Forex AI</strong><span>fx-control dashboard</span></div></div>
        @foreach($navGroups as $groupName => $items)
            @php $groupOpen = collect($items)->contains(fn($item) => ($active ?? '') === $item[0]); @endphp
            <details class="nav-accordion" {{ $groupOpen ? 'open' : '' }}>
                <summary>{{ $groupName }}</summary>
                <nav class="nav">
                    @foreach($items as [$key,$label,$route])
                        <a class="{{ ($active ?? '') === $key ? 'active' : '' }}" href="{{ route($route) }}">{{ $label }}</a>
                    @endforeach
                </nav>
            </details>
        @endforeach
        <div class="side-status">
            <span class="badge ok">{{ strtoupper($runtime['environment'] ?? 'DEMO') }}</span>
            <span class="badge {{ (($runtime['trading_mode'] ?? 'monitor_only') === 'demo_auto') ? 'warn' : 'ok' }}">{{ strtoupper($runtime['trading_mode'] ?? 'monitor_only') }}</span>
            <span class="badge {{ !empty($runtime['live_auto_trading']) ? 'warn' : 'ok' }}">{{ !empty($runtime['live_auto_trading']) ? 'AUTO READY' : 'AUTO OFF' }}</span>
            <span class="badge {{ !empty($authenticated) ? 'ok' : 'warn' }}">{{ !empty($authenticated) ? 'authenticated' : 'login required' }}</span>
        </div>
    </aside>
    <section class="workspace">
        <header class="topbar">
            <div>
                <p class="eyebrow">{{ $eyebrow ?? 'Operations Console' }}</p>
                <h1>{{ $title ?? 'Forex AI Control Tower' }}</h1>
                <p>{{ $description ?? 'Production control dashboard for fx-control services, workers, credentials, and observability.' }}</p>
                <div class="header-meta">
                    <span class="badge ok" data-tip="Execution environment. DEMO means non-live broker account context.">{{ strtoupper($runtime['environment'] ?? 'demo') }}</span>
                    <span class="badge {{ (($runtime['trading_mode'] ?? 'monitor_only') === 'demo_auto') ? 'warn' : 'ok' }}" data-tip="Current account trading mode. monitor_only = observe only. demo_auto = governed auto on demo account only.">{{ strtoupper($runtime['trading_mode'] ?? 'monitor_only') }}</span>
                    <span class="badge {{ !empty($runtime['live_auto_trading']) ? 'warn' : 'ok' }}" data-tip="AUTO READY means auto execution path is enabled in config but still guarded by approvals and Execution Guard token.">{{ !empty($runtime['live_auto_trading']) ? 'AUTO READY' : 'AUTO OFF' }}</span>
                    <span class="badge {{ !empty($authenticated) ? 'ok' : 'warn' }}" data-tip="Authentication status for this dashboard session.">{{ !empty($authenticated) ? 'AUTHENTICATED' : 'LOGIN REQUIRED' }}</span>
                </div>
                <div class="legend">
                    <div class="legend-item"><strong>DEMO</strong><p>System is operating in demo environment, not production-live.</p></div>
                    <div class="legend-item"><strong>DEMO_AUTO</strong><p>Demo account can auto-route signals, still controlled by risk and approvals.</p></div>
                    <div class="legend-item"><strong>AUTO READY</strong><p>Auto path is available, but execution remains blocked without guard + policy pass.</p></div>
                    <div class="legend-item"><strong>AUTHENTICATED</strong><p>Your login token is active for protected pages and actions.</p></div>
                </div>
            </div>
            <div class="actions">
                <div class="refresh-box">
                    <select id="live-refresh-interval">
                        <option value="0">Live Refresh: Off</option>
                        <option value="5">Every 5s</option>
                        <option value="10">Every 10s</option>
                        <option value="15">Every 15s</option>
                        <option value="30">Every 30s</option>
                    </select>
                    <span class="refresh-state" id="live-refresh-state"></span>
                </div>
                <a class="button secondary" href="{{ $links['docs'] }}" target="_blank" rel="noreferrer">API Docs</a>
                <a class="button secondary" href="{{ $links['grafana'] }}" target="_blank" rel="noreferrer">Grafana</a>
                @if($authenticated)
                    <form method="POST" action="{{ route('logout') }}">@csrf<button class="danger" type="submit">Logout</button></form>
                @endif
            </div>
        </header>
        @if(session('status'))<div class="notice ok">{{ session('status') }}</div>@endif
        @if(session('error'))<div class="notice bad">{{ session('error') }}</div>@endif
        @if($errors->any())<div class="notice bad">{{ $errors->first() }}</div>@endif
        @yield('content')
    </section>
</main>
<script>
document.addEventListener('DOMContentLoaded', function () {
    window.fxFormatKualaLumpur = function (raw) {
        if (!raw) return '';
        if (String(raw).includes('GMT+8')) return raw;
        const parsed = new Date(raw);
        if (Number.isNaN(parsed.getTime())) return String(raw);
        return parsed.toLocaleString('en-US', {
            timeZone: 'Asia/Kuala_Lumpur',
            hour12: true,
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        }) + ' GMT+8';
    };
    const applyKualaLumpurTimes = function () {
        document.querySelectorAll('[data-utc]').forEach(function (node) {
            const raw = node.getAttribute('data-utc');
            if (!raw) return;
            node.textContent = window.fxFormatKualaLumpur(raw);
        });
    };
    const groups = Array.from(document.querySelectorAll('.nav-accordion'));
    const activeGroup = groups.find(function (group) {
        return group.querySelector('a.active');
    });
    groups.forEach(function (group) {
        group.open = activeGroup ? group === activeGroup : group.open;
    });
    groups.forEach(function (group) {
        group.addEventListener('toggle', function () {
            if (!group.open) return;
            groups.forEach(function (other) {
                if (other !== group) {
                    other.open = false;
                }
            });
        });
    });
    const refreshSelect = document.getElementById('live-refresh-interval');
    const refreshState = document.getElementById('live-refresh-state');
    if (!refreshSelect || !refreshState) return;
    const STORAGE_KEY = 'fx_live_refresh_seconds';
    let timer = null;
    let refreshingSections = false;
    const refreshMarkedSections = async function () {
        const sections = Array.from(document.querySelectorAll('[data-live-section]'));
        if (!sections.length || refreshingSections) {
            return;
        }
        refreshingSections = true;
        try {
            const response = await fetch(window.location.href, {
                headers: {
                    'Accept': 'text/html',
                    'X-Section-Refresh': '1',
                },
                credentials: 'same-origin',
            });
            if (!response.ok) {
                throw new Error('section refresh failed');
            }
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            sections.forEach(function (section) {
                if (section.contains(document.activeElement)) {
                    return;
                }
                const key = section.getAttribute('data-live-section');
                if (!key) {
                    return;
                }
                const incoming = doc.querySelector(`[data-live-section="${key}"]`);
                if (!incoming) {
                    return;
                }
                section.innerHTML = incoming.innerHTML;
            });
            if (typeof window.fxAfterSectionRefresh === 'function') {
                window.fxAfterSectionRefresh();
            }
            applyKualaLumpurTimes();
            refreshState.textContent = 'Sections updated';
        } catch (_error) {
            refreshState.textContent = 'Refresh failed';
        } finally {
            refreshingSections = false;
        }
    };
    const applyRefresh = function (seconds) {
        if (timer) {
            clearInterval(timer);
            timer = null;
        }
        if (!seconds) {
            refreshState.textContent = 'Static view';
            return;
        }
        refreshState.textContent = 'Auto-updating sections';
        timer = setInterval(function () {
            refreshMarkedSections();
        }, seconds * 1000);
    };
    const persisted = parseInt(localStorage.getItem(STORAGE_KEY) || '0', 10);
    if ([0, 5, 10, 15, 30].includes(persisted)) {
        refreshSelect.value = String(persisted);
        applyRefresh(persisted);
    } else {
        applyRefresh(0);
    }
    refreshSelect.addEventListener('change', function () {
        const seconds = parseInt(refreshSelect.value || '0', 10);
        localStorage.setItem(STORAGE_KEY, String(seconds));
        applyRefresh(seconds);
    });
    applyKualaLumpurTimes();
});
</script>
</body>
</html>
