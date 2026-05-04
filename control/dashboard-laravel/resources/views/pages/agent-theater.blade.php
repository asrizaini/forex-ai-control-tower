@extends('layouts.control', [
    'title' => 'Agent Theater',
    'description' => 'Filtered live room for human-readable agent and worker communication. Use Orchestrator Console for direct operator chat.',
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
    .theater-layout{display:grid;gap:14px;grid-template-columns:320px minmax(0,1fr)}
    .chat-feed{background:#101820;border:1px solid #243244;border-radius:8px;display:grid;gap:10px;max-height:760px;overflow:auto;padding:14px}
    .chat-bubble{background:#f8fafc;border:1px solid #dfe7f0;border-radius:8px;padding:12px}
    .chat-bubble.orchestrator{background:#101820;border-color:#324256;color:#eef6ff}
    .chat-bubble.orchestrator p,.chat-bubble.orchestrator .muted{color:#aab8c8}
    .chat-top{align-items:center;display:flex;gap:10px;justify-content:space-between;margin-bottom:6px}
    .chat-agent{font-weight:860}
    .chat-time{color:#718096;font-size:12px;white-space:nowrap}
    .chat-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
    .chat-meta span{border:1px solid #d8e1eb;border-radius:999px;color:#53657b;font-size:12px;padding:4px 8px}
    .chat-bubble.orchestrator .chat-meta span{border-color:#34465a;color:#b8c5d3}
    .check-list{display:grid;gap:8px;max-height:380px;overflow:auto}
    .check-line{align-items:center;display:flex;gap:8px}
    .check-line input{width:auto}
    @media(max-width:1050px){.theater-layout{grid-template-columns:1fr}.chat-feed{max-height:none}}
</style>

<section class="grid-3">
    <div class="metric"><span class="eyebrow">Feed Type</span><strong>Broadcast</strong><p>Agent-to-agent and worker summaries only.</p></div>
    <div class="metric"><span class="eyebrow">Timezone</span><strong>MYT</strong><p>Timestamps render in Asia/Kuala_Lumpur.</p></div>
    <div class="metric"><span class="eyebrow">Direct Chat</span><strong>Separate</strong><p>Use the Orchestrator Console page for operator messages.</p></div>
</section>

<section class="theater-layout">
    <aside class="stack">
        <section class="panel">
            <div class="panel-head">
                <div><h2>Feed Filters</h2><p>Choose which room and agents are visible.</p></div>
            </div>
            <form class="stack" method="GET" action="{{ route('dashboard.agent-theater') }}">
                <label>Room / Stream
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
                <label>Visible Agents</label>
                <div class="check-list">
                    @forelse($availableAgents as $agent)
                        <label class="check-line">
                            <input type="checkbox" name="agent[]" value="{{ $agent }}" @checked(in_array($agent, $selectedAgents, true))>
                            <span>{{ $agent }}</span>
                        </label>
                    @empty
                        <p class="empty">No agent names have been seen yet.</p>
                    @endforelse
                </div>
                <div class="actions">
                    <button type="submit">Apply Filter</button>
                    <a class="button secondary" href="{{ route('dashboard.agent-theater') }}">Clear</a>
                </div>
            </form>
        </section>

        <section class="panel">
            <div class="panel-head"><div><h2>Operator Chat</h2><p>Direct messages are isolated from this broadcast view.</p></div></div>
            <a class="button" href="{{ route('dashboard.orchestrator-console') }}">Open Orchestrator Console</a>
        </section>
    </aside>

    <section class="panel">
        <div class="panel-head">
            <div><h2>Live Agent Feed</h2><p>Recent filtered events. This page has no chat input by design.</p></div>
            <span class="badge ok">{{ count($theaterEvents) }} visible</span>
        </div>
        <div class="chat-feed">
            @forelse($theaterEvents as $event)
                @php
                    $agent = $event['agent'] ?? 'Agent';
                    $bubbleClass = str_contains($agent, 'Orchestrator') ? 'orchestrator' : '';
                @endphp
                <article class="chat-bubble {{ $bubbleClass }}">
                    <div class="chat-top">
                        <span class="chat-agent">{{ $agent }}</span>
                        <span class="chat-time">{{ $event['timestamp'] ?? 'time pending' }}</span>
                    </div>
                    <p>{{ $event['summary'] ?? 'No summary available.' }}</p>
                    <div class="chat-meta">
                        <span>{{ $event['stream'] ?? 'Live Chat View' }}</span>
                        <span>{{ $event['risk_status'] ?? 'guarded' }}</span>
                        <span>{{ $event['result'] ?? 'observed' }}</span>
                    </div>
                    @if(!empty($event['next_action']))
                        <p class="muted" style="margin-top:8px">{{ $event['next_action'] }}</p>
                    @endif
                </article>
            @empty
                <p class="empty">No events match the current filters.</p>
            @endforelse
        </div>
    </section>
</section>
@endsection
