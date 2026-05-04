@extends('layouts.control', [
    'title' => 'Orchestrator Console',
    'description' => 'Compact real-time operator-to-orchestrator chat. This lane only shows Operator and Orchestrator Agent messages.',
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
    .console-shell{background:#0f1720;border:1px solid #233044;border-radius:8px;color:#d9e5f2;display:grid;gap:12px;padding:14px}
    .console-topline{align-items:center;display:flex;gap:10px;justify-content:space-between}
    .console-controls{align-items:center;display:flex;flex-wrap:wrap;gap:8px}
    .console-controls select{background:#111c29;border-color:#304158;color:#e7eef7;width:auto}
    .console-grid{display:grid;gap:12px;grid-template-columns:minmax(280px,380px) minmax(0,1fr)}
    .composer-dark{background:#111c29;border:1px solid #304158;border-radius:8px;display:grid;gap:10px;padding:12px}
    .composer-dark label{color:#96a6ba}
    .composer-dark select,.composer-dark textarea{background:#0b1119;border-color:#304158;color:#e7eef7}
    .prompt-strip{display:flex;flex-wrap:wrap;gap:6px}
    .prompt-strip button{background:#162233;border-color:#2d4058;color:#cfdae8;font-size:12px;min-height:30px;padding:5px 8px;white-space:normal}
    .console-feed{background:#0b1119;border:1px solid #233044;border-radius:8px;display:grid;max-height:calc(100vh - 350px);min-height:500px;overflow:auto}
    .console-row{border-bottom:1px solid #1c2a3a;display:grid;gap:10px;grid-template-columns:220px minmax(0,1fr) 170px;padding:9px 12px}
    .console-row.operator{background:#10221f}
    .console-row.orchestrator{background:#101822}
    .console-row:hover{background:#132031}
    .console-agent{color:#76e1cd;font-weight:850;line-height:1.2}
    .console-room{color:#8fa3ba;font-size:12px;margin-top:2px}
    .console-summary{color:#e6edf6;font-size:13px;line-height:1.35}
    .console-next{color:#9fb0c4;font-size:12px;line-height:1.35;margin-top:3px}
    .console-time{color:#91a4b8;font-size:11px;text-align:right;white-space:nowrap}
    .console-tags{display:flex;flex-wrap:wrap;gap:5px;justify-content:flex-end;margin-top:5px}
    .console-tags span{background:#121f2d;border:1px solid #293b52;border-radius:999px;color:#a9b8ca;font-size:10px;padding:3px 6px}
    .empty-dark{color:#91a4b8;padding:28px;text-align:center}
    @media(max-width:1050px){.console-grid{grid-template-columns:1fr}.console-row{grid-template-columns:1fr}.console-time{text-align:left}.console-tags{justify-content:flex-start}.console-feed{max-height:none}}
</style>

<section class="console-shell" data-feed-url="{{ route('orchestrator-console.feed') }}">
    <div class="console-topline">
        <div><strong id="visibleCount">{{ count($consoleEvents) }}</strong> messages · <span id="lastUpdated">loaded</span></div>
        <div class="console-controls">
            <label>Refresh
                <select id="refreshRate">
                    <option value="1000">1 second</option>
                    <option value="2000" selected>2 seconds</option>
                    <option value="5000">5 seconds</option>
                    <option value="10000">10 seconds</option>
                    <option value="0">Paused</option>
                </select>
            </label>
            <button class="secondary small" type="button" id="refreshNow">Refresh</button>
            <a class="button secondary small" href="{{ route('dashboard.agent-theater') }}">Agent Theater</a>
        </div>
    </div>

    <section class="console-grid">
        <aside class="composer-dark">
            <div>
                <h2>Talk To Orchestrator</h2>
                <p>Read-only governed chat. No trade execution or approval bypass.</p>
            </div>
            <form id="orchestratorForm" class="stack" method="POST" action="{{ route('agent-theater.chat') }}">
                @csrf
                <label>Language
                    <select name="language">
                        <option value="en">English</option>
                        <option value="ms-MY">Bahasa Melayu Malaysia</option>
                        <option value="auto">Auto</option>
                    </select>
                </label>
                <label>Message
                    <textarea id="orchestrator-message" name="message" placeholder="Ask about time, system status, risk, MT5 bridge, strategies, deployment, or general questions."></textarea>
                </label>
                <button id="sendButton" type="submit" {{ $authenticated ? '' : 'disabled' }}>Send</button>
            </form>
            <div class="prompt-strip">
                @foreach($quickPrompts as $prompt)
                    <button type="button" class="secondary prompt-button" data-prompt="{{ $prompt }}">{{ $prompt }}</button>
                @endforeach
            </div>
            <p class="muted" id="chatStatus">{{ $authenticated ? 'Ready.' : 'Login required to send messages.' }}</p>
        </aside>

        <div id="consoleFeed" class="console-feed"></div>
    </section>
</section>

<script>
    const initialEvents = @json($consoleEvents);
    const feedUrl = document.querySelector('.console-shell').dataset.feedUrl;
    const feedEl = document.getElementById('consoleFeed');
    const refreshRateEl = document.getElementById('refreshRate');
    const countEl = document.getElementById('visibleCount');
    const lastUpdatedEl = document.getElementById('lastUpdated');
    const chatStatusEl = document.getElementById('chatStatus');
    const sendButton = document.getElementById('sendButton');
    let refreshTimer = null;
    let sending = false;

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    }

    function renderFeed(events) {
        countEl.textContent = events.length;
        if (!events.length) {
            feedEl.innerHTML = '<div class="empty-dark">No orchestrator messages yet.</div>';
            return;
        }
        feedEl.innerHTML = events.map((event) => {
            const isOperator = event.agent === 'Operator';
            const agentLabel = event.agent === 'Orchestrator Agent' ? 'Orchestrator' : (event.agent || 'Agent');
            return `
                <article class="console-row ${isOperator ? 'operator' : 'orchestrator'}">
                    <div><div class="console-agent" title="${escapeHtml(event.agent || 'Agent')}">${escapeHtml(agentLabel)}</div><div class="console-room">${escapeHtml(event.stream || 'Orchestrator Console')}</div></div>
                    <div><div class="console-summary">${escapeHtml(event.display?.summary || event.summary || 'No summary available.')}</div>${event.next_action ? `<div class="console-next">${escapeHtml(event.next_action)}</div>` : ''}</div>
                    <div><div class="console-time">${escapeHtml(event.timestamp || '')}</div><div class="console-tags"><span>${escapeHtml(event.display?.risk_status || event.risk_status || 'read_only')}</span><span>${escapeHtml(event.result || 'safe_reply')}</span></div></div>
                </article>
            `;
        }).join('');
    }

    async function refreshFeed() {
        const response = await fetch(feedUrl, {headers: {'Accept': 'application/json'}});
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

    document.querySelectorAll('[data-prompt]').forEach((button) => {
        button.addEventListener('click', () => {
            const box = document.getElementById('orchestrator-message');
            box.value = button.dataset.prompt;
            box.focus();
        });
    });
    document.getElementById('refreshNow').addEventListener('click', () => refreshFeed().catch(() => { lastUpdatedEl.textContent = 'refresh failed'; }));
    refreshRateEl.addEventListener('change', scheduleRefresh);
    document.getElementById('orchestratorForm').addEventListener('submit', async (event) => {
        event.preventDefault();
        if (sending) return;
        sending = true;
        sendButton.disabled = true;
        chatStatusEl.textContent = 'Sending...';
        try {
            const response = await fetch(event.currentTarget.action, {
                method: 'POST',
                headers: {'Accept':'application/json', 'X-Requested-With':'XMLHttpRequest'},
                body: new FormData(event.currentTarget),
                credentials: 'same-origin',
            });
            if (!response.ok) {
                chatStatusEl.textContent = 'Send failed. Check login session.';
                return;
            }
            event.currentTarget.reset();
            chatStatusEl.textContent = 'Orchestrator replied.';
            await refreshFeed();
        } finally {
            sending = false;
            sendButton.disabled = false;
        }
    });
    renderFeed(initialEvents);
    scheduleRefresh();
</script>
@endsection
