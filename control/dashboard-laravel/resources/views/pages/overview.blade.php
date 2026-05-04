@extends('layouts.control', ['title' => 'Overview / Home', 'description' => 'System summary, API health, worker state, data ingestion, recent alerts, and recent errors.'])

@section('content')
<section class="grid-4">
    <div class="metric"><span class="eyebrow">API</span><strong>{{ $apiStatus['status'] ?? 'unknown' }}</strong><span>{{ $links['api'] }}</span></div>
    <div class="metric"><span class="eyebrow">Database</span><strong>{{ $healthStatus['services']['database']['status'] ?? 'unknown' }}</strong><span>Control plane persistence</span></div>
    <div class="metric"><span class="eyebrow">Grafana</span><strong>{{ $healthStatus['services']['grafana']['status'] ?? 'unknown' }}</strong><span>Monitoring UI</span></div>
    <div class="metric"><span class="eyebrow">Calendar</span><strong>{{ $calendarStatus['status'] ?? 'unknown' }}</strong><span>{{ $calendarStatus['events_count'] ?? 0 }} events stored</span></div>
</section>
<section class="grid-2">
    <article class="panel">
        <div class="panel-head"><div><h2>Worker Status</h2><p>Registered workers and current runtime state.</p></div><a href="{{ route('dashboard.workers') }}">Manage</a></div>
        <div class="table">
            @forelse(($workers['workers'] ?? []) as $worker)
                <div class="row cols-4"><strong>{{ $worker['name'] }}</strong><span>{{ $worker['worker_type'] }}</span><span class="badge {{ in_array($worker['status'], ['running','ready','standby']) ? 'ok' : 'warn' }}">{{ $worker['status'] }}</span><span>{{ $worker['last_run_at'] ?? 'never' }}</span></div>
            @empty
                <p class="empty">No workers registered.</p>
            @endforelse
        </div>
    </article>
    <article class="panel">
        <div class="panel-head"><div><h2>Ingestion Status</h2><p>News and calendar readiness at a glance.</p></div><a href="{{ route('dashboard.data-sources') }}">Sources</a></div>
        <div class="row cols-3"><strong>News</strong><span>{{ $newsStatus['risk_status'] ?? 'unknown' }}</span><span class="badge {{ empty($newsStatus['news_halt_active']) ? 'ok' : 'warn' }}">{{ empty($newsStatus['news_halt_active']) ? 'clear' : 'halt' }}</span></div>
        <div class="row cols-3"><strong>Calendar last success</strong><span>{{ $calendarStatus['last_success_at'] ?? 'none' }}</span><span></span></div>
        <div class="row cols-3"><strong>Calendar last failure</strong><span>{{ $calendarStatus['last_failure_at'] ?? 'none' }}</span><span></span></div>
    </article>
</section>
<section class="grid-2">
    <article class="panel">
        <div class="panel-head"><div><h2>Recent Alerts / Audit</h2><p>Safe audit summaries only. Secret values are never logged.</p></div><a href="{{ route('dashboard.logs') }}">Open logs</a></div>
        @forelse(($auditLogs['items'] ?? []) as $log)
            <div class="row cols-4"><strong>{{ $log['action'] }}</strong><span>{{ $log['resource_type'] }}</span><span>{{ $log['resource_id'] }}</span><span>{{ $log['created_at'] }}</span></div>
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
@endsection
