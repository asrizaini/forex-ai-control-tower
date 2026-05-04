<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Forex AI Control Tower</title>
    <style>
        :root {
            color-scheme: light;
            --ink: #0f172a;
            --muted: #475569;
            --line: #d9e2ec;
            --panel: #ffffff;
            --bg: #f5f7fb;
            --ok: #047857;
            --warn: #b45309;
            --block: #b91c1c;
            --accent: #0f766e;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            background: var(--bg);
            color: var(--ink);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        main {
            width: min(1180px, calc(100vw - 32px));
            margin: 32px auto;
        }
        header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 24px;
            margin-bottom: 24px;
        }
        h1 { margin: 0; font-size: 28px; }
        h2 { margin: 0 0 12px; font-size: 16px; }
        a { color: var(--accent); text-decoration: none; font-weight: 700; }
        .sub { margin-top: 8px; color: var(--muted); }
        .grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
        }
        .panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 18px;
        }
        .wide { grid-column: span 2; }
        .status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-weight: 800;
            color: var(--ok);
        }
        .status.blocked { color: var(--block); }
        .pill {
            display: inline-flex;
            margin: 4px 6px 0 0;
            padding: 6px 10px;
            border: 1px solid var(--line);
            border-radius: 999px;
            color: var(--muted);
            background: #fbfdff;
            font-size: 13px;
        }
        .gate {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid #eef2f7;
        }
        .gate:last-child { border-bottom: 0; }
        .pass { color: var(--ok); font-weight: 800; }
        .fail { color: var(--block); font-weight: 800; }
        table { width: 100%; border-collapse: collapse; }
        th, td {
            padding: 10px 8px;
            border-bottom: 1px solid #eef2f7;
            text-align: left;
            font-size: 14px;
        }
        th { color: var(--muted); }
        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        button {
            border: 1px solid var(--line);
            background: #e2e8f0;
            color: #64748b;
            border-radius: 6px;
            padding: 10px 12px;
            font-weight: 800;
            cursor: not-allowed;
        }
        .note { color: var(--muted); font-size: 14px; line-height: 1.55; }
        @media (max-width: 900px) {
            .grid { grid-template-columns: 1fr; }
            .wide { grid-column: span 1; }
            header { display: block; }
        }
    </style>
</head>
<body>
<main>
    <header>
        <div>
            <h1>Forex AI Control Tower</h1>
            <div class="sub">
                {{ $readiness['environment'] ?? 'demo' }} · {{ $readiness['trading_mode'] ?? 'monitor_only' }}
            </div>
        </div>
        <div class="actions">
            <a href="{{ $links['docs'] }}">API Docs</a>
            <a href="{{ $links['grafana'] }}">Grafana</a>
        </div>
    </header>

    <section class="grid">
        <div class="panel">
            <h2>System Health</h2>
            <div class="status">{{ $health['status'] ?? 'unknown' }}</div>
        </div>
        <div class="panel">
            <h2>Trading Mode</h2>
            <div class="status blocked">
                {{ !empty($readiness['live_trading_allowed']) ? 'live enabled' : 'live blocked' }}
            </div>
        </div>
        <div class="panel">
            <h2>Runtime Guard</h2>
            <div class="status">
                {{ !empty($readiness['restricted_live_auto_allowed']) ? 'restricted live ready' : 'approval required' }}
            </div>
        </div>

        <div class="panel wide">
            <h2>Pre-Live Gates</h2>
            @foreach(($readiness['gates'] ?? []) as $gate => $passed)
                <div class="gate">
                    <span>{{ str_replace('_', ' ', $gate) }}</span>
                    <span class="{{ $passed ? 'pass' : 'fail' }}">{{ $passed ? 'PASS' : 'HOLD' }}</span>
                </div>
            @endforeach
        </div>

        <div class="panel">
            <h2>Next Required Actions</h2>
            @forelse(($readiness['next_required_actions'] ?? []) as $action)
                <span class="pill">{{ $action }}</span>
            @empty
                <span class="pill">No blocking gates reported</span>
            @endforelse
            <p class="note">Live controls stay disabled in this Laravel console until the security review and explicit production-live approval are recorded through the FastAPI control plane.</p>
        </div>

        <div class="panel wide">
            <h2>Market Feed</h2>
            <table>
                <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Trend</th>
                    <th>Spread</th>
                    <th>Fresh</th>
                    <th>Candles</th>
                </tr>
                </thead>
                <tbody>
                @forelse($market as $item)
                    <tr>
                        <td>{{ $item['symbol'] ?? '-' }}</td>
                        <td>{{ $item['trend'] ?? '-' }}</td>
                        <td>{{ $item['spread'] ?? '-' }}</td>
                        <td>{{ !empty($item['feed_fresh']) ? 'yes' : 'no' }}</td>
                        <td>{{ $item['rates_count'] ?? 0 }}</td>
                    </tr>
                @empty
                    <tr><td colspan="5">No market snapshots available.</td></tr>
                @endforelse
                </tbody>
            </table>
        </div>

        <div class="panel">
            <h2>Live Actions</h2>
            <button disabled>Record Security Review</button>
            <button disabled>Approve Production Live</button>
            <p class="note">These controls are intentionally disabled in the first Laravel shell. They will become authenticated, audited POST flows after we wire Laravel login to the control-plane JWT flow.</p>
        </div>
    </section>
</main>
</body>
</html>
