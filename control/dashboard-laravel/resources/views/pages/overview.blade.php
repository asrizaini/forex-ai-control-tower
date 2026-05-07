@extends('layouts.control', ['title' => 'Overview / Home', 'description' => 'System summary, API health, worker state, data ingestion, recent alerts, and recent errors.'])

@section('content')
@php
    $pairBuckets = $pairSummaries['summary'] ?? [];
    $demoAccount = collect($accounts ?? [])->firstWhere('account_id', 'demo_main') ?? collect($accounts ?? [])->first();
    $latestAccount = collect($accountSnapshots ?? [])->first();
    $orchestrator = $runtimeStatus['orchestrator'] ?? ['status' => 'down'];
@endphp
<section class="workflow-strip">
    <article class="step-card">
        <span class="step-number">Step 1</span>
        <div class="step-title">Configure Pairs</div>
        <p>Enable symbols and set timeframe/strategy assignment before analysis runs.</p>
        <div class="step-actions">
            <a class="button secondary small" href="{{ route('dashboard.trading-pairs') }}">Open Trading Pairs</a>
        </div>
    </article>
    <article class="step-card">
        <span class="step-number">Step 2</span>
        <div class="step-title">Run Analysis</div>
        <p>Generate fresh technical/fundamental/candle/trend output for every enabled pair.</p>
        <div class="step-actions">
            <form method="POST" action="{{ route('analysis.run') }}">@csrf<button class="small" type="submit">Run Analysis Now</button></form>
            <a class="button secondary small" href="{{ route('dashboard.signals') }}">View Signals</a>
        </div>
    </article>
    <article class="step-card">
        <span class="step-number">Step 3</span>
        <div class="step-title">Demo Auto Trade</div>
        <p>Switch between monitor-only and demo_auto from Risk Validation without bypassing guard rails.</p>
        <div class="step-actions">
            <a class="button secondary small" href="{{ route('dashboard.risk-validation') }}">Open Risk Validation</a>
            @if($demoAccount)
                <span class="badge {{ ($demoAccount['trading_mode'] ?? 'monitor_only') === 'demo_auto' ? 'warn' : 'ok' }}">
                    {{ strtoupper($demoAccount['trading_mode'] ?? 'monitor_only') }}
                </span>
            @endif
        </div>
    </article>
    <article class="step-card">
        <span class="step-number">Step 4</span>
        <div class="step-title">Monitor Runtime</div>
        <p>Track worker health, latest account snapshot, pair freshness, and signal quality.</p>
        <div class="step-actions">
            <a class="button secondary small" href="{{ route('dashboard.workers') }}">Workers</a>
            <a class="button secondary small" href="{{ route('dashboard.monitoring') }}">Monitoring</a>
        </div>
    </article>
</section>

<section class="grid-4" data-live-section="overview-health-cards">
    <div class="metric {{ ($apiStatus['status'] ?? '') === 'ok' ? 'status-ok' : 'status-warn' }}"><span class="eyebrow">API</span><strong>{{ $apiStatus['status'] ?? 'unknown' }}</strong><span>{{ $links['api'] }}</span></div>
    <div class="metric {{ ($healthStatus['services']['database']['status'] ?? '') === 'ok' ? 'status-ok' : 'status-bad' }}"><span class="eyebrow">Database</span><strong>{{ $healthStatus['services']['database']['status'] ?? 'unknown' }}</strong><span>Control plane persistence</span></div>
    <div class="metric {{ ($healthStatus['services']['grafana']['status'] ?? '') === 'ok' ? 'status-ok' : 'status-warn' }}"><span class="eyebrow">Grafana</span><strong>{{ $healthStatus['services']['grafana']['status'] ?? 'unknown' }}</strong><span>Monitoring UI</span></div>
    <div class="metric {{ ($orchestrator['status'] ?? 'down') === 'running' ? 'status-ok' : 'status-warn' }}"><span class="eyebrow">Orchestrator</span><strong>{{ strtoupper($orchestrator['status'] ?? 'down') }}</strong><span>{{ $orchestrator['reason'] ?? 'no reason reported' }}</span></div>
</section>
<section class="panel" data-live-section="overview-orchestrator-status">
    <div class="panel-head"><div><h2>Orchestrator Health</h2><p>Shows coordination runtime state and latest success/failure checkpoints.</p></div><a href="{{ route('dashboard.orchestrator-console') }}">Open Console</a></div>
    <div class="row cols-4">
        <strong>Last success</strong>
        <span data-utc="{{ $orchestrator['last_success_run'] ?? '' }}">{{ $orchestrator['last_success_run'] ?? 'none' }}</span>
        <strong>Last failure</strong>
        <span data-utc="{{ $orchestrator['last_failed_run'] ?? '' }}">{{ $orchestrator['last_failed_run'] ?? 'none' }}</span>
    </div>
    <div class="row cols-3">
        <strong>Failure reason</strong>
        <span>{{ $orchestrator['last_failed_reason'] ?? 'none' }}</span>
        <span class="badge {{ ($orchestrator['retry_status'] ?? 'stable') === 'stable' ? 'ok' : 'warn' }}">{{ $orchestrator['retry_status'] ?? 'stable' }}</span>
    </div>
</section>
<section class="grid-4" data-live-section="overview-pair-cards">
    <div class="metric status-ok"><span class="eyebrow">Enabled Pairs</span><strong>{{ count($pairSummaries['items'] ?? []) }}</strong><span><a href="{{ route('dashboard.trading-pairs') }}">Manage pairs</a></span></div>
    <div class="metric {{ (count($pairBuckets['bullish'] ?? []) + count($pairBuckets['bearish'] ?? [])) > 0 ? 'status-ok' : 'status-warn' }}"><span class="eyebrow">Bullish / Bearish</span><strong>{{ count($pairBuckets['bullish'] ?? []) }} / {{ count($pairBuckets['bearish'] ?? []) }}</strong><span>{{ implode(', ', array_merge($pairBuckets['bullish'] ?? [], $pairBuckets['bearish'] ?? [])) ?: 'none' }}</span></div>
    <div class="metric {{ count($pairBuckets['stale'] ?? []) > 0 ? 'status-warn' : 'status-ok' }}"><span class="eyebrow">Stale Pairs</span><strong>{{ count($pairBuckets['stale'] ?? []) }}</strong><span>{{ implode(', ', $pairBuckets['stale'] ?? []) ?: 'none' }}</span></div>
    <div class="metric {{ count($pairBuckets['blocked'] ?? []) > 0 ? 'status-warn' : 'status-ok' }}"><span class="eyebrow">Blocked Signals</span><strong>{{ count($pairBuckets['blocked'] ?? []) }}</strong><span>{{ implode(', ', $pairBuckets['blocked'] ?? []) ?: 'none' }}</span></div>
</section>
<section class="grid-3" data-live-section="overview-account-cards">
    <article class="metric">
        <span class="eyebrow">Demo Account</span>
        <strong>{{ $latestAccount['login_masked'] ?? ($demoAccount['account_id'] ?? 'not-configured') }}</strong>
        <span>{{ $latestAccount['server'] ?? ($demoAccount['display_name'] ?? 'No snapshot yet') }}</span>
    </article>
    <article class="metric">
        <span class="eyebrow">Equity / Positions</span>
        <strong>{{ isset($latestAccount['equity']) ? number_format((float)$latestAccount['equity'], 2) : 'n/a' }}</strong>
        <span>{{ $latestAccount['positions_count'] ?? 0 }} open positions</span>
    </article>
    <article class="metric">
        <span class="eyebrow">Risk Mode</span>
        <strong>{{ strtoupper($latestAccount['risk_mode'] ?? ($demoAccount['trading_mode'] ?? 'monitor_only')) }}</strong>
        <span>{{ !empty($latestAccount['auto_execution_enabled']) ? 'auto execution enabled' : 'auto execution disabled' }}</span>
    </article>
</section>
<section class="panel" data-live-section="overview-pair-snapshot">
    <div class="panel-head"><div><h2>Pair Snapshot</h2><p>Latest multi-pair analysis summary.</p></div><a href="{{ route('dashboard.pair-summary') }}">Open details</a></div>
    <div class="table-wrap"><div class="table">
        @forelse(array_slice($pairSummaries['items'] ?? [], 0, 8) as $item)
            <div class="row" style="grid-template-columns:.7fr .6fr .8fr .8fr .8fr 1.6fr">
                <strong>{{ $item['symbol'] }}</strong><span>{{ $item['timeframe'] }}</span><span>{{ $item['current_bias'] }}</span><span>{{ $item['trend_status'] }}</span><span>{{ $item['signal_status'] }}</span><span>{{ $item['candle_summary'] }}</span>
            </div>
        @empty
            <p class="empty">No enabled pair analysis yet.</p>
        @endforelse
    </div></div>
</section>
<section class="grid-2" data-live-section="overview-worker-ingestion">
    <article class="panel">
        <div class="panel-head"><div><h2>Worker Status</h2><p>Registered workers and current runtime state.</p></div><a href="{{ route('dashboard.workers') }}">Manage</a></div>
        <div class="table-wrap"><div class="table">
            @forelse(($workers['workers'] ?? []) as $worker)
                <div class="row cols-4"><strong>{{ $worker['name'] }}</strong><span>{{ $worker['worker_type'] }}</span><span class="badge {{ in_array($worker['status'], ['running','ready','standby']) ? 'ok' : 'warn' }}">{{ $worker['status'] }}</span><span data-utc="{{ $worker['last_run_at'] ?? '' }}">{{ $worker['last_run_at'] ?? 'never' }}</span></div>
            @empty
                <p class="empty">No workers registered.</p>
            @endforelse
        </div></div>
    </article>
    <article class="panel">
        <div class="panel-head"><div><h2>Ingestion Status</h2><p>News and calendar readiness at a glance.</p></div><a href="{{ route('dashboard.data-sources') }}">Sources</a></div>
        <div class="row cols-3"><strong>News</strong><span>{{ $newsStatus['risk_status'] ?? 'unknown' }}</span><span class="badge {{ empty($newsStatus['news_halt_active']) ? 'ok' : 'warn' }}">{{ empty($newsStatus['news_halt_active']) ? 'clear' : 'halt' }}</span></div>
        <div class="row cols-3"><strong>Calendar last success</strong><span data-utc="{{ $calendarStatus['last_success_at'] ?? '' }}">{{ $calendarStatus['last_success_at'] ?? 'none' }}</span><span></span></div>
        <div class="row cols-3"><strong>Calendar last failure</strong><span data-utc="{{ $calendarStatus['last_failure_at'] ?? '' }}">{{ $calendarStatus['last_failure_at'] ?? 'none' }}</span><span></span></div>
    </article>
</section>
<section class="grid-2" data-live-section="overview-audit-gates">
    <article class="panel">
        <div class="panel-head"><div><h2>Recent Alerts / Audit</h2><p>Safe audit summaries only. Secret values are never logged.</p></div><a href="{{ route('dashboard.logs') }}">Open logs</a></div>
        @forelse(($auditLogs['items'] ?? []) as $log)
            <div class="row cols-4"><strong>{{ $log['action'] }}</strong><span>{{ $log['resource_type'] }}</span><span>{{ $log['resource_id'] }}</span><span data-utc="{{ $log['created_at'] ?? '' }}">{{ $log['created_at'] }}</span></div>
        @empty
            <p class="empty">No recent audit entries.</p>
        @endforelse
    </article>
    <article class="panel">
        <div class="panel-head"><div><h2>Production Gates</h2><p>Live trading remains blocked unless every gate passes.</p></div><span class="badge {{ !empty($readiness['live_trading_allowed']) ? 'ok' : 'warn' }}">{{ !empty($readiness['live_trading_allowed']) ? 'ready' : 'blocked' }}</span></div>
        @foreach(($readiness['gates'] ?? []) as $gate => $passed)
            <div class="row cols-3"><strong>{{ str_replace('_', ' ', $gate) }}</strong><span></span><span class="badge {{ $passed ? 'ok' : 'warn' }}">{{ $passed ? 'passed' : 'pending' }}</span></div>
        @endforeach
    </article>
</section>
<section class="panel" data-live-section="overview-signals">
    <div class="panel-head"><div><h2>Recent Signal Output</h2><p>Latest generated records to verify pair coverage and freshness.</p></div><a href="{{ route('dashboard.signals') }}">Open Signals</a></div>
    <div class="table-wrap"><div class="table">
        @forelse(($signalRecords['items'] ?? []) as $signal)
            <div class="row" style="grid-template-columns:.7fr .45fr .6fr .6fr .8fr 1.6fr">
                <strong>{{ $signal['pair'] ?? '-' }}</strong>
                <span>{{ $signal['timeframe'] ?? '-' }}</span>
                <span class="badge {{ in_array(($signal['direction'] ?? ''), ['buy','sell']) ? 'ok' : 'warn' }}">{{ $signal['direction'] ?? '-' }}</span>
                <span>{{ $signal['confidence'] ?? 0 }}%</span>
                <span>{{ $signal['freshness_status'] ?? '-' }}</span>
                <span>{{ $signal['reason'] ?? '-' }}</span>
            </div>
        @empty
            <p class="empty">No signal records yet. Run analysis from Step 2 above.</p>
        @endforelse
    </div></div>
</section>
@endsection
