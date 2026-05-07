@extends('layouts.control', [
    'title' => 'Credentials & Secrets',
    'description' => 'Manage API keys, tokens, passwords, and integration settings. All values are encrypted at rest.',
    'eyebrow' => 'Configuration',
])

@section('content')
@php
    $pending = session('pending_generated_credential');
    $revealed = session('generated_secret');
    $categoryIcons = [
        'Core Runtime' => '⚙️',
        'Trading Safety' => '🛡️',
        'News' => '📰',
        'Notifications' => '🔔',
        'Mobile Push' => '📱',
        'OpenClaw' => '🤖',
        'MT5 Bridge' => '🌉',
        'Paid LLM' => '💰',
        'Auth And Recovery' => '🔐',
    ];
    $categoryOrder = ['Core Runtime', 'Auth And Recovery', 'Trading Safety', 'MT5 Bridge', 'OpenClaw', 'Paid LLM', 'News', 'Notifications', 'Mobile Push'];
    $orderedGroups = [];
    foreach ($categoryOrder as $cat) {
        if (!empty($credentialGroups[$cat])) {
            $orderedGroups[$cat] = $credentialGroups[$cat];
        }
    }
    foreach (($credentialGroups ?? []) as $cat => $items) {
        if (!isset($orderedGroups[$cat])) {
            $orderedGroups[$cat] = $items;
        }
    }
    $configuredCount = $credentials['configured_count'] ?? 0;
    $missingCount = count($credentials['missing_required'] ?? []);
    $invalidCount = count($credentials['invalid'] ?? []);
    $totalItems = array_sum(array_map('count', $orderedGroups));
@endphp
<style>
    .cred-shell{display:grid;gap:16px}
    .cred-summary{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}
    .cred-summary-card{background:rgba(15,26,43,.86);border:1px solid var(--line);border-radius:12px;padding:16px;display:grid;gap:4px}
    .cred-summary-card .num{font-size:28px;font-weight:800;line-height:1.1}
    .cred-summary-card .lbl{color:var(--muted);font-size:12px;font-weight:760;text-transform:uppercase;letter-spacing:.04em}
    .cred-category{background:rgba(15,26,43,.86);border:1px solid var(--line);border-radius:12px;overflow:hidden}
    .cred-category-head{align-items:center;background:#0b1829;border-bottom:1px solid var(--line);cursor:pointer;display:flex;gap:10px;padding:14px 18px;user-select:none}
    .cred-category-head:hover{background:#102036}
    .cred-category-icon{font-size:18px}
    .cred-category-title{font-size:15px;font-weight:800;flex:1}
    .cred-category-count{background:#122136;border:1px solid #2f4763;border-radius:999px;color:#b7c8dc;font-size:11px;font-weight:700;padding:3px 10px}
    .cred-category-body{display:grid;gap:0}
    .cred-item{border-bottom:1px solid #1a2b3f;display:grid;gap:10px;grid-template-columns:minmax(0,1fr) minmax(0,1fr) auto auto;padding:14px 18px;transition:background .12s}
    .cred-item:last-child{border-bottom:none}
    .cred-item:hover{background:rgba(20,34,53,.35)}
    .cred-item-name{font-weight:760;font-size:13px;line-height:1.3}
    .cred-item-key{color:var(--muted);font-size:11px;font-family:monospace}
    .cred-item-current{background:var(--soft);border:1px solid #29394d;border-radius:8px;font-family:monospace;font-size:12px;overflow:hidden;padding:8px 10px;text-overflow:ellipsis;white-space:nowrap}
    .cred-item-form{display:grid;gap:8px;grid-template-columns:minmax(0,1fr) auto;padding:10px 18px 14px;border-bottom:1px solid #1a2b3f;background:rgba(10,19,32,.5)}
    .cred-item-form input,.cred-item-form select{background:#0b1422;border:1px solid #2a3f5b;border-radius:8px;color:#e8eef6;font-size:13px;padding:8px 10px}
    .cred-item-form input:focus,.cred-item-form select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(32,201,174,.18);outline:none}
    .cred-item-actions{display:flex;gap:6px;align-items:center}
    .badge-sm{border-radius:999px;font-size:10px;font-weight:760;letter-spacing:.02em;padding:3px 8px;text-transform:uppercase}
    .badge-sm.ok{background:var(--okbg);color:var(--ok)}
    .badge-sm.warn{background:var(--warnbg);color:var(--warn)}
    .badge-sm.bad{background:var(--badbg);color:var(--bad)}
    .badge-sm.neutral{background:#122136;border:1px solid #2f4763;color:#8ca3be}
    .cred-actions-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
    .cred-notice{background:rgba(15,26,43,.86);border:1px solid var(--line);border-radius:12px;padding:16px 18px;display:grid;gap:8px}
    .cred-notice h3{font-size:15px;margin:0}
    .cred-notice p{color:var(--muted);font-size:13px;margin:0}
    @media(max-width:900px){.cred-item{grid-template-columns:1fr}.cred-item-form{grid-template-columns:1fr}.cred-summary{grid-template-columns:1fr 1fr}}
    @media(max-width:600px){.cred-summary{grid-template-columns:1fr}}
</style>

<section class="cred-shell">
    {{-- Summary Stats --}}
    <section class="cred-summary">
        <div class="cred-summary-card">
            <span class="num" style="color:var(--ok)">{{ $configuredCount }}</span>
            <span class="lbl">Configured</span>
        </div>
        <div class="cred-summary-card">
            <span class="num" style="color:{{ $missingCount > 0 ? 'var(--bad)' : 'var(--ok)' }}">{{ $missingCount }}</span>
            <span class="lbl">Missing Required</span>
        </div>
        <div class="cred-summary-card">
            <span class="num" style="color:{{ $invalidCount > 0 ? 'var(--warn)' : 'var(--ok)' }}">{{ $invalidCount }}</span>
            <span class="lbl">Invalid</span>
        </div>
        <div class="cred-summary-card">
            <span class="num">{{ $totalItems }}</span>
            <span class="lbl">Total Fields</span>
        </div>
    </section>

    {{-- Storage Model Notice --}}
    <section class="cred-notice">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
            <div>
                <h3>Encrypted Credential Store</h3>
                <p>All secrets are encrypted at rest using a service key file. Values are never written to audit logs. Runtime environment values sync automatically.</p>
            </div>
            @if($authenticated)
                <form method="POST" action="{{ route('credentials.migrate-runtime') }}">
                    @csrf
                    <button class="button secondary small" type="submit">Migrate Runtime Env → DB</button>
                </form>
            @endif
        </div>
    </section>

    {{-- Admin Security --}}
    @if($authenticated)
        <section class="cred-notice">
            <h3>Admin Password</h3>
            <form style="display:grid;gap:10px;grid-template-columns:minmax(0,1fr) minmax(0,1fr) auto;align-items:end" method="POST" action="{{ route('password.update') }}">
                @csrf
                <label style="gap:4px">New password<input name="password" type="password" autocomplete="new-password" minlength="12" required placeholder="Min 12 characters"></label>
                <label style="gap:4px">Confirm<input name="password_confirmation" type="password" autocomplete="new-password" minlength="12" required placeholder="Repeat password"></label>
                <button type="submit" style="align-self:end">Change Password</button>
            </form>
        </section>
    @endif

    {{-- Pending Generated Value --}}
    @if($pending)
        <section class="cred-notice" style="border-color:var(--warn)">
            <h3>⏳ Generated Value Pending Approval</h3>
            <p>{{ $pending['message'] }}</p>
            <div style="display:grid;gap:10px;grid-template-columns:1fr 1fr">
                <label style="gap:4px">Current {{ $pending['label'] ?? $pending['name'] }}<div class="cred-item-current">{{ $pending['current'] ?? 'not configured' }}</div></label>
                <label style="gap:4px">Generated<input id="pending-generated-secret" readonly value="{{ $pending['value'] }}" autocomplete="off" style="font-family:monospace"></label>
            </div>
            <div class="cred-actions-bar" style="margin-top:8px">
                <button class="secondary small" type="button" onclick="navigator.clipboard.writeText(document.getElementById('pending-generated-secret').value)">Copy Generated</button>
                <form method="POST" action="{{ route('credentials.apply-generated', $pending['name']) }}">@csrf<button type="submit">Apply Generated</button></form>
                <form method="POST" action="{{ route('credentials.discard-generated') }}">@csrf<button class="secondary small" type="submit">Discard</button></form>
            </div>
        </section>
    @endif

    {{-- Revealed Secret --}}
    @if($revealed)
        <section class="cred-notice" style="border-color:var(--warn)">
            <h3>🔓 Secret Revealed For This Session</h3>
            <p>{{ $revealed['message'] }}</p>
            <label style="gap:4px">{{ $revealed['name'] }}<input id="revealed-secret" readonly value="{{ $revealed['value'] }}" autocomplete="off" style="font-family:monospace"></label>
            <button class="secondary small" type="button" onclick="navigator.clipboard.writeText(document.getElementById('revealed-secret').value)" style="margin-top:4px">Copy</button>
        </section>
    @endif

    {{-- Credential Categories --}}
    @if(!$authenticated)
        <section class="cred-notice">
            <h3>Login Required</h3>
            <p>Sign in to view and manage credentials.</p>
        </section>
    @else
        @foreach($orderedGroups as $category => $items)
            @php
                $icon = $categoryIcons[$category] ?? '📁';
                $configuredInCat = 0;
                $requiredMissing = 0;
                foreach ($items as $item) {
                    if (!empty($item['configured'])) $configuredInCat++;
                    if (!empty($item['required']) && empty($item['configured'])) $requiredMissing++;
                }
                $catStatus = $requiredMissing > 0 ? 'bad' : ($configuredInCat < count($items) ? 'warn' : 'ok');
            @endphp
            <details class="cred-category" {{ $requiredMissing > 0 ? 'open' : '' }}>
                <summary class="cred-category-head">
                    <span class="cred-category-icon">{{ $icon }}</span>
                    <span class="cred-category-title">{{ $category }}</span>
                    <span class="badge-sm {{ $catStatus }}">{{ $configuredInCat }}/{{ count($items) }}</span>
                    <span class="cred-category-count">{{ count($items) }} fields</span>
                </summary>
                <div class="cred-category-body">
                    @foreach($items as $item)
                        @php
                            $fieldType = $item['field_type'] ?? 'text';
                            $options = $item['options'] ?? [];
                            $currentForEdit = (!$item['sensitive'] && !empty($item['configured'])) ? ($item['masked_value'] ?? '') : '';
                            $currentLabel = !empty($item['configured']) ? ($item['masked_value'] ?? 'configured') : 'not configured';
                            $statusBadge = !empty($item['configured']) ? 'ok' : (!empty($item['required']) ? 'bad' : 'warn');
                            $statusText = !empty($item['configured']) ? ($item['source'] ?? 'configured') : (!empty($item['required']) ? 'required' : 'optional');
                        @endphp
                        <div class="cred-item">
                            <div>
                                <div class="cred-item-name">{{ $item['label'] }}</div>
                                <div class="cred-item-key">{{ $item['name'] }}</div>
                            </div>
                            <div>
                                <div class="cred-item-current">{{ $currentLabel }}</div>
                            </div>
                            <span class="badge-sm {{ $statusBadge }}">{{ $statusText }}</span>
                            <span class="badge-sm neutral">{{ $item['validation_status'] ?? 'unknown' }}</span>
                        </div>
                        <form class="cred-item-form" method="POST" action="{{ route('credentials.update', $item['name']) }}">
                            @csrf
                            @if($fieldType === 'boolean' || $fieldType === 'select')
                                <label style="gap:4px">New value<select name="value"><option value="">Not configured</option>@foreach($options as $option)<option value="{{ $option }}" @selected($currentForEdit === $option)>{{ $option }}</option>@endforeach</select></label>
                            @else
                                <label style="gap:4px">New value<input name="value" type="{{ $item['sensitive'] ? 'password' : 'text' }}" value="{{ $currentForEdit }}" placeholder="{{ !empty($item['sensitive']) ? 'Enter replacement value' : 'Enter value' }}" autocomplete="off"></label>
                            @endif
                            <div class="cred-item-actions">
                                <button type="submit" class="small">Save</button>
                                @if(!empty($item['generator']))<form method="POST" action="{{ route('credentials.generate', $item['name']) }}">@csrf<button class="secondary small" type="submit">Generate</button></form>@endif
                                @if(!empty($item['configured']))<form method="POST" action="{{ route('credentials.reveal', $item['name']) }}">@csrf<button class="secondary small" type="submit">Reveal</button></form>@endif
                            </div>
                        </form>
                    @endforeach
                </div>
            </details>
        @endforeach
    @endif
</section>
@endsection
