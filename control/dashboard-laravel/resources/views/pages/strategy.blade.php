@extends('layouts.control', ['title' => 'Strategy', 'description' => 'Strategy enablement, pair assignment, validation status, conflicts, and performance summary.'])

@section('content')
@php
    $strategyItems = $strategies['items'] ?? [];
    $approvedCount = collect($strategyItems)->whereIn('lifecycle_state', ['approved_for_demo_auto','approved_for_manual','approved_for_live_restricted'])->count();
    $draftCount = collect($strategyItems)->where('lifecycle_state', 'draft')->count();
@endphp
<section class="grid-3">
    <div class="metric status-ok"><span class="eyebrow">Strategies</span><strong>{{ count($strategyItems) }}</strong><span>registered lifecycle entries</span></div>
    <div class="metric {{ $approvedCount > 0 ? 'status-ok' : 'status-warn' }}"><span class="eyebrow">Approved</span><strong>{{ $approvedCount }}</strong><span>ready for governed demo flow</span></div>
    <div class="metric {{ $draftCount > 0 ? 'status-warn' : 'status-ok' }}"><span class="eyebrow">Draft</span><strong>{{ $draftCount }}</strong><span>still under validation</span></div>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Strategy Registry</h2><p>Only governed strategies can produce monitor-only signals; execution still requires approval and guard token.</p></div></div>
    <div class="table-wrap"><div class="table">
        @forelse(($strategies['items'] ?? []) as $strategy)
            <div class="row" style="grid-template-columns:1fr .8fr .9fr 1.3fr .8fr">
                <strong>{{ $strategy['strategy_id'] }}</strong>
                <span class="badge {{ $strategy['enabled'] ? 'ok' : 'warn' }}">{{ $strategy['lifecycle_state'] }}</span>
                <span style="overflow-wrap:anywhere">{{ $strategy['validation'] }}</span>
                <span style="overflow-wrap:anywhere">Pairs: {{ implode(', ', $strategy['assigned_pairs'] ?? []) ?: 'none' }}</span>
                <span>Best score {{ $strategy['performance_summary']['best_quality_score'] ?? 0 }}</span>
            </div>
        @empty
            <p class="empty">No strategy records synced yet. Sync strategy plugins from the Strategies API/governance flow.</p>
        @endforelse
    </div></div>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Plugin Metadata</h2><p>Discovered local strategy plugins.</p></div></div>
    <div class="table-wrap"><div class="table">
        @forelse(($plugins['plugins'] ?? []) as $plugin)
            <div class="row cols-4"><strong>{{ $plugin['strategy_id'] ?? 'strategy' }}</strong><span>{{ $plugin['name'] ?? '' }}</span><span>{{ $plugin['version'] ?? '' }}</span><span>{{ implode(', ', $plugin['supported_symbols'] ?? []) }}</span></div>
        @empty
            <p class="empty">No plugin metadata visible.</p>
        @endforelse
    </div></div>
</section>
@endsection
