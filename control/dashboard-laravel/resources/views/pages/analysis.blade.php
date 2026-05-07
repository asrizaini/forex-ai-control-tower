@extends('layouts.control', ['title' => $title, 'description' => $analysisType === 'technical' ? 'Indicator output combined with calendar/news risk context.' : 'Currency and pair-level fundamental summaries from calendar and news context.'])

@section('content')
<section class="panel">
    <div class="panel-head">
        <div><h2>{{ $title }} Snapshots</h2><p>Workers store structured snapshots for dashboard display and API consumers.</p></div>
        @if($authenticated)<form method="POST" action="{{ route('analysis.seed', $analysisType) }}">@csrf<button class="secondary" type="submit">Seed Test Snapshot</button></form>@endif
    </div>
    @forelse(($snapshots['items'] ?? []) as $snapshot)
        <div class="panel" style="box-shadow:none;margin-bottom:12px">
            <div class="row cols-5"><strong>{{ $snapshot['symbol'] ?: 'global' }}</strong><span>{{ $snapshot['timeframe'] ?: '-' }}</span><span>{{ $snapshot['status'] }}</span><span>confidence {{ $snapshot['confidence'] ?? '-' }}</span><span data-utc="{{ $snapshot['created_at'] ?? '' }}">{{ $snapshot['created_at'] }}</span></div>
            <p>{{ $snapshot['summary'] }}</p>
        </div>
    @empty
        <p class="empty">No {{ strtolower($title) }} snapshots yet. Start the worker or seed a test snapshot.</p>
    @endforelse
</section>
@endsection
