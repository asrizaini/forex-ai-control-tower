@extends('layouts.control', [
    'title' => 'Agent Theater',
    'description' => 'Compact real-time broadcast feed for agent and worker communication. Use Orchestrator Console for direct operator chat.',
    'eyebrow' => 'AI Trading Room',
])

@section('content')
@php
    $theaterEvents = array_reverse($events['events'] ?? []);
    $availableAgents = $events['agents'] ?? [];
    $availableStreams = $events['streams'] ?? [];
    $selectedAgents = (array)($filters['agent'] ?? []);
    $selectedStream = $filters['stream'] ?? '';
@endphp
<style>
    .feed-shell{background:#0f1720;border:1px solid #233044;border-radius:8px;color:#d9e5f2;display:grid;gap:12px;padding:14px}
    .feed-toolbar{align-items:end;display:grid;gap:10px;grid-template-columns:1.1fr .9fr .7fr .7fr auto}
    .feed-toolbar label{color:#96a6ba}
    .feed-toolbar select{background:#111c29;border-color:#304158;color:#e7eef7}
    .feed-actions{display:flex;gap:8px}
    .agent-picker{background:#111c29;border:1px solid #304158;border-radius:8px;display:flex;flex-wrap:wrap;gap:6px;max-height:86px;overflow:auto;padding:8px}
    .agent-chip{align-items:center;background:#162233;border:1px solid #2d4058;border-radius:999px;color:#cfdae8;display:flex;font-size:12px;font-weight:700;gap:5px;padding:5px 8px}
    .agent-chip input{accent-color:#15a388;width:auto}
    .feed-status{align-items:center;color:#90a3b8;display:flex;font-size:12px;gap:10px;justify-content:space-between}
    .compact-feed{background:#0b1119;border:1px solid #233044;border-radius:8px;display:grid;max-height:calc(100vh - 360px);min-height:480px;overflow:auto}
    .feed-row{border-bottom:1px solid #1c2a3a;display:grid;gap:10px;grid-template-columns:170px minmax(0,1fr) 180px;padding:9px 12px}
    .feed-row:hover{background:#111a26}
    .feed-agent{color:#76e1cd;font-weight:850;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .feed-room{color:#8fa3ba;font-size:12px;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .feed-summary{color:#e6edf6;font-size:13px;line-height:1.35}
    .feed-next{color:#9fb0c4;font-size:12px;line-height:1.35;margin-top:3px}
    .feed-time{color:#91a4b8;font-size:11px;text-align:right;white-space:nowrap}
    .feed-tags{display:flex;flex-wrap:wrap;gap:5px;justify-content:flex-end;margin-top:5px}
    .feed-tags span{background:#121f2d;border:1px solid #293b52;border-radius:999px;color:#a9b8ca;font-size:10px;padding:3px 6px}
    .empty-dark{color:#91a4b8;padding:28px;text-align:center}
    .theater-links{display:flex;gap:8px;justify-content:flex-end}
    @media(max-width:1150px){.feed-toolbar{grid-template-columns:1fr 1fr}.feed-actions,.theater-links{justify-content:flex-start}.feed-row{grid-template-columns:1fr}.feed-time{text-align:left}.feed-tags{justify-content:flex-start}.compact-feed{max-height:none}}
</style>

<section class="feed-shell" data-feed-url="{{ route('agent-theater.feed') }}">
    <form id="feedFilters" class="feed-toolbar" method="GET" action="{{ route('dashboard.agent-theater') }}">
        <label>Room
            <select name="stream">
                <option value="">All rooms</option>
                @foreach($availableStreams as $stream)
                    <option value="{{ $stream }}" @selected($selectedStream === $stream)>{{ $stream }}</option>
                @endforeach
            </select>
        </label>
        <label>Language
            <select name="language">
                <option value="en" @selected(($filters['language'] ?? 'en') === 'en')>English</option>
                <option value="ms-MY" @selected(($filters['language'] ?? '') === 'ms-MY')>Bahasa Melayu Malaysia</option>
            </select>
        </label>
        <label>Limit
            <select name="limit">
                @foreach([50,100,150,200] as $limit)
                    <option value="{{ $limit }}" @selected((int)($filters['limit'] ?? 100) === $limit)>{{ $limit }}</option>
                @endforeach
            </select>
        </label>
        <label>Refresh
            <select id="refreshRate">
                <option value="2000">2 seconds</option>
                <option value="5000" selected>5 seconds</option>
                <option value="10000">10 seconds</option>
                <option value="30000">30 seconds</option>
                <option value="0">Paused</option>
            </select>
        </label>
        <div class="feed-actions">
            <button type="submit">Filter</button>
            <button class="secondary" type="button" id="refreshNow">Refresh</button>
        </div>
        <div style="grid-column:1/-1">
            <div class="agent-picker">
                @forelse($availableAgents as $agent)
                    <label class="agent-chip"><input type="checkbox" name="agent[]" value="{{ $agent }}" @checked(in_array($agent, $selectedAgents, true))>{{ $agent }}</label>
                @empty
                    <span class="muted">No agent names have been seen yet.</span>
                @endforelse
            </div>
        </div>
    </form>
    <div class="feed-status">
        <span><strong id="visibleCount">{{ count($theaterEvents) }}</strong> visible · <span id="lastUpdated">loaded</span></span>
        <div class="theater-links">
            <a class="button secondary small" href="{{ route('dashboard.orchestrator-console') }}">Orchestrator Console</a>
            <a class="button secondary small" href="{{ route('dashboard.agent-theater') }}">Clear Filters</a>
        </div>
    </div>
    <div id="agentFeed" class="compact-feed"></div>
</section>

<script>
    const initialEvents = @json($theaterEvents);
    const feedUrl = document.querySelector('.feed-shell').dataset.feedUrl;
    const feedEl = document.getElementById('agentFeed');
    const refreshRateEl = document.getElementById('refreshRate');
    const countEl = document.getElementById('visibleCount');
    const lastUpdatedEl = document.getElementById('lastUpdated');
    let refreshTimer = null;

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    }

    function eventSummary(event) {
        return event.display?.summary || event.summary || 'No summary available.';
    }

    function eventRisk(event) {
        return event.display?.risk_status || event.risk_status || 'guarded';
    }

    function renderFeed(events) {
        countEl.textContent = events.length;
        if (!events.length) {
            feedEl.innerHTML = '<div class="empty-dark">No events match the current filters.</div>';
            return;
        }
        feedEl.innerHTML = events.map((event) => `
            <article class="feed-row">
                <div>
                    <div class="feed-agent">${escapeHtml(event.agent || 'Agent')}</div>
                    <div class="feed-room">${escapeHtml(event.stream || 'Live Chat View')}</div>
                </div>
                <div>
                    <div class="feed-summary">${escapeHtml(eventSummary(event))}</div>
                    ${event.next_action ? `<div class="feed-next">${escapeHtml(event.next_action)}</div>` : ''}
                </div>
                <div>
                    <div class="feed-time">${escapeHtml(event.timestamp || '')}</div>
                    <div class="feed-tags"><span>${escapeHtml(eventRisk(event))}</span><span>${escapeHtml(event.result || 'observed')}</span></div>
                </div>
            </article>
        `).join('');
    }

    function queryFromFilters() {
        return new URLSearchParams(new FormData(document.getElementById('feedFilters'))).toString();
    }

    async function refreshFeed() {
        const response = await fetch(`${feedUrl}?${queryFromFilters()}`, {headers: {'Accept': 'application/json'}});
        if (!response.ok) throw new Error('Feed refresh failed');
        const body = await response.json();
        renderFeed([...(body.events || [])].reverse());
        lastUpdatedEl.textContent = `updated ${new Date().toLocaleTimeString()}`;
    }

    function scheduleRefresh() {
        if (refreshTimer) clearInterval(refreshTimer);
        const interval = Number(refreshRateEl.value);
        if (interval > 0) refreshTimer = setInterval(() => refreshFeed().catch(() => { lastUpdatedEl.textContent = 'refresh failed'; }), interval);
    }

    document.getElementById('refreshNow').addEventListener('click', () => refreshFeed().catch(() => { lastUpdatedEl.textContent = 'refresh failed'; }));
    refreshRateEl.addEventListener('change', scheduleRefresh);
    renderFeed(initialEvents);
    scheduleRefresh();
</script>
@endsection
