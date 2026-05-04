@extends('layouts.control', [
    'title' => 'Agent Theater / Orchestrator Console',
    'description' => 'Human-readable agent room and safe operator chat for orchestration, diagnostics, and governed task routing.',
    'eyebrow' => 'AI Trading Room',
])

@section('content')
@php
    $theaterEvents = array_reverse($events['events'] ?? []);
    $roomModes = $modes['modes'] ?? ($events['modes'] ?? []);
    $quickPrompts = [
        'What is the current time and date?',
        'What is the system status and what should we do next?',
        'Summarize today risk posture for demo trading.',
        'Ask the Market Data Agent what data is stale.',
        'What is blocking controlled demo trading activation?',
    ];
@endphp
<style>
    .theater-layout{display:grid;gap:14px;grid-template-columns:360px minmax(0,1fr)}
    .chat-feed{background:#101820;border:1px solid #243244;border-radius:8px;display:grid;gap:10px;max-height:720px;overflow:auto;padding:14px}
    .chat-bubble{background:#f8fafc;border:1px solid #dfe7f0;border-radius:8px;padding:12px}
    .chat-bubble.operator{background:#e8f5f2;border-color:#b6ded6}
    .chat-bubble.orchestrator{background:#101820;border-color:#324256;color:#eef6ff}
    .chat-bubble.orchestrator p,.chat-bubble.orchestrator .muted{color:#aab8c8}
    .chat-top{align-items:center;display:flex;gap:10px;justify-content:space-between;margin-bottom:6px}
    .chat-agent{font-weight:860}
    .chat-time{color:#718096;font-size:12px;white-space:nowrap}
    .chat-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
    .chat-meta span{border:1px solid #d8e1eb;border-radius:999px;color:#53657b;font-size:12px;padding:4px 8px}
    .chat-bubble.orchestrator .chat-meta span{border-color:#34465a;color:#b8c5d3}
    .prompt-list{display:grid;gap:8px}
    .prompt-button{justify-content:flex-start;text-align:left;white-space:normal}
    @media(max-width:1050px){.theater-layout{grid-template-columns:1fr}.chat-feed{max-height:none}}
</style>

<section class="grid-3">
    <div class="metric"><span class="eyebrow">Theater Mode</span><strong>Live Chat</strong><p>Human-readable summaries only. No hidden reasoning or secrets.</p></div>
    <div class="metric"><span class="eyebrow">Operator Timezone</span><strong>MYT</strong><p>Dashboard-facing timestamps use Asia/Kuala_Lumpur.</p></div>
    <div class="metric"><span class="eyebrow">Safety</span><strong>Guarded</strong><p>Chat cannot bypass Risk Manager, approvals, or Execution Guard.</p></div>
</section>

<section class="theater-layout">
    <aside class="stack">
        <section class="panel">
            <div class="panel-head">
                <div><h2>Talk To Orchestrator</h2><p>Ask general questions or route safe system work to agents.</p></div>
                <span class="badge {{ $authenticated ? 'ok' : 'warn' }}">{{ $authenticated ? 'ready' : 'login required' }}</span>
            </div>
            <form class="stack" method="POST" action="{{ route('agent-theater.chat') }}">
                @csrf
                <label>Language
                    <select name="language">
                        <option value="en">English</option>
                        <option value="ms-MY">Bahasa Melayu Malaysia</option>
                        <option value="auto">Auto</option>
                    </select>
                </label>
                <label>Message
                    <textarea id="orchestrator-message" name="message" placeholder="Ask about system status, current time, risk posture, MT5 bridge, data freshness, strategies, or general questions."></textarea>
                </label>
                <button type="submit" {{ $authenticated ? '' : 'disabled' }}>Send To Orchestrator</button>
            </form>
        </section>

        <section class="panel">
            <div class="panel-head"><div><h2>Quick Prompts</h2><p>Click one, then send.</p></div></div>
            <div class="prompt-list">
                @foreach($quickPrompts as $prompt)
                    <button type="button" class="secondary prompt-button" data-prompt="{{ $prompt }}">{{ $prompt }}</button>
                @endforeach
            </div>
        </section>

        <section class="panel">
            <div class="panel-head"><div><h2>Rooms</h2><p>Available presentation modes.</p></div></div>
            <div class="stack">
                @forelse($roomModes as $mode)
                    <div class="masked">
                        <strong>{{ $mode['name'] ?? $mode }}</strong>
                        @if(is_array($mode) && !empty($mode['description']))<p>{{ $mode['description'] }}</p>@endif
                    </div>
                @empty
                    <p class="empty">No room metadata is available yet.</p>
                @endforelse
            </div>
        </section>
    </aside>

    <section class="panel">
        <div class="panel-head">
            <div><h2>Live Agent Feed</h2><p>Recent orchestrator, worker, and agent messages in chatroom style.</p></div>
            <a class="button secondary" href="{{ $links['api'] }}/api/v1/agent-theater/console" target="_blank" rel="noreferrer">Standalone Console</a>
        </div>
        <div class="chat-feed">
            @forelse($theaterEvents as $event)
                @php
                    $agent = $event['agent'] ?? 'Agent';
                    $bubbleClass = $agent === 'Operator' ? 'operator' : (str_contains($agent, 'Orchestrator') ? 'orchestrator' : '');
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
                <p class="empty">No Agent Theater events yet. Send a message to the orchestrator after login.</p>
            @endforelse
        </div>
    </section>
</section>

<script>
    document.querySelectorAll('[data-prompt]').forEach((button) => {
        button.addEventListener('click', () => {
            const box = document.getElementById('orchestrator-message');
            box.value = button.dataset.prompt;
            box.focus();
        });
    });
</script>
@endsection
