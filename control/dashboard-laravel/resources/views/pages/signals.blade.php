@extends('layouts.control', ['title' => 'Signals', 'description' => 'Monitor-only signal output for all enabled pairs. No order is sent from this page.'])

@section('content')
@php
    $recordRows = collect($records['items'] ?? [])
        ->groupBy(fn($item) => ($item['pair'] ?? 'unknown') . '|' . ($item['timeframe'] ?? 'M1'))
        ->map(fn($items) => $items[0])
        ->values();
    $summaryRows = collect($signals['items'] ?? []);
    $signalRows = $recordRows
        ->concat($summaryRows)
        ->groupBy(fn($item) => ($item['pair'] ?? 'unknown') . '|' . ($item['timeframe'] ?? 'M1'))
        ->map(fn($items) => $items[0])
        ->values();
@endphp
<section class="grid-4" data-live-section="signals-summary-cards">
    @foreach(['no_valid_signal'=>'No Valid Signal','blocked'=>'Blocked','stale'=>'Stale','missing_data'=>'Missing Data'] as $key => $label)
        <div class="metric"><span>{{ $label }}</span><strong>{{ count(($signals['summary'] ?? [])[$key] ?? []) }}</strong><p>{{ implode(', ', ($signals['summary'] ?? [])[$key] ?? []) ?: 'none' }}</p></div>
    @endforeach
</section>
<section class="panel" data-live-section="signals-table">
    <div class="panel-head">
        <div><h2>Latest Signals</h2><p>Signals combine technical, candle, trend, fundamental/news, and risk status.</p></div>
        <div class="actions">
            <form method="POST" action="{{ route('analysis.run') }}">@csrf<button type="submit">Generate Monitor Signals</button></form>
            <a class="button secondary small" href="{{ route('dashboard.pair-summary') }}">Pair Summary</a>
            <a class="button secondary small" href="{{ route('dashboard.risk-validation') }}">Risk Validation</a>
        </div>
    </div>
    <div class="table-wrap"><div class="table">
        @forelse($signalRows as $signal)
            <div class="row" style="grid-template-columns:.65fr .45fr .6fr .55fr .75fr 1.4fr .9fr">
                <strong>{{ $signal['pair'] }}</strong>
                <span>{{ $signal['timeframe'] }}</span>
                <span class="badge {{ in_array($signal['direction'], ['buy','sell']) ? 'ok' : ($signal['signal_status'] === 'blocked' ? 'bad' : 'warn') }}">{{ $signal['direction'] }}</span>
                <span>{{ $signal['confidence'] }}%</span>
                <span>{{ $signal['freshness_status'] }}</span>
                <span>{{ $signal['reason'] }}</span>
                <span data-utc="{{ $signal['timestamp'] ?? '' }}">{{ $signal['timestamp'] ?? 'unknown' }}</span>
            </div>
        @empty
            <p class="empty">No signal records yet. Run analysis to produce monitor-only signal output.</p>
        @endforelse
    </div></div>
</section>
@endsection
