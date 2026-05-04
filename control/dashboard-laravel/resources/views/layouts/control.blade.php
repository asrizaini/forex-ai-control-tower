<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ $title ?? 'Forex AI Control Tower' }}</title>
    <style>
        :root { --bg:#0b1118; --surface:#111a24; --soft:#0f1720; --ink:#e8eef6; --muted:#8fa3ba; --line:#243244; --nav:#0d141d; --nav2:#172232; --accent:#14a58f; --ok:#58d6a7; --warn:#ffd166; --bad:#ff6b7a; --okbg:#123529; --warnbg:#352b12; --badbg:#3b1720; }
        *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif} a{color:var(--accent);font-weight:750;text-decoration:none} h1,h2,h3,p{margin:0;letter-spacing:0} h1{font-size:28px} h2{font-size:18px} h3{font-size:14px} p{color:var(--muted);line-height:1.45} input,select,textarea,button{font:inherit} input,select,textarea{background:#0d1520;border:1px solid #2a3b51;border-radius:6px;color:#e8eef6;padding:10px 11px;width:100%} textarea{min-height:92px} input:focus,select:focus,textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(20,165,143,.16);outline:none} label{color:#b8c7d9;display:grid;font-size:12px;font-weight:780;gap:6px}
        .shell{display:grid;grid-template-columns:278px minmax(0,1fr);min-height:100vh}.sidebar{background:var(--nav);color:#fff;display:flex;flex-direction:column;gap:18px;padding:20px 15px}.brand{align-items:center;display:flex;gap:12px}.brand-mark{align-items:center;background:var(--accent);border-radius:8px;display:flex;font-weight:860;height:42px;justify-content:center;width:42px}.brand span{color:#aebbd0;display:block;font-size:13px}.nav{display:grid;gap:4px}.nav a{border:1px solid transparent;border-radius:6px;color:#cbd5e1;padding:10px 12px}.nav a.active,.nav a:hover{background:var(--nav2);border-color:#344256;color:#fff}.side-status{border-top:1px solid #2b374a;display:grid;gap:8px;margin-top:auto;padding-top:16px}
        .workspace{display:grid;gap:18px;padding:22px}.topbar,.panel,.metric{background:var(--surface);border:1px solid var(--line);border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,.18)}.topbar{align-items:center;display:flex;gap:16px;justify-content:space-between;padding:18px 20px}.actions{align-items:center;display:flex;flex-wrap:wrap;gap:9px}.button,button{align-items:center;background:var(--accent);border:1px solid var(--accent);border-radius:6px;color:#06110f;cursor:pointer;display:inline-flex;font-weight:790;justify-content:center;min-height:38px;padding:8px 12px;white-space:nowrap}.button.secondary,button.secondary{background:#142033;border-color:#31445d;color:#dbe8f5}.button.danger,button.danger{background:#24131a;border-color:#62303c;color:var(--bad)}.button.small,button.small{font-size:12px;min-height:32px;padding:6px 9px}
        .badge{border-radius:6px;display:inline-flex;font-size:12px;font-weight:820;padding:5px 8px;text-transform:uppercase;width:fit-content}.ok{background:var(--okbg);color:var(--ok)}.warn{background:var(--warnbg);color:var(--warn)}.bad{background:var(--badbg);color:var(--bad)}.muted{color:var(--muted)}.eyebrow{color:#69778a;font-size:12px;font-weight:790;text-transform:uppercase}.notice{border-radius:8px;padding:12px 14px}.notice.ok{background:var(--okbg);color:var(--ok)}.notice.bad{background:var(--badbg);color:var(--bad)}
        .grid-2{display:grid;gap:14px;grid-template-columns:repeat(2,minmax(0,1fr))}.grid-3{display:grid;gap:14px;grid-template-columns:repeat(3,minmax(0,1fr))}.grid-4{display:grid;gap:14px;grid-template-columns:repeat(4,minmax(0,1fr))}.panel{padding:18px}.panel-head{align-items:flex-start;display:flex;gap:12px;justify-content:space-between;margin-bottom:16px}.metric{display:grid;gap:5px;min-height:108px;padding:16px}.metric strong{font-size:26px}.table{display:grid;gap:0}.row{align-items:center;border-bottom:1px solid #233244;display:grid;gap:10px;padding:10px 0}.row.cols-2{grid-template-columns:1fr 1fr}.row.cols-3{grid-template-columns:1fr 1fr auto}.row.cols-4{grid-template-columns:1fr 1fr 1fr auto}.row.cols-5{grid-template-columns:1.2fr .8fr .8fr .8fr auto}.form-grid{display:grid;gap:10px;grid-template-columns:repeat(3,minmax(0,1fr)) auto}.stack{display:grid;gap:12px}.empty{color:var(--muted);padding:18px 0}.masked{background:var(--soft);border:1px solid #29394d;border-radius:6px;overflow-wrap:anywhere;padding:10px 11px}.login-form{display:grid;gap:10px;grid-template-columns:minmax(140px,1fr) minmax(180px,1fr) minmax(150px,.8fr) auto}.login-only{grid-template-columns:1fr}.login-only .workspace{align-content:center;justify-self:center;max-width:860px;width:100%}.login-only .sidebar,.login-only .topbar{display:none}.section-tabs{display:flex;flex-wrap:wrap;gap:8px}.section-tabs a{background:#142033;border:1px solid #2d4058;border-radius:6px;color:#cbd8e6;padding:8px 10px}.section-tabs a.active{background:#17483f;color:#dffcf6}
        @media(max-width:1180px){.grid-4{grid-template-columns:repeat(2,minmax(0,1fr))}.grid-3,.grid-2,.form-grid{grid-template-columns:1fr}.row,.row.cols-2,.row.cols-3,.row.cols-4,.row.cols-5{grid-template-columns:1fr}}@media(max-width:820px){.shell{grid-template-columns:1fr}.workspace{padding:14px}.topbar,.panel-head{align-items:stretch;flex-direction:column}.login-form{grid-template-columns:1fr}}
    </style>
</head>
<body>
@php
    $nav = [
        ['overview','Overview','dashboard.overview'], ['trading-pairs','Trading Pairs','dashboard.trading-pairs'], ['pair-summary','Pair Summary','dashboard.pair-summary'], ['signals','Signals','dashboard.signals'], ['strategy','Strategy','dashboard.strategy'],
        ['technical','Technical Analysis','dashboard.technical'], ['fundamental','Fundamental Analysis','dashboard.fundamental'], ['candle-analysis','Candle Analysis','dashboard.candle-analysis'], ['trend-analysis','Trend Analysis','dashboard.trend-analysis'], ['risk-validation','Risk Validation','dashboard.risk-validation'], ['testing','Testing / Backtesting','dashboard.testing'],
        ['credentials','Credentials','dashboard.credentials'], ['data-sources','Data Sources','dashboard.data-sources'],
        ['calendar','Economic Calendar','dashboard.calendar'], ['news','News','dashboard.news'], ['alert-rules','Alert Rules','dashboard.alert-rules'],
        ['workers','Workers / Agents','dashboard.workers'], ['agent-theater','Agent Theater','dashboard.agent-theater'], ['orchestrator-console','Orchestrator Console','dashboard.orchestrator-console'],
        ['monitoring','Grafana / Monitoring','dashboard.monitoring'], ['api-status','API Status','dashboard.api-status'], ['logs','Logs & Audit','dashboard.logs'], ['settings','Settings','dashboard.settings'],
    ];
@endphp
<main class="shell {{ ($active ?? '') === 'login' ? 'login-only' : '' }}">
    <aside class="sidebar">
        <div class="brand"><div class="brand-mark">FX</div><div><strong>Forex AI</strong><span>fx-control dashboard</span></div></div>
        <nav class="nav">
            @foreach($nav as [$key,$label,$route])
                <a class="{{ ($active ?? '') === $key ? 'active' : '' }}" href="{{ route($route) }}">{{ $label }}</a>
            @endforeach
        </nav>
        <div class="side-status">
            <span class="badge ok">demo</span>
            <span class="badge ok">monitor_only</span>
            <span class="badge {{ !empty($authenticated) ? 'ok' : 'warn' }}">{{ !empty($authenticated) ? 'authenticated' : 'login required' }}</span>
        </div>
    </aside>
    <section class="workspace">
        <header class="topbar">
            <div>
                <p class="eyebrow">{{ $eyebrow ?? 'Operations Console' }}</p>
                <h1>{{ $title ?? 'Forex AI Control Tower' }}</h1>
                <p>{{ $description ?? 'Production control dashboard for fx-control services, workers, credentials, and observability.' }}</p>
            </div>
            <div class="actions">
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
</body>
</html>
