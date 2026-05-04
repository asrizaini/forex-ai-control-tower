@extends('layouts.control', ['title' => 'Signals', 'description' => 'Monitor-only signal output for all enabled pairs. No order is sent from this page.'])

@section('content')
<section class="grid-4">
    @foreach(['no_valid_signal'=>'No Valid Signal','blocked'=>'Blocked','stale'=>'Stale','missing_data'=>'Missing Data'] as $key => $label)
        <div class="metric"><span>{{ $label }}</span><strong>{{ count(($signals['summary'] ?? [])[$key] ?? []) }}</strong><p>{{ implode(', ', ($signals['summary'] ?? [])[$key] ?? []) ?: 'none' }}</p></div>
    @endforeach
</section>
<section class="panel">
    <div class="panel-head">
        <div><h2>Latest Signals</h2><p>Signals combine technical, candle, trend, fundamental/news, and risk status.</p></div>
        <form method="POST" action="{{ route('analysis.run') }}">@csrf<button type="submit">Generate Monitor Signals</button></form>
    </div>
    <div class="table">
        @forelse(($records['items'] ?? []) as $signal)
            <div class="row" style="grid-template-columns:.7fr .5fr .6fr .7fr .9fr 1.8fr">
                <strong>{{ $signal['pair'] }}</strong>
                <span>{{ $signal['timeframe'] }}</span>
                <span class="badge {{ in_array($signal['direction'], ['buy','sell']) ? 'ok' : ($signal['signal_status'] === 'blocked' ? 'bad' : 'warn') }}">{{ $signal['direction'] }}</span>
                <span>{{ $signal['confidence'] }}%</span>
                <span>{{ $signal['freshness_status'] }}</span>
                <span>{{ $signal['reason'] }}</span>
            </div>
        @empty
            <p class="empty">No signal records yet. Run analysis to produce monitor-only signal output.</p>
        @endforelse
    </div>
</section>
@endsection
