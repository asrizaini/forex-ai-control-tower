@extends('layouts.control', [
    'title' => 'Orchestrator Console',
    'description' => 'Dedicated operator-to-orchestrator chat. This lane only displays Operator and Orchestrator Agent messages.',
    'eyebrow' => 'Operator Console',
])

@section('content')
@php
    $consoleEvents = array_reverse($events['events'] ?? []);
    $quickPrompts = [
        'What is the current time and date?',
        'What is the system status and what should we do next?',
        'Summarize today risk posture for demo trading.',
        'What is blocking controlled demo trading activation?',
        'Explain how the control tower should operate safely.',
    ];
@endphp
<style>
    .console-layout{display:grid;gap:14px;grid-template-columns:360px minmax(0,1fr)}
    .console-feed{background:#101820;border:1px solid #243244;border-radius:8px;display:grid;gap:10px;max-height:760px;overflow:auto;padding:14px}
    .console-bubble{border:1px solid #304155;border-radius:8px;padding:12px}
    .console-bubble.operator{background:#17352f;color:#f2fffb}
    .console-bubble.orchestrator{background:#111b26;color:#eef6ff}
    .console-top{align-items:center;display:flex;gap:10px;justify-content:space-between;margin-bottom:6px}
    .console-agent{color:#7ee2ce;font-weight:860}
    .console-time{color:#aab8c8;font-size:12px;white-space:nowrap}
    .console-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
    .console-meta span{border:1px solid #34465a;border-radius:999px;color:#b8c5d3;font-size:12px;padding:4px 8px}
    .prompt-list{display:grid;gap:8px}
    .prompt-button{justify-content:flex-start;text-align:left;white-space:normal}
    @media(max-width:1050px){.console-layout{grid-template-columns:1fr}.console-feed{max-height:none}}
</style>

<section class="grid-3">
    <div class="metric"><span class="eyebrow">Conversation</span><strong>1:1</strong><p>Operator and Orchestrator Agent only.</p></div>
    <div class="metric"><span class="eyebrow">Timezone</span><strong>MYT</strong><p>Replies use Asia/Kuala_Lumpur time.</p></div>
    <div class="metric"><span class="eyebrow">Safety</span><strong>Read Only</strong><p>Chat cannot execute trades or bypass approvals.</p></div>
</section>

<section class="console-layout">
    <aside class="stack">
        <section class="panel">
            <div class="panel-head">
                <div><h2>Talk To Orchestrator</h2><p>Ask general questions or request safe task routing.</p></div>
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
                    <textarea id="orchestrator-message" name="message" placeholder="Ask about current time, system status, risk, MT5 bridge, strategies, deployment, or general questions."></textarea>
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
    </aside>

    <section class="panel">
        <div class="panel-head">
            <div><h2>Operator Conversation</h2><p>Isolated from the multi-agent broadcast feed.</p></div>
            <a class="button secondary" href="{{ route('dashboard.agent-theater') }}">Open Agent Theater</a>
        </div>
        <div class="console-feed">
            @forelse($consoleEvents as $event)
                @php
                    $agent = $event['agent'] ?? 'Agent';
                    $bubbleClass = $agent === 'Operator' ? 'operator' : 'orchestrator';
                @endphp
                <article class="console-bubble {{ $bubbleClass }}">
                    <div class="console-top">
                        <span class="console-agent">{{ $agent }}</span>
                        <span class="console-time">{{ $event['timestamp'] ?? 'time pending' }}</span>
                    </div>
                    <p>{{ $event['summary'] ?? 'No summary available.' }}</p>
                    <div class="console-meta">
                        <span>{{ $event['risk_status'] ?? 'read_only_no_trade_execution' }}</span>
                        <span>{{ $event['result'] ?? 'safe_reply' }}</span>
                    </div>
                    @if(!empty($event['next_action']))
                        <p class="muted" style="margin-top:8px">{{ $event['next_action'] }}</p>
                    @endif
                </article>
            @empty
                <p class="empty">No dedicated orchestrator messages yet. Send a message after login.</p>
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
