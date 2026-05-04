@extends('layouts.control', ['title' => 'Pair Summary', 'description' => 'Per-pair freshness, candles, trend, signal, fundamental risk, and final conclusion.'])

@section('content')
@php $bucket = $summaries['summary'] ?? []; @endphp
<section class="grid-4">
    @foreach(['bullish'=>'Bullish','bearish'=>'Bearish','neutral'=>'Neutral','stale'=>'Stale'] as $key => $label)
        <div class="metric"><span>{{ $label }}</span><strong>{{ count($bucket[$key] ?? []) }}</strong><p>{{ implode(', ', $bucket[$key] ?? []) ?: 'none' }}</p></div>
    @endforeach
</section>
<section class="panel">
    <div class="panel-head">
        <div><h2>Enabled Pair Status</h2><p>Stale or missing data is excluded from final signal generation unless settings later allow it.</p></div>
        <form method="POST" action="{{ route('analysis.run') }}">@csrf<button type="submit">Run Analysis Now</button></form>
    </div>
    <div class="table">
        @forelse(($summaries['items'] ?? []) as $item)
            <div class="row" style="grid-template-columns:.7fr .55fr .8fr .8fr .8fr .8fr 1.5fr">
                <strong>{{ $item['symbol'] }}</strong>
                <span>{{ $item['timeframe'] }}</span>
                <span class="badge {{ $item['data_freshness_status'] === 'fresh' ? 'ok' : 'bad' }}">{{ $item['data_freshness_status'] }}</span>
                <span class="badge {{ $item['current_bias'] === 'bullish' ? 'ok' : ($item['current_bias'] === 'bearish' ? 'bad' : 'warn') }}">{{ $item['current_bias'] }}</span>
                <span>{{ $item['trend_status'] }}</span>
                <span>{{ $item['signal_status'] }} · {{ $item['signal_confidence'] }}%</span>
                <span>{{ $item['candle_summary'] }}</span>
            </div>
        @empty
            <p class="empty">No enabled pair summaries yet.</p>
        @endforelse
    </div>
</section>
@endsection
