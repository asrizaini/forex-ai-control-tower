@extends('layouts.control', ['title' => 'News', 'description' => 'News ingestion, freshness, source filters, sentiment tags, and calendar-event mapping.'])

@section('content')
<section class="grid-3">
    <div class="metric"><span class="eyebrow">Provider</span><strong>{{ $status['provider_type'] ?? 'unknown' }}</strong><span>{{ !empty($status['provider_enabled']) ? 'enabled' : 'disabled' }}</span></div>
    <div class="metric"><span class="eyebrow">Risk</span><strong>{{ $status['risk_status'] ?? 'unknown' }}</strong><span>{{ $status['note'] ?? '' }}</span></div>
    <div class="metric"><span class="eyebrow">Events</span><strong>{{ $status['events_count'] ?? 0 }}</strong><span>provider calendar events</span></div>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>News Filters</h2><p>Search normalized news records and mapped calendar context.</p></div></div>
    <form class="form-grid" method="GET" action="{{ route('dashboard.news') }}">
        <label>Keyword<input name="keyword" value="{{ $filters['keyword'] ?? '' }}"></label>
        <label>Currency<input name="currency" value="{{ $filters['currency'] ?? '' }}" placeholder="USD"></label>
        <label>Source<input name="source" value="{{ $filters['source'] ?? '' }}"></label>
        <button type="submit">Filter</button>
    </form>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Normalized News</h2><p>{{ $items['total'] ?? 0 }} records. Raw records are retained in the API, not rendered by default.</p></div></div>
    @forelse(($items['results'] ?? []) as $item)
        <div class="row cols-5"><strong>{{ $item['title'] }}</strong><span>{{ implode(',', $item['currencies'] ?? []) }}</span><span>{{ $item['sentiment'] }}</span><span>{{ $item['published_at'] ?? 'unknown' }}</span><a href="{{ $item['url'] }}" target="_blank" rel="noreferrer">Open</a></div>
    @empty
        <p class="empty">No normalized news records yet.</p>
    @endforelse
</section>
@endsection
