@extends('layouts.control', ['title' => 'Trading Pairs', 'description' => 'Enable, disable, and assign strategies per pair. Workers process enabled pairs only.'])

@section('content')
@php
    $pairItems = $pairs['items'] ?? [];
    $enabledCount = collect($pairItems)->where('enabled', true)->count();
    $disabledCount = collect($pairItems)->where('enabled', false)->count();
@endphp
<section class="grid-4">
    <div class="metric status-ok"><span class="eyebrow">Configured Pairs</span><strong>{{ count($pairItems) }}</strong><span>all symbols in control plane</span></div>
    <div class="metric {{ $enabledCount > 0 ? 'status-ok' : 'status-warn' }}"><span class="eyebrow">Enabled</span><strong>{{ $enabledCount }}</strong><span>actively processed by agents</span></div>
    <div class="metric {{ $disabledCount > 0 ? 'status-warn' : 'status-ok' }}"><span class="eyebrow">Disabled</span><strong>{{ $disabledCount }}</strong><span>kept visible, skipped safely</span></div>
    <div class="metric status-ok"><span class="eyebrow">Next Step</span><strong>Run Analysis</strong><span><a href="{{ route('dashboard.signals') }}">Open Signals</a></span></div>
</section>
<section class="panel">
    <div class="panel-head">
        <div><h2>Configured Pairs</h2><p>Disabled pairs are skipped and still visible here instead of disappearing silently.</p></div>
        <div class="actions">
            <a class="button secondary small" href="{{ route('dashboard.pair-summary') }}">Pair Summary</a>
            <a class="button secondary small" href="{{ route('dashboard.signals') }}">Signals</a>
        </div>
    </div>
    <div class="table-wrap"><div class="table">
        @forelse(($pairs['items'] ?? []) as $pair)
            @php
                $analysisTimeframes = implode(',', array_values(array_unique(array_filter($pair['metadata_json']['analysis_timeframes'] ?? []))));
            @endphp
            <form class="row" style="grid-template-columns:1fr 1fr .8fr 1fr 1.2fr .7fr auto auto" method="POST" action="{{ route('trading-pairs.update', $pair['symbol']) }}">
                @csrf
                <input name="symbol" value="{{ $pair['symbol'] }}" readonly>
                <input name="display_name" value="{{ $pair['display_name'] ?? $pair['symbol'] }}">
                <select name="default_timeframe">
                    @foreach(['M1','M5','M15','M30','H1','H4','D1'] as $tf)
                        <option value="{{ $tf }}" @selected(($pair['default_timeframe'] ?? 'M1') === $tf)>{{ $tf }}</option>
                    @endforeach
                </select>
                <input name="additional_timeframes" value="{{ $analysisTimeframes }}" placeholder="M1,M5,H1">
                <select name="assigned_strategy_id">
                    <option value="">No strategy</option>
                    @foreach(($strategies['items'] ?? []) as $strategy)
                        <option value="{{ $strategy['strategy_id'] }}" @selected(($pair['assigned_strategy_id'] ?? '') === $strategy['strategy_id'])>{{ $strategy['strategy_id'] }}</option>
                    @endforeach
                    <option value="trend_pullback_v1" @selected(($pair['assigned_strategy_id'] ?? '') === 'trend_pullback_v1')>trend_pullback_v1</option>
                </select>
                <label style="display:flex;align-items:center;gap:8px"><input style="width:auto" type="checkbox" name="enabled" value="1" @checked($pair['enabled'])> <span class="badge {{ $pair['enabled'] ? 'ok' : 'warn' }}">{{ $pair['enabled'] ? 'Enabled' : 'Disabled' }}</span></label>
                <button type="submit">Save</button>
                <a class="button secondary small" href="{{ route('dashboard.pair-detail', $pair['symbol']) }}">Details</a>
            </form>
        @empty
            <p class="empty">No pairs configured yet.</p>
        @endforelse
    </div></div>
</section>

<section class="panel">
    <div class="panel-head"><div><h2>Add Pair</h2><p>Add a new symbol exactly as the broker/MT5 bridge exposes it.</p></div></div>
    <form class="form-grid" method="POST" action="{{ route('trading-pairs.create') }}">
        @csrf
        <input name="symbol" placeholder="AUDUSD">
        <input name="display_name" placeholder="AUD/USD">
        <select name="default_timeframe">@foreach(['M1','M5','M15','M30','H1','H4','D1'] as $tf)<option value="{{ $tf }}">{{ $tf }}</option>@endforeach</select>
        <input name="additional_timeframes" placeholder="M1,M5,H1">
        <select name="assigned_strategy_id"><option value="trend_pullback_v1">trend_pullback_v1</option><option value="">No strategy</option></select>
        <label style="display:flex;align-items:center;gap:8px"><input style="width:auto" type="checkbox" name="enabled" value="1" checked> Enabled</label>
        <button type="submit">Add Pair</button>
    </form>
</section>
@endsection
