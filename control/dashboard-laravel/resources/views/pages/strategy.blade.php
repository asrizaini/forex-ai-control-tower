@extends('layouts.control', ['title' => 'Strategy', 'description' => 'Strategy enablement, pair assignment, validation status, conflicts, and performance summary.'])

@section('content')
<section class="panel">
    <div class="panel-head"><div><h2>Strategy Registry</h2><p>Only governed strategies can produce monitor-only signals; execution still requires approval and guard token.</p></div></div>
    <div class="table">
        @forelse(($strategies['items'] ?? []) as $strategy)
            <div class="row" style="grid-template-columns:1fr .8fr .7fr 1fr 1fr">
                <strong>{{ $strategy['strategy_id'] }}</strong>
                <span class="badge {{ $strategy['enabled'] ? 'ok' : 'warn' }}">{{ $strategy['lifecycle_state'] }}</span>
                <span>{{ $strategy['validation'] }}</span>
                <span>Pairs: {{ implode(', ', $strategy['assigned_pairs'] ?? []) ?: 'none' }}</span>
                <span>Best score {{ $strategy['performance_summary']['best_quality_score'] ?? 0 }}</span>
            </div>
        @empty
            <p class="empty">No strategy records synced yet. Sync strategy plugins from the Strategies API/governance flow.</p>
        @endforelse
    </div>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Plugin Metadata</h2><p>Discovered local strategy plugins.</p></div></div>
    <div class="table">
        @forelse(($plugins['plugins'] ?? []) as $plugin)
            <div class="row cols-4"><strong>{{ $plugin['strategy_id'] ?? 'strategy' }}</strong><span>{{ $plugin['name'] ?? '' }}</span><span>{{ $plugin['version'] ?? '' }}</span><span>{{ implode(', ', $plugin['supported_symbols'] ?? []) }}</span></div>
        @empty
            <p class="empty">No plugin metadata visible.</p>
        @endforelse
    </div>
</section>
@endsection
