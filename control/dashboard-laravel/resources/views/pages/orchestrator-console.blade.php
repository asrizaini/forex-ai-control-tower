@extends('layouts.control', [
    'title' => 'Orchestrator Console',
    'description' => 'Compact real-time operator-to-orchestrator chat. This lane only shows Operator and Orchestrator Agent messages.',
    'eyebrow' => 'Operator Console',
])

@section('content')
@php
    $consoleEvents = array_reverse($events['events'] ?? []);
    $provider = $orchestratorHealth['provider'] ?? [];
    $activeProvider = strtoupper((string)($provider['active_provider'] ?? 'local'));
    $providerMode = strtoupper((string)($provider['mode'] ?? 'local'));
    $localStatus = (string)(($provider['providers']['local']['status'] ?? 'unknown'));
    $localModel = (string)(($provider['providers']['local']['model'] ?? 'n/a'));
    $localStyle = (string)(($provider['providers']['local']['api_style'] ?? 'ollama'));
    $lastFailedReason = (string)($orchestratorHealth['last_failed_reason'] ?? '');
    $lastLatency = $orchestratorHealth['last_latency_ms'] ?? null;
    $quickPrompts = [
        'What is the current time and date?',
        'What is the system status and what should we do next?',
        'Summarize today risk posture for demo trading.',
        'What is blocking controlled demo trading activation?',
        'Explain how the control tower should operate safely.',
    ];
@endphp
<style>
    .console-shell{background:#0d1117;border:1px solid #21262d;border-radius:8px;color:#e6edf3;display:grid;gap:0}
    .console-topline{align-items:center;background:#161b22;border-bottom:1px solid #21262d;display:flex;gap:10px;padding:10px 16px}
    .console-topline h2{font-size:15px;margin:0}
    .console-topline .badge{background:#238636;border-radius:999px;color:#fff;font-size:11px;font-weight:600;padding:2px 8px}
    .console-topline .spacer{flex:1}
    .console-topline .pill{background:#0d1117;border:1px solid #30363d;border-radius:999px;color:#8b949e;font-size:12px;padding:4px 10px;display:flex;align-items:center;gap:6px}
    .console-topline .pill .dot{width:7px;height:7px;border-radius:50%}
    .console-topline .pill .dot.ok{background:#238636}
    .console-topline .pill .dot.warn{background:#d29922}
    .console-topline .pill .dot.err{background:#f85149}
    .console-controls{align-items:center;display:flex;flex-wrap:wrap;gap:8px;padding:8px 16px;background:#161b22;border-bottom:1px solid #21262d}
    .console-controls select{background:#0d1117;border-color:#30363d;color:#e6edf3;width:auto;font-size:12px;padding:3px 6px}
    .console-grid{display:grid;gap:0;grid-template-columns:minmax(280px,360px) minmax(0,1fr)}
    .composer-dark{background:#161b22;border-right:1px solid #21262d;display:grid;gap:10px;padding:14px;overflow-y:auto}
    .composer-dark h3{font-size:14px;margin:0}
    .composer-dark p{color:#8b949e;font-size:12px;line-height:1.4;margin:0}
    .composer-dark label{color:#8b949e;display:flex;flex-direction:column;gap:4px;font-size:12px}
    .composer-dark select,.composer-dark textarea{background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#e6edf3;font:inherit;padding:8px 10px}
    .composer-dark textarea{min-height:90px;resize:vertical}
    .composer-dark select:focus,.composer-dark textarea:focus{border-color:#1f6feb;outline:none}
    .prompt-strip{display:flex;flex-wrap:wrap;gap:6px}
    .prompt-strip button{background:#21262d;border:1px solid #30363d;border-radius:6px;color:#e6edf3;cursor:pointer;font-size:12px;padding:6px 10px;text-align:left;transition:background .15s;white-space:normal}
    .prompt-strip button:hover{background:#30363d}
    .btn-send{background:#1f6feb;border:none;border-radius:6px;color:#fff;cursor:pointer;font-weight:600;padding:10px;text-align:center;transition:background .15s;width:100%}
    .btn-send:hover{background:#388bfd}
    .btn-send:disabled{opacity:.5;cursor:not-allowed}
    .console-feed{background:#0d1117;display:flex;flex-direction:column;max-height:calc(100vh - 200px);min-height:400px;overflow-y:auto}
    .console-row{border-bottom:1px solid #21262d;display:grid;gap:10px;grid-template-columns:140px minmax(0,1fr) auto;padding:10px 16px;transition:background .15s}
    .console-row.operator{background:#0d2818}
    .console-row.orchestrator{background:#0d1b2a}
    .console-row:hover{background:#161b22}
    .console-agent{color:#58a6ff;font-weight:600;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .console-room{color:#8b949e;font-size:11px;margin-top:2px}
    .console-summary{color:#e6edf3;font-size:13px;line-height:1.4}
    .console-next{color:#8b949e;font-size:12px;line-height:1.35;margin-top:4px}
    .console-time{color:#8b949e;font-size:11px;text-align:right;white-space:nowrap}
    .console-tags{display:flex;flex-wrap:wrap;gap:4px;justify-content:flex-end;margin-top:4px}
    .console-tags span{border-radius:999px;font-size:10px;padding:2px 6px}
    .console-tags .tag-ok{background:#0d2818;border:1px solid #23863633;color:#7ee787}
    .console-tags .tag-warn{background:#2d1f00;border:1px solid #d2992233;color:#d29922}
    .console-tags .tag-bad{background:#2d0a0a;border:1px solid #f8514933;color:#f85149}
    .console-tags .tag-neutral{background:#161b22;border:1px solid #30363d;color:#8b949e}
    .empty-dark{color:#8b949e;padding:40px;text-align:center}
    .console-footer{background:#161b22;border-top:1px solid #21262d;color:#8b949e;font-size:12px;padding:6px 16px}
    @media(max-width:768px){.console-grid{grid-template-columns:1fr}.console-row{grid-template-columns:1fr}.console-time{text-align:left}.console-tags{justify-content:flex-start}.console-feed{max-height:none}.composer-dark{border-right:none;border-bottom:1px solid #21262d}}
</style>

<section class="console-shell" data-feed-url="{{ route('orchestrator-console.feed') }}">
    <section class="console-topline">
        <h2>Orchestrator Console</h2>
        <span class="badge">Ollama</span>
        <div class="spacer"></div>
        <div class="pill"><span class="dot {{ $localStatus === 'ready' ? 'ok' : 'err' }}"></span>{{ $localModel }} · {{ $localStyle }}</div>
        <a class="button secondary small" href="{{ route('dashboard.agent-theater') }}">Agent Theater</a>
    </section>

    <section class="console-grid">
        <aside class="composer-dark">
            <div>
                <h3>Talk To Orchestrator</h3>
                <p>Read-only governed chat. No trade execution or approval bypass. Powered by local Ollama LLM.</p>
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
                    <textarea id="orchestrator-message" name="message" placeholder="Ask about time, system status, risk, MT5 bridge, strategies, deployment..."></textarea>
                </label>
                <button id="sendButton" type="submit" class="btn-send" {{ $authenticated ? '' : 'disabled' }}>Send To Orchestrator</button>
            </form>
            <div class="prompt-strip">
                @foreach($quickPrompts as $prompt)
                    <button type="button" class="prompt-button" data-prompt="{{ $prompt }}">{{ $prompt }}</button>
                @endforeach
            </div>
        </aside>

        <div id="consoleFeed" class="console-feed"></div>
    </section>

    <div class="console-footer" id="chatStatus">{{ $authenticated ? 'Ready. Chat cannot bypass approvals, Risk Manager, or Execution Guard.' : 'Login required to send messages.' }}</div>
</section>

<script>
    const initialEvents = @json($consoleEvents);
    const feedUrl = document.querySelector('.console-shell').dataset.feedUrl;
    const feedEl = document.getElementById('consoleFeed');
    const chatStatusEl = document.getElementById('chatStatus');
    const sendButton = document.getElementById('sendButton');
    let refreshTimer = null;
    let sending = false;

    function esc(v) { return String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
    function riskClass(r) { const s=String(r||'').toLowerCase(); return s.includes('blocked')||s.includes('halt')||s.includes('safe_mode')?'bad':s.includes('waiting')||s.includes('manual')||s.includes('review')?'warn':'ok'; }

    function klNowLabel() {
        return new Date().toLocaleString('en-US',{timeZone:'Asia/Kuala_Lumpur',hour12:true,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'})+' GMT+8';
    }

    function formatTimestamp(value) {
        if(!value) return '';
        if(String(value).includes('GMT+8')) return value;
        const p=new Date(value);
        if(Number.isNaN(p.getTime())) return value;
        return p.toLocaleString('en-US',{timeZone:'Asia/Kuala_Lumpur',hour12:true,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'})+' GMT+8';
    }

    function renderFeed(events) {
        if(!events.length) { feedEl.innerHTML='<div class="empty-dark">No orchestrator messages yet.</div>'; return; }
        feedEl.innerHTML = events.map(event => {
            const isOp = event.agent === 'Operator';
            const agent = event.agent === 'Orchestrator Agent' ? 'Orchestrator' : (event.agent || 'Agent');
            const risk = event.display?.risk_status || event.risk_status || 'read_only';
            const rc = riskClass(risk);
            return `<article class="console-row ${isOp?'operator':'orchestrator'}">
                <div><div class="console-agent" title="${esc(event.agent||'Agent')}">${esc(agent)}</div><div class="console-room">${esc(event.stream||'Orchestrator Console')}</div></div>
                <div><div class="console-summary">${esc(event.display?.summary||event.summary||'No summary available.')}</div>${event.next_action?`<div class="console-next">${esc(event.next_action)}</div>`:''}</div>
                <div><div class="console-time">${esc(formatTimestamp(event.timestamp||''))}</div><div class="console-tags"><span class="tag-${rc}">${esc(risk)}</span><span class="tag-neutral">${esc(event.result||'safe_reply')}</span></div></div>
            </article>`;
        }).join('');
    }

    async function fetchWithTimeout(url, options={}, timeoutMs=12000) {
        const c=new AbortController(); const t=setTimeout(()=>c.abort(),timeoutMs);
        try { return await fetch(url,{...options,signal:c.signal}); } finally { clearTimeout(t); }
    }

    async function refreshFeed() {
        try {
            const r = await fetchWithTimeout(feedUrl,{headers:{'Accept':'application/json'}},8000);
            if(!r.ok) throw new Error('Feed refresh failed');
            const b = await r.json();
            renderFeed([...(b.events||[])].reverse());
        } catch(e) { /* silent */ }
    }

    function scheduleRefresh() {
        if(refreshTimer) clearInterval(refreshTimer);
        const sel = document.getElementById('refreshRate');
        if(!sel) return;
        const ms = Number(sel.value);
        if(ms>0) refreshTimer = setInterval(()=>refreshFeed(), ms);
    }

    document.querySelectorAll('[data-prompt]').forEach(b => b.addEventListener('click',()=>{const box=document.getElementById('orchestrator-message');box.value=b.dataset.prompt;box.focus();}));
    document.getElementById('orchestratorForm').addEventListener('submit', async (event) => {
        event.preventDefault();
        if(sending) return;
        sending = true;
        sendButton.disabled = true;
        chatStatusEl.textContent = 'Sending...';
        try {
            const opts = {method:'POST',headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest'},body:new FormData(event.currentTarget),credentials:'same-origin'};
            let response;
            try { response = await fetchWithTimeout(event.currentTarget.action, opts, 15000); }
            catch(err) {
                if(err&&err.name==='AbortError') { chatStatusEl.textContent='Orchestrator timeout. Retrying...'; response=await fetchWithTimeout(event.currentTarget.action,opts,15000); }
                else throw err;
            }
            if(!response.ok) {
                let msg='Send failed. Check login session.';
                try { const b=await response.json(); if(b&&typeof b.message==='string'&&b.message.trim()) msg=b.message; } catch(_){}
                chatStatusEl.textContent=msg; return;
            }
            const body = await response.json().catch(()=>({}));
            event.currentTarget.reset();
            const provider = typeof body.provider==='string'&&body.provider?body.provider:'local';
            const lat = Number.isFinite(Number(body.latency_ms))?` in ${Number(body.latency_ms)}ms`:'';
            chatStatusEl.textContent = `Orchestrator replied via ${provider}${lat}.`;
            await refreshFeed();
        } catch(_e) { chatStatusEl.textContent='Send failed. Orchestrator is unavailable or timed out.'; }
        finally { sending=false; sendButton.disabled=false; }
    });
    renderFeed(initialEvents);
    scheduleRefresh();
</script>
@endsection
