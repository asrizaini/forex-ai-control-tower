@extends('layouts.control', ['title' => $title, 'description' => 'Pair-by-pair structured analysis derived from the latest market/candle/news state.'])

@section('content')
<section class="panel">
    <div class="panel-head">
        <div><h2>{{ $title }}</h2><p>Rows show every enabled pair, including stale or missing data.</p></div>
        <form method="POST" action="{{ route('analysis.run') }}">@csrf<button type="submit">Refresh Analysis</button></form>
    </div>
    <div class="table-wrap"><div class="table">
        @forelse(($summaries['items'] ?? []) as $item)
            @php $analysis = $item[$analysisKey] ?? []; @endphp
            <div class="row" style="grid-template-columns:.7fr .6fr .7fr .7fr 2fr">
                <strong>{{ $item['symbol'] }}</strong>
                <span>{{ $item['timeframe'] }}</span>
                <span class="badge {{ ($analysis['status'] ?? '') === 'ok' || ($analysis['bias'] ?? '') === 'bullish' ? 'ok' : ((($analysis['status'] ?? '') === 'stale') ? 'bad' : 'warn') }}">{{ $analysis['status'] ?? $analysis['bias'] ?? 'unknown' }}</span>
                <span>{{ $analysis['direction'] ?? $analysis['bias'] ?? '-' }}</span>
                <span>{{ $analysis['summary'] ?? 'No summary.' }}</span>
            </div>
        @empty
            <p class="empty">No analysis output yet.</p>
        @endforelse
    </div></div>
</section>
@endsection
