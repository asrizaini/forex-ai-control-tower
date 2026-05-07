@extends('layouts.control', ['title' => 'Risk Validation', 'description' => 'Clear demo trading control with live status, activity feed, and MT5 execution confirmation.'])

@section('content')
<style>
    .risk-feed {max-height: 360px; overflow: auto; display: grid; gap: 8px}
    .risk-feed-item {background: #0d1829; border: 1px solid #234059; border-radius: 10px; display: grid; gap: 4px; padding: 10px 12px}
    .risk-feed-item.error {border-color: #663345}
    .risk-feed-item.warn {border-color: #6b5326}
    .risk-feed-meta {color: #7f98b4; display: flex; flex-wrap: wrap; font-size: 12px; gap: 10px}
    .risk-helper {color: #9cb2ca; font-size: 13px; line-height: 1.45}
    .step-grid {display: grid; gap: 10px; grid-template-columns: repeat(3, minmax(0, 1fr))}
    @media(max-width: 1180px){.step-grid{grid-template-columns:1fr}}
    .flash-msg {padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 14px}
    .flash-msg.ok {background: #0d2818; border: 1px solid #1a5c2e; color: #4ade80}
    .flash-msg.err {background: #2a0f1a; border: 1px solid #6b2d42; color: #f87171}
</style>
@if(session('status'))
    <div class="flash-msg ok">{{ session('status') }}</div>
@endif
@if(session('error'))
    <div class="flash-msg err">{{ session('error') }}</div>
@endif
@php
    $demoAccount = collect($accounts ?? [])->firstWhere('account_id', 'demo_main') ?? collect($accounts ?? [])->first();
    $latestAccount = collect($accountSnapshots ?? [])->first();
    $status = is_array($demoStatus ?? null) ? $demoStatus : [];
    $activity = collect(($demoActivity['items'] ?? []));
    $fmtKl = function ($value) {
        if (!$value) {
            return 'unknown';
        }
        try {
            return \Carbon\Carbon::parse((string) $value)->setTimezone('Asia/Kuala_Lumpur')->format('Y-m-d h:i:s A') . ' GMT+8';
        } catch (\Throwable $e) {
            return (string) $value;
        }
    };
    $cycleRaw = (string)($status['cycle_status'] ?? 'idle');
    $cycleLabelMap = [
        'idle' => 'Idle',
        'analyzing' => 'Analyzing',
        'waiting_for_signal' => 'Waiting For Signal',
        'executing_trade' => 'Executing Trade',
        'monitoring_trade' => 'Monitoring Trade',
        'stopped' => 'Stopped',
        'error' => 'Error',
    ];
    $cycleStatus = $cycleLabelMap[$cycleRaw] ?? ucfirst(str_replace('_', ' ', $cycleRaw));
    $autoStatus = strtoupper((string)($status['auto_trade_status'] ?? 'stopped'));
    $mt5Connected = (bool)($status['mt5_connected'] ?? false);
    $accountType = strtoupper((string)($status['account_type'] ?? 'unknown'));
    $executionReady = (bool)($status['execution_confirmation']['dashboard_can_place_demo_orders'] ?? false);
    $llmUsage = is_array($status['llm_usage'] ?? null) ? $status['llm_usage'] : [];
@endphp

<section class="grid-4" data-live-section="risk-top-status">
    <article class="metric {{ ($status['mode'] ?? 'disabled') === 'demo' ? 'status-ok' : 'status-bad' }}">
        <span class="eyebrow">Trading Mode</span>
        <strong>{{ strtoupper((string)($status['mode'] ?? 'disabled')) }}</strong>
        <span>{{ strtoupper((string)($status['auto_trade_status'] ?? 'stopped')) }}</span>
    </article>
    <article class="metric {{ $mt5Connected ? 'status-ok' : 'status-bad' }}">
        <span class="eyebrow">MT5 Connection</span>
        <strong>{{ $mt5Connected ? 'Connected' : 'Disconnected' }}</strong>
        <span>
            Account type: {{ $accountType }} ·
            Equity: {{ isset($status['account_snapshot']['equity']) ? number_format((float)$status['account_snapshot']['equity'], 2) : 'n/a' }}
        </span>
    </article>
    <article class="metric {{ $executionReady ? 'status-ok' : 'status-warn' }}">
        <span class="eyebrow">Current Cycle</span>
        <strong>{{ $cycleStatus }}</strong>
        <span>{{ strtoupper((string)($status['active_pair'] ?? '-')) }} {{ strtoupper((string)($status['active_timeframe'] ?? '-')) }}</span>
    </article>
    <article class="metric status-warn">
        <span class="eyebrow">Last Action</span>
        <strong style="font-size:18px">{{ $status['last_action'] ?? 'No action yet' }}</strong>
        <span>{{ $status['last_update_local'] ?? $fmtKl(now()) }}</span>
    </article>
</section>

<section class="panel" data-live-section="risk-controls">
    <div class="panel-head">
        <div>
            <h2>Demo Trading Controls</h2>
            <p>Use these controls to run demo automation safely. Real trading remains off unless explicitly enabled elsewhere.</p>
        </div>
        <span class="badge {{ ($status['guard_enabled'] ?? false) ? 'warn' : 'ok' }}">
            {{ ($status['guard_enabled'] ?? false) ? 'Guard Enabled' : 'Guard Disabled (Demo)' }}
        </span>
    </div>
    <p class="risk-helper">{{ $status['guard_note'] ?? 'Guard mode status unavailable.' }}</p>
    <div class="actions" style="margin-top:10px">
        @if($demoAccount)
            <form method="POST" action="{{ route('demo-trading.mode') }}">
                @csrf
                <input type="hidden" name="account_id" value="{{ $demoAccount['account_id'] }}">
                <input type="hidden" name="trading_mode" value="demo_auto">
                <button type="submit">Start Demo Auto Trade</button>
            </form>
            <form method="POST" action="{{ route('demo-trading.mode') }}">
                @csrf
                <input type="hidden" name="account_id" value="{{ $demoAccount['account_id'] }}">
                <input type="hidden" name="trading_mode" value="monitor_only">
                <button class="secondary" type="submit">Stop Demo Auto Trade</button>
            </form>
            <form method="POST" action="{{ route('demo-trading.run-cycle') }}">
                @csrf
                <button class="secondary" type="submit">Run Demo Execution Cycle</button>
            </form>
        @else
            <form method="POST" action="{{ route('demo-trading.mode') }}">
                @csrf
                <input type="hidden" name="account_id" value="demo_main">
                <input type="hidden" name="trading_mode" value="demo_auto">
                <button type="submit">Start Demo Auto Trade</button>
            </form>
            <form method="POST" action="{{ route('demo-trading.mode') }}">
                @csrf
                <input type="hidden" name="account_id" value="demo_main">
                <input type="hidden" name="trading_mode" value="monitor_only">
                <button class="secondary" type="submit">Stop Demo Auto Trade</button>
            </form>
            <form method="POST" action="{{ route('demo-trading.run-cycle') }}">
                @csrf
                <button class="secondary" type="submit">Run Demo Execution Cycle</button>
            </form>
        @endif
    </div>
    <div class="table-wrap" style="margin-top:12px">
        <div class="table">
            <div class="row cols-2">
                <strong>Start Demo Auto Trade</strong>
                <span class="risk-helper">Starts automated demo trading. The system analyzes enabled pairs/timeframes and may place demo orders on MT5 demo account only.</span>
            </div>
            <div class="row cols-2">
                <strong>Stop Demo Auto Trade</strong>
                <span class="risk-helper">Stops new automated demo entries. Existing open demo positions remain untouched unless managed by strategy exit logic.</span>
            </div>
            <div class="row cols-2">
                <strong>Demo Execution Cycle</strong>
                <span class="risk-helper">One cycle: load enabled pairs, refresh analysis/signals, run risk checks, send valid demo orders, then write status and logs.</span>
            </div>
        </div>
    </div>
</section>

<section class="panel" data-live-section="risk-next-steps">
    <div class="panel-head"><div><h2>What Should I Do Next?</h2><p>Follow this guided flow to start and verify demo trading quickly.</p></div></div>
    <div class="step-grid">
        <article class="step-card"><span class="step-number">Step 1</span><span class="step-title">Connect MT5 Demo</span><p>Ensure MT5 bridge is connected and account type is demo.</p></article>
        <article class="step-card"><span class="step-number">Step 2</span><span class="step-title">Enable Pairs/Timeframes</span><p>Go to Trading Pairs and enable symbols/timeframes you want to process.</p></article>
        <article class="step-card"><span class="step-number">Step 3</span><span class="step-title">Start Demo Auto</span><p>Start demo auto trade, then monitor cycle state and feed updates below.</p></article>
    </div>
</section>

<section class="grid-2" data-live-section="risk-confirmation-and-usage">
    <article class="panel">
        <div class="panel-head"><div><h2>MT5 Demo Execution Confirmation</h2><p>This confirms if the dashboard can place demo orders right now.</p></div></div>
        <div class="table-wrap"><div class="table">
            <div class="row cols-3">
                <strong>MT5 bridge connected</strong>
                <span class="badge {{ $mt5Connected ? 'ok' : 'bad' }}">{{ $mt5Connected ? 'YES' : 'NO' }}</span>
                <span>{{ $mt5Connected ? 'Bridge and terminal reachable.' : 'Bridge/terminal not reachable.' }}</span>
            </div>
            <div class="row cols-3">
                <strong>Account type</strong>
                <span class="badge {{ $accountType === 'DEMO' ? 'ok' : 'warn' }}">{{ $accountType }}</span>
                <span>{{ $accountType === 'DEMO' ? 'Confirmed demo account.' : 'Cannot confirm demo account type.' }}</span>
            </div>
            <div class="row cols-3">
                <strong>Dashboard can place demo orders</strong>
                <span class="badge {{ $executionReady ? 'ok' : 'warn' }}">{{ $executionReady ? 'READY' : 'NOT READY' }}</span>
                <span>{{ $executionReady ? 'Demo order route is available.' : 'Mode/bridge/account gate is preventing execution.' }}</span>
            </div>
            <div class="row cols-3">
                <strong>Open positions</strong>
                <span>{{ $status['execution_confirmation']['open_positions_count'] ?? ($latestAccount['positions_count'] ?? 0) }}</span>
                <span>Current demo open positions detected by bridge.</span>
            </div>
            <div class="row cols-3">
                <strong>Last order attempt</strong>
                <span>{{ strtoupper((string)($status['execution_confirmation']['last_order_attempt']['status'] ?? 'none')) }}</span>
                <span>{{ $status['execution_confirmation']['last_order_attempt']['reason'] ?? 'No attempt yet.' }}</span>
            </div>
        </div></div>
    </article>
    <article class="panel">
        <div class="panel-head"><div><h2>AI/Token Usage</h2><p>To reduce cost, this flow prefers rules + cached outputs and avoids unnecessary LLM calls.</p></div></div>
        <div class="table-wrap"><div class="table">
            <div class="row cols-3">
                <strong>Today LLM requests</strong>
                <span>{{ $llmUsage['today_requests'] ?? 0 }}</span>
                <span>Requests to paid/local LLM providers today.</span>
            </div>
            <div class="row cols-3">
                <strong>Today estimated cost (USD)</strong>
                <span>{{ number_format((float)($llmUsage['today_estimated_cost'] ?? 0), 4) }}</span>
                <span>Budget visibility for control decisions.</span>
            </div>
            <div class="row cols-3">
                <strong>Last provider</strong>
                <span>{{ strtoupper((string)($llmUsage['last_provider'] ?? 'none')) }}</span>
                <span>{{ $llmUsage['last_task_type'] ?? 'No AI task logged yet.' }}</span>
            </div>
            <div class="row cols-2">
                <strong>Optimization policy</strong>
                <span class="risk-helper">{{ $llmUsage['optimization_note'] ?? 'No optimization note available.' }}</span>
            </div>
        </div></div>
    </article>
</section>

<section class="panel" data-live-section="risk-activity-feed">
    <div class="panel-head"><div><h2>Live Progress Feed</h2><p>Step-by-step activity so you can see whether the system is idle, analyzing, waiting, executing, monitoring, or stopped.</p></div></div>
    <div class="risk-feed">
        @forelse($activity as $item)
            @php $level = in_array(($item['status'] ?? 'info'), ['ok','warn','error'], true) ? $item['status'] : 'info'; @endphp
            <article class="risk-feed-item {{ $level }}">
                <div class="risk-feed-meta">
                    <strong>{{ strtoupper((string)($item['step'] ?? 'update')) }}</strong>
                    <span>{{ $item['timestamp'] ?? $fmtKl(now()) }}</span>
                </div>
                <p style="color:#e6eef9">{{ $item['message'] ?? 'No message' }}</p>
            </article>
        @empty
            <p class="empty">No activity events yet. Start demo auto mode or run one cycle to populate progress feed.</p>
        @endforelse
    </div>
</section>

<section class="panel" data-live-section="risk-execution-journal">
    <div class="panel-head"><div><h2>Demo Execution Journal</h2><p>Execution attempts and outcomes for all pairs/timeframes.</p></div></div>
    <div class="table-wrap"><div class="table">
        @forelse(($executions['items'] ?? []) as $row)
            <div class="row" style="grid-template-columns:.75fr .45fr .6fr .5fr .7fr 1.6fr .95fr">
                <strong>{{ $row['symbol'] ?? '-' }}</strong>
                <span>{{ $row['timeframe'] ?? '-' }}</span>
                <span class="badge {{ ($row['status'] ?? '') === 'sent' ? 'ok' : (($row['status'] ?? '') === 'blocked' ? 'bad' : 'warn') }}">{{ $row['status'] ?? 'unknown' }}</span>
                <span>{{ strtoupper($row['direction'] ?? '-') }}</span>
                <span>{{ $row['volume'] ?? '-' }}</span>
                <span>{{ $row['reason'] ?? '-' }}</span>
                <span>{{ $fmtKl($row['created_at'] ?? null) }}</span>
            </div>
        @empty
            <p class="empty">No execution records yet.</p>
        @endforelse
    </div></div>
</section>
@endsection
