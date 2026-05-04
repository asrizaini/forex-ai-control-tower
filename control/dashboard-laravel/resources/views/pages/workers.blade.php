@extends('layouts.control', ['title' => 'Workers / Agents', 'description' => 'Monitor and control calendar, news, analysis, signal, risk, notification, and validation workers.'])

@section('content')
<section class="panel">
    <div class="panel-head"><div><h2>Worker Registry</h2><p>Actions are queued and audited; runtime services consume the action queue.</p></div><span class="badge ok">audited controls</span></div>
    @forelse(($workers['workers'] ?? []) as $worker)
        <div class="panel" style="box-shadow:none;margin-bottom:12px">
            <div class="row cols-5"><strong>{{ $worker['name'] }}</strong><span>{{ $worker['worker_type'] }}</span><span class="badge {{ in_array($worker['status'], ['running','ready','standby']) ? 'ok' : 'warn' }}">{{ $worker['status'] }}</span><span>last {{ $worker['last_run_at'] ?? 'never' }}</span><span>next {{ $worker['next_run_at'] ?? 'not scheduled' }}</span></div>
            <div class="row cols-4"><span>Duration {{ $worker['duration_ms'] }} ms</span><span>Errors {{ $worker['error_count'] }}</span><span>Retries {{ $worker['retry_count'] }}</span><span>{{ $worker['enabled'] ? 'enabled' : 'disabled' }}</span></div>
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
        </div>
    @empty
        <p class="empty">No workers registered.</p>
    @endforelse
</section>
@endsection
