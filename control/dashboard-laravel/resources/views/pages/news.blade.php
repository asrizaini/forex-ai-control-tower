@extends('layouts.control', ['title' => 'News', 'description' => 'News ingestion, freshness, source filters, sentiment tags, and calendar-event mapping.'])

@section('content')
<style>
    .impact-high{animation:pulseNews 2s ease-in-out infinite}
    .event-row{position:relative}
    .event-row .hover-note{background:#0f2135;border:1px solid #2f4a66;border-radius:8px;color:#dce9f8;display:none;font-size:12px;line-height:1.35;max-width:440px;padding:8px 10px;position:absolute;right:8px;top:44px;z-index:25}
    .event-row:hover .hover-note{display:block}
    @keyframes pulseNews{0%{box-shadow:0 0 0 0 rgba(255,207,112,.28)}70%{box-shadow:0 0 0 10px rgba(255,207,112,0)}100%{box-shadow:0 0 0 0 rgba(255,207,112,0)}}
</style>
<section class="grid-3" data-live-section="news-provider-cards">
    <div class="metric"><span class="eyebrow">Provider</span><strong>{{ $status['provider_type'] ?? 'unknown' }}</strong><span>{{ !empty($status['provider_enabled']) ? 'enabled' : 'disabled' }}</span></div>
    <div class="metric"><span class="eyebrow">Risk</span><strong>{{ $status['risk_status'] ?? 'unknown' }}</strong><span>{{ $status['note'] ?? '' }}</span></div>
    <div class="metric"><span class="eyebrow">Events</span><strong>{{ $status['events_count'] ?? 0 }}</strong><span>provider calendar events</span></div>
</section>
<section class="grid-3" data-live-section="news-window-cards">
    <div class="metric"><span class="eyebrow">Block Before Event</span><strong>{{ $status['high_impact_window_minutes'] ?? 45 }} min</strong><span>pre-event safety window</span></div>
    <div class="metric"><span class="eyebrow">Block After Event</span><strong>{{ $status['high_impact_cooldown_minutes'] ?? 90 }} min</strong><span>post-event cooldown</span></div>
    <div class="metric"><span class="eyebrow">Safe Resume ETA</span><strong>{{ $status['safe_resume_in_minutes'] ?? 'n/a' }}</strong><span>{{ $status['safe_resume_at'] ?? 'no active block window' }}</span></div>
</section>
<section class="notice warn" data-live-section="news-active-halt">
    @if(!empty($status['active_halt_events']))
        <strong>High-impact news protection is active.</strong>
        Trading resumes after cooldown ends. Hover event rows for exact start/end windows.
    @else
        <strong>No active high-impact cooldown window.</strong>
        News gate is clear at the moment; continue monitoring upcoming events.
    @endif
</section>
<section class="panel" data-live-section="news-filter-panel">
    <div class="panel-head"><div><h2>News Filters</h2><p>Search normalized news records and mapped calendar context.</p></div></div>
    <form class="form-grid" method="GET" action="{{ route('dashboard.news') }}">
        <label>Keyword<input name="keyword" value="{{ $filters['keyword'] ?? '' }}"></label>
        <label>Currency<input name="currency" value="{{ $filters['currency'] ?? '' }}" placeholder="USD"></label>
        <label>Source<input name="source" value="{{ $filters['source'] ?? '' }}"></label>
        <button type="submit">Filter</button>
    </form>
</section>
<section class="panel" data-live-section="news-normalized-table">
    <div class="panel-head"><div><h2>Normalized News</h2><p>{{ $items['total'] ?? 0 }} records. Raw records are retained in the API, not rendered by default.</p></div></div>
    <div class="table-wrap"><div class="table">
        @forelse(($items['results'] ?? []) as $item)
            <div class="row cols-5"><strong>{{ $item['title'] }}</strong><span>{{ implode(',', $item['currencies'] ?? []) }}</span><span>{{ $item['sentiment'] }}</span><span data-utc="{{ $item['published_at'] ?? '' }}">{{ $item['published_at'] ?? 'unknown' }}</span><a href="{{ $item['url'] }}" target="_blank" rel="noreferrer">Open</a></div>
        @empty
            <p class="empty">No normalized news records yet.</p>
        @endforelse
    </div></div>
</section>
<section class="panel" data-live-section="news-live-events">
    <div class="panel-head"><div><h2>Live Provider Events</h2><p>Direct feed from the active news provider so agent updates stay visible even before normalization jobs persist records.</p></div></div>
    <div class="table-wrap"><div class="table">
        @forelse(($providerEvents['events'] ?? []) as $event)
            @php
                $eventTime = $event['event_time'] ?? null;
                $start = $eventTime ? \Carbon\Carbon::parse($eventTime)->subMinutes((int)($status['high_impact_window_minutes'] ?? 45))->toIso8601String() : null;
                $end = $eventTime ? \Carbon\Carbon::parse($eventTime)->addMinutes((int)($status['high_impact_cooldown_minutes'] ?? 90))->toIso8601String() : null;
            @endphp
            <div class="row event-row" style="grid-template-columns:1.8fr .7fr .6fr .9fr 1.2fr">
                <strong>{{ $event['title'] ?? 'Economic event' }}</strong>
                <span>{{ implode(',', $event['currencies'] ?? []) }}</span>
                <span class="badge {{ ($event['impact'] ?? '') === 'high' ? 'warn impact-high' : 'ok' }}">{{ $event['impact'] ?? 'unknown' }}</span>
                <span data-utc="{{ $event['event_time'] ?? '' }}" class="local-time">{{ $event['event_time'] ?? 'unknown' }}</span>
                <span>{{ $event['source'] ?? ($providerEvents['provider_type'] ?? 'provider') }}</span>
                <div class="hover-note">
                    Start: <span data-utc="{{ $start }}" class="local-time">{{ $start ?? 'unknown' }}</span><br>
                    Event: <span data-utc="{{ $event['event_time'] ?? '' }}" class="local-time">{{ $event['event_time'] ?? 'unknown' }}</span><br>
                    End: <span data-utc="{{ $end }}" class="local-time">{{ $end ?? 'unknown' }}</span><br>
                    Rule: block {{ $status['high_impact_window_minutes'] ?? 45 }} min before + {{ $status['high_impact_cooldown_minutes'] ?? 90 }} min after.
                </div>
            </div>
        @empty
            <p class="empty">No provider events available right now.</p>
        @endforelse
    </div></div>
</section>
<script>
document.addEventListener('DOMContentLoaded', function () {
    const formatLocal = function (raw) {
        if (typeof window.fxFormatKualaLumpur === 'function') {
            return window.fxFormatKualaLumpur(raw);
        }
        if (!raw) return '';
        const date = new Date(raw);
        if (Number.isNaN(date.getTime())) return raw;
        return date.toLocaleString('en-US', { timeZone: 'Asia/Kuala_Lumpur', hour12: true }) + ' GMT+8';
    };
    const applyTimes = function () {
        document.querySelectorAll('.local-time[data-utc], [data-utc]').forEach(function (cell) {
            const raw = cell.getAttribute('data-utc');
            if (!raw) return;
            cell.textContent = formatLocal(raw);
        });
    };
    window.fxAfterSectionRefresh = function () {
        applyTimes();
    };
    applyTimes();
});
</script>
@endsection
