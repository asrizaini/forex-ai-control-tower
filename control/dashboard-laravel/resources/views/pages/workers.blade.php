@extends('layouts.control', ['title' => 'Workers / Agents', 'description' => 'Monitor and control calendar, news, analysis, signal, risk, notification, and validation workers.'])

@section('content')
@php
    $runtime = $runtimeStatus['orchestrator'] ?? [];
    $agentRuntime = $agentRuntime ?? [];
    $lastFailedTask = $agentRuntime['last_failed_task'] ?? null;
@endphp

<section class="grid-4" data-live-section="workers-runtime">
    <div class="metric {{ (($agentRuntime['orchestrator_health'] ?? 'unknown') === 'healthy') ? 'status-ok' : 'status-warn' }}">
        <span class="eyebrow">Orchestrator</span>
        <strong>{{ $runtime['status'] ?? 'unknown' }}</strong>
        <p>{{ $runtime['reason'] ?? 'runtime status unavailable' }}</p>
    </div>
    <div class="metric status-ok">
        <span class="eyebrow">Agent Queue</span>
        <strong>{{ $agentRuntime['queued_tasks'] ?? 0 }}</strong>
        <p>queued tasks</p>
    </div>
    <div class="metric {{ (($agentRuntime['failed_tasks'] ?? 0) > 0) ? 'status-bad' : 'status-ok' }}">
        <span class="eyebrow">Failures</span>
        <strong>{{ $agentRuntime['failed_tasks'] ?? 0 }}</strong>
        <p>failed task records</p>
    </div>
    <div class="metric {{ (($agentRuntime['stale_agents_count'] ?? 0) > 0) ? 'status-warn' : 'status-ok' }}">
        <span class="eyebrow">Stale Agents</span>
        <strong>{{ $agentRuntime['stale_agents_count'] ?? 0 }}</strong>
        <p>heartbeat older than threshold</p>
    </div>
</section>

<section class="panel">
    <div class="panel-head">
        <div>
            <h2>Orchestrator Runtime</h2>
            <p>This section summarizes queue pressure, retry/failure signals, and most recent orchestrator outcomes.</p>
        </div>
        <span class="badge {{ (($agentRuntime['orchestrator_health'] ?? 'unknown') === 'healthy') ? 'ok' : 'warn' }}">{{ $agentRuntime['orchestrator_health'] ?? 'unknown' }}</span>
    </div>
    <div class="table-wrap">
        <div class="table">
            <div class="row cols-4">
                <span>Running tasks {{ $agentRuntime['running_tasks'] ?? 0 }}</span>
                <span>Retrying {{ $agentRuntime['retrying_tasks'] ?? 0 }}</span>
                <span>Completed {{ $agentRuntime['completed_tasks'] ?? 0 }}</span>
                <span>Oldest queued age {{ isset($agentRuntime['oldest_queued_age_seconds']) ? ($agentRuntime['oldest_queued_age_seconds'] . 's') : '-' }}</span>
            </div>
            <div class="row cols-3">
                <span>Last success <span data-utc="{{ $runtime['last_success_run'] ?? '' }}">{{ $runtime['last_success_run'] ?? 'none' }}</span></span>
                <span>Last failed run <span data-utc="{{ $runtime['last_failed_run'] ?? '' }}">{{ $runtime['last_failed_run'] ?? 'none' }}</span></span>
                <span>Retry status {{ $runtime['retry_status'] ?? 'unknown' }}</span>
            </div>
            <div class="row cols-3">
                <span>Retry default {{ $agentRuntime['retry_policy']['default_max_attempts'] ?? 3 }} attempts</span>
                <span>Workflow poll {{ $agentRuntime['retry_policy']['workflow_poll_interval_seconds'] ?? 5 }}s</span>
                <span>Stale threshold {{ $agentRuntime['retry_policy']['stale_threshold_seconds'] ?? 180 }}s</span>
            </div>
            @if(!empty($agentRuntime['recovery_actions']))
                <p style="margin-top:8px">Recovery suggestions: {{ implode(' ', $agentRuntime['recovery_actions']) }}</p>
            @endif
            @if($lastFailedTask)
                <div class="row cols-1">
                    <span class="badge warn">Last failed task {{ $lastFailedTask['task_id'] ?? '' }}</span>
                </div>
                <p style="margin-top:8px">
                    Agent {{ $lastFailedTask['assigned_agent'] ?? '-' }} | type {{ $lastFailedTask['task_type'] ?? '-' }} |
                    attempts {{ $lastFailedTask['attempts'] ?? 0 }}/{{ $lastFailedTask['max_attempts'] ?? 0 }} |
                    updated <span data-utc="{{ $lastFailedTask['updated_at'] ?? '' }}">{{ $lastFailedTask['updated_at'] ?? 'unknown' }}</span>
                    @if(!empty($lastFailedTask['detail']))
                        | reason {{ $lastFailedTask['detail'] }}
                    @endif
                </p>
            @else
                <p>No failed task record in the current runtime window.</p>
            @endif
            <form method="POST" action="{{ route('workers.recover-stale') }}" class="stack" style="margin-top:8px;max-width:520px">
                @csrf
                <div class="row cols-3">
                    <label>Stale seconds<input type="number" min="30" max="3600" name="stale_after_seconds" value="{{ $agentRuntime['stale_threshold_seconds'] ?? 180 }}"></label>
                    <label style="display:flex;align-items:end;gap:8px"><input type="checkbox" name="queue_watchdog_review" value="1" checked> Queue watchdog review task</label>
                </div>
                <div class="actions"><button class="secondary small" type="submit">Recover Stale Agents</button></div>
            </form>
        </div>
    </div>
</section>

<section class="panel" data-live-section="workers-registry">
    <div class="panel-head"><div><h2>Worker Registry</h2><p>Actions are queued and audited; runtime services consume the action queue.</p></div><span class="badge ok">audited controls</span></div>
    @forelse(($workers['workers'] ?? []) as $worker)
        <div class="panel" style="box-shadow:none;margin-bottom:12px">
            <div class="table-wrap"><div class="table">
            <div class="row cols-5"><strong>{{ $worker['name'] }}</strong><span>{{ $worker['worker_type'] }}</span><span class="badge {{ in_array($worker['status'], ['running','ready','standby']) ? 'ok' : 'warn' }}">{{ $worker['status'] }}</span><span>last <span data-utc="{{ $worker['last_run_at'] ?? '' }}">{{ $worker['last_run_at'] ?? 'never' }}</span></span><span>next <span data-utc="{{ $worker['next_run_at'] ?? '' }}">{{ $worker['next_run_at'] ?? 'not scheduled' }}</span></span></div>
            <div class="row cols-4"><span>Duration {{ $worker['duration_ms'] }} ms</span><span>Errors {{ $worker['error_count'] }}</span><span>Retries {{ $worker['retry_count'] }}</span><span>{{ $worker['enabled'] ? 'enabled' : 'disabled' }}</span></div>
            @php $runSummary = $worker['run_summary'] ?? []; @endphp
            <div class="row cols-4">
                <span>Latest run {{ $runSummary['latest_run_status'] ?? '-' }}</span>
                <span>Completed runs {{ $runSummary['completed_runs'] ?? 0 }}</span>
                <span>Retry runs {{ $runSummary['retry_runs'] ?? 0 }}</span>
                <span>Failed runs {{ $runSummary['failed_runs'] ?? 0 }} / queued {{ $runSummary['queued_runs'] ?? 0 }}</span>
            </div>
            @php $health = $worker['health_json'] ?? []; @endphp
            <div class="row" style="grid-template-columns:repeat(5,1fr)">
                <span>Current pair {{ $health['current_pair'] ?? '-' }}</span>
                <span>Processed {{ $health['pairs_processed'] ?? '-' }}</span>
                <span>Stale {{ $health['stale_pairs'] ?? '-' }}</span>
                <span>Valid signals {{ $health['valid_signals'] ?? '-' }}</span>
                <span>Blocked {{ $health['blocked_signals'] ?? '-' }}</span>
            </div>
            <p>{{ $health['note'] ?? 'No worker note available.' }}</p>
            <div class="actions">
                @foreach(['start','stop','restart'] as $action)
                    <form method="POST" action="{{ route('workers.action', [$worker['worker_id'], $action]) }}">@csrf<button class="secondary small" type="submit">{{ ucfirst($action) }}</button></form>
                @endforeach
            </div>
            </div></div>
        </div>
    @empty
        <p class="empty">No workers registered.</p>
    @endforelse
</section>
@endsection
