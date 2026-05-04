@extends('layouts.control', ['title' => 'Economic Calendar', 'description' => 'Browse normalized calendar events, source health, manual scrape requests, paging, and filters.'])

@section('content')
<section class="panel">
    <div class="panel-head"><div><h2>Calendar Controls</h2><p>Events are normalized into one internal schema with raw and normalized views preserved.</p></div><span class="badge {{ ($status['status'] ?? '') === 'ok' ? 'ok' : 'warn' }}">{{ $status['status'] ?? 'unknown' }}</span></div>
    <form class="form-grid" method="GET" action="{{ route('dashboard.calendar') }}">
        <label>Currency<input name="currency" value="{{ $filters['currency'] ?? '' }}" placeholder="USD"></label>
        <label>Impact<select name="impact"><option value="">Any</option><option @selected(($filters['impact'] ?? '')==='high')>high</option><option @selected(($filters['impact'] ?? '')==='medium')>medium</option><option @selected(($filters['impact'] ?? '')==='low')>low</option></select></label>
        <label>Keyword<input name="keyword" value="{{ $filters['keyword'] ?? '' }}" placeholder="CPI"></label>
        <button type="submit">Filter</button>
    </form>
    <form method="POST" action="{{ route('calendar.scrape') }}" style="margin-top:12px">@csrf<button class="secondary" type="submit">Manual Scrape</button></form>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Events</h2><p>{{ $events['total'] ?? 0 }} records. Daily, weekly, monthly, and custom range views use these filters.</p></div></div>
    @forelse(($events['results'] ?? []) as $event)
        <div class="row cols-5"><strong>{{ $event['event_name'] }}</strong><span>{{ $event['currency'] }} · {{ $event['impact'] }}</span><span>{{ $event['event_time_utc'] }}</span><span>{{ $event['actual'] ?: '-' }} / {{ $event['forecast'] ?: '-' }} / {{ $event['previous'] ?: '-' }}</span><span>{{ $event['source'] }}</span></div>
    @empty
        <p class="empty">No calendar events stored yet. Enable a source and run the calendar worker/manual scrape.</p>
    @endforelse
</section>
@endsection
