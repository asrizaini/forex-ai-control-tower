@extends('layouts.control', ['title' => 'OpenClaw Gateway', 'description' => 'Governed human-facing assistant bridge. No direct MT5 execution, no risk bypass, no unrestricted shell access.'])

@section('content')
@php
    $gatewayEnabled = (bool)($status['enabled'] ?? false);
    $runtimeConfigured = (bool)($status['runtime_configured'] ?? false);
    $bridgeState = $runtimeConfigured ? 'configured' : 'not configured';
    $runtimeProbeOk = (bool)(($runtimeHealth['runtime_probe']['ok'] ?? false));
    $result = session('openclaw_result', []);
@endphp

<div class="grid-4" data-live-section="openclaw-metrics">
    <div class="metric {{ $gatewayEnabled ? 'status-ok' : 'status-warn' }}">
        <span class="eyebrow">Gateway</span>
        <strong>{{ $gatewayEnabled ? 'enabled' : 'disabled' }}</strong>
        <p>OPENCLAW_ENABLED policy state</p>
    </div>
    <div class="metric {{ $runtimeConfigured ? 'status-ok' : 'status-warn' }}">
        <span class="eyebrow">Runtime Adapter</span>
        <strong>{{ $bridgeState }}</strong>
        <p>External OpenClaw runtime endpoint</p>
    </div>
    <div class="metric status-ok">
        <span class="eyebrow">Trade Execution</span>
        <strong>forbidden</strong>
        <p>OpenClaw cannot execute MT5 orders</p>
    </div>
    <div class="metric status-ok">
        <span class="eyebrow">Safety</span>
        <strong>governed</strong>
        <p>Only approved human-facing actions</p>
    </div>
</div>

<div class="grid-3" data-live-section="openclaw-runtime-health">
    <div class="metric {{ $runtimeProbeOk ? 'status-ok' : 'status-warn' }}">
        <span class="eyebrow">Runtime Probe</span>
        <strong>{{ $runtimeProbeOk ? 'reachable' : 'degraded' }}</strong>
        <p>GET /health on OpenClaw runtime adapter</p>
    </div>
    <div class="metric status-ok">
        <span class="eyebrow">Allowed Targets</span>
        <strong>{{ count($contract['allowed_status_query_targets'] ?? []) }}</strong>
        <p>status query domains</p>
    </div>
    <div class="metric status-ok">
        <span class="eyebrow">Approved API Paths</span>
        <strong>{{ count($contract['allowed_approved_api_paths'] ?? []) }}</strong>
        <p>read-only bridge endpoints</p>
    </div>
</div>

<div class="panel stack">
    <div class="panel-head">
        <div>
            <h2>Allowed Actions</h2>
            <p>These actions are constrained and audited.</p>
        </div>
        <span class="badge ok">policy enforced</span>
    </div>
    <div class="grid-4">
        @foreach(($status['allowed_actions'] ?? []) as $action)
            <span class="badge ok">{{ $action }}</span>
        @endforeach
    </div>
    <div class="panel-head" style="margin-top:8px;">
        <div>
            <h2>Forbidden Actions</h2>
            <p>Hard-blocked even if OpenClaw is enabled.</p>
        </div>
        <span class="badge bad">blocked</span>
    </div>
    <div class="grid-3">
        @foreach(($status['forbidden_actions'] ?? []) as $action)
            <span class="badge bad">{{ $action }}</span>
        @endforeach
    </div>
</div>

<div class="grid-2">
    <div class="panel stack">
        <div class="panel-head"><div><h2>Chat With OpenClaw</h2><p>Human-facing chat only. Replies are safe summaries.</p></div><span class="badge warn">no trade ops</span></div>
        <form method="POST" action="{{ route('openclaw.chat') }}" class="stack">
            @csrf
            <div class="grid-3">
                <label>Role
                    <select name="role">
                        <option value="admin">admin</option>
                        <option value="user">user</option>
                    </select>
                </label>
                <label>Language
                    <select name="language">
                        <option value="en">English</option>
                        <option value="ms-MY">Bahasa Melayu Malaysia</option>
                        <option value="auto">Auto</option>
                    </select>
                </label>
            </div>
            <label>Message<textarea name="message" placeholder="Ask status, risk posture, signals, workers, or daily summary." required></textarea></label>
            <div class="step-actions"><button type="submit">Send Chat</button></div>
        </form>
    </div>

    <div class="panel stack">
        <div class="panel-head"><div><h2>Status Query</h2><p>Generate a scoped safe summary by domain.</p></div><span class="badge ok">read-only</span></div>
        <form method="POST" action="{{ route('openclaw.status-query') }}" class="stack">
            @csrf
            <div class="grid-2">
                <label>Target
                    <select name="target">
                        @foreach($allowedTargets as $target)
                            <option value="{{ $target }}">{{ $target }}</option>
                        @endforeach
                    </select>
                </label>
                <label>Language
                    <select name="language">
                        <option value="en">English</option>
                        <option value="ms-MY">Bahasa Melayu Malaysia</option>
                        <option value="auto">Auto</option>
                    </select>
                </label>
            </div>
            <div class="step-actions">
                <button type="submit">Run Status Query</button>
            </div>
        </form>

        <form method="POST" action="{{ route('openclaw.daily-summary') }}" class="stack">
            @csrf
            <div class="grid-2">
                <label>Daily summary language
                    <select name="language">
                        <option value="en">English</option>
                        <option value="ms-MY">Bahasa Melayu Malaysia</option>
                        <option value="auto">Auto</option>
                    </select>
                </label>
            </div>
            <div class="step-actions">
                <button type="submit" class="secondary">Generate Daily Summary</button>
            </div>
        </form>
    </div>
</div>

<div class="panel stack">
    <div class="panel-head"><div><h2>Approved API Bridge</h2><p>Super-admin only. Limited whitelist for read-only control-plane endpoints.</p></div><span class="badge warn">approval required</span></div>
    <form method="POST" action="{{ route('openclaw.api-call') }}" class="stack">
        @csrf
        <div class="grid-2">
            <label>Whitelisted API path
                <select name="path">
                    @foreach($allowedPaths as $path)
                        <option value="{{ $path }}">{{ $path }}</option>
                    @endforeach
                </select>
            </label>
            <label>Reason<input name="reason" maxlength="300" placeholder="Why this approved bridge call is needed"></label>
        </div>
        <div class="step-actions"><button type="submit" class="secondary">Execute Approved API Call</button></div>
    </form>
</div>

@if(!empty($result))
<div class="panel stack">
    <div class="panel-head"><div><h2>Last OpenClaw Result</h2><p>Most recent response from OpenClaw gateway action.</p></div><span class="badge ok">latest</span></div>
    <div class="masked"><pre style="margin:0;white-space:pre-wrap;">{{ json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) }}</pre></div>
</div>
@endif
@endsection
