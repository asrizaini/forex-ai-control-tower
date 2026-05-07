@extends('layouts.control', ['title' => 'Credentials & Secrets', 'description' => 'Manage credentials, tokens, API keys, passwords, webhook URLs, broker secrets, and integration values from fx-control.'])

@section('content')
@php
    $pending = session('pending_generated_credential');
    $revealed = session('generated_secret');
    $primaryCategories = ['Core Runtime', 'Trading Safety', 'News', 'Notifications', 'Mobile Push', 'OpenClaw', 'MT5 Bridge', 'Paid LLM', 'Auth And Recovery'];
    $orderedGroups = [];
    foreach ($primaryCategories as $category) {
        if (!empty($credentialGroups[$category])) {
            $orderedGroups[$category] = $credentialGroups[$category];
        }
    }
    foreach (($credentialGroups ?? []) as $category => $items) {
        if (!isset($orderedGroups[$category])) {
            $orderedGroups[$category] = $items;
        }
    }
@endphp
<section class="panel">
    <div class="panel-head"><div><h2>Storage Model</h2><p>Credentials saved here are encrypted in the control-plane database and persist across page refresh, API restart, and machine reboot.</p></div><span class="badge ok">persistent</span></div>
    @if($authenticated)
        <div class="actions" style="margin-top:8px">
            <form method="POST" action="{{ route('credentials.migrate-runtime') }}">
                @csrf
                <button class="secondary small" type="submit">Migrate Runtime Env To DB</button>
            </form>
        </div>
    @endif
    <div class="row cols-3">
        <strong>At rest</strong>
        <span>Encrypted in credential store using service key file.</span>
        <span class="muted">Secret values are never written to audit logs.</span>
    </div>
    <div class="row cols-3">
        <strong>Runtime fallback</strong>
        <span>If a value exists in runtime environment, the dashboard syncs and validates it.</span>
        <span class="muted">Source labels: dashboard_store, runtime_env, runtime_env_fallback.</span>
    </div>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Admin Security</h2><p>Change the active control-plane admin password.</p></div><span class="badge {{ $authenticated ? 'ok' : 'warn' }}">{{ $authenticated ? 'available' : 'login required' }}</span></div>
    @if($authenticated)
        <form class="form-grid" method="POST" action="{{ route('password.update') }}">
            @csrf
            <label>New admin password<input name="password" type="password" autocomplete="new-password" minlength="12" required></label>
            <label>Confirm password<input name="password_confirmation" type="password" autocomplete="new-password" minlength="12" required></label>
            <span></span><button type="submit">Change Password</button>
        </form>
    @endif
</section>
@if($pending)
    <section class="panel">
        <div class="panel-head"><div><h2>Generated Value Pending Approval</h2><p>{{ $pending['message'] }}</p></div><span class="badge warn">not applied</span></div>
        <div class="grid-2">
            <label>Current {{ $pending['label'] ?? $pending['name'] }}<div class="masked">{{ $pending['current'] ?? 'not configured' }}</div></label>
            <label>Generated {{ $pending['label'] ?? $pending['name'] }}<input id="pending-generated-secret" readonly value="{{ $pending['value'] }}" autocomplete="off"></label>
        </div>
        <div class="actions" style="margin-top:12px">
            <button class="secondary" type="button" onclick="navigator.clipboard.writeText(document.getElementById('pending-generated-secret').value)">Copy Generated</button>
            <form method="POST" action="{{ route('credentials.apply-generated', $pending['name']) }}">@csrf<button type="submit">Apply Generated</button></form>
            <form method="POST" action="{{ route('credentials.discard-generated') }}">@csrf<button class="secondary" type="submit">Discard</button></form>
        </div>
    </section>
@endif
@if($revealed)
    <section class="panel">
        <div class="panel-head"><div><h2>Secret Revealed For This Session</h2><p>{{ $revealed['message'] }}</p></div><span class="badge warn">audited</span></div>
        <label>{{ $revealed['name'] }}<input id="revealed-secret" readonly value="{{ $revealed['value'] }}" autocomplete="off"></label>
        <button class="secondary" type="button" onclick="navigator.clipboard.writeText(document.getElementById('revealed-secret').value)" style="margin-top:12px">Copy</button>
    </section>
@endif
<section class="panel">
    <div class="panel-head">
        <div><h2>Credentials Catalog</h2><p>Current secret values stay masked. Generated values are staged until explicitly applied.</p></div>
        <span class="badge {{ !empty($credentials['healthy']) ? 'ok' : 'warn' }}">{{ !empty($credentials['healthy']) ? 'healthy' : 'needs input' }}</span>
    </div>
    @if(!$authenticated)
        <p class="empty">Login to configure credentials.</p>
    @else
        <div class="grid-3">
            <div class="metric"><span class="eyebrow">Configured</span><strong>{{ $credentials['configured_count'] ?? 0 }}</strong><span>stored in credential manager</span></div>
            <div class="metric"><span class="eyebrow">Missing Required</span><strong>{{ count($credentials['missing_required'] ?? []) }}</strong><span>must be completed</span></div>
            <div class="metric"><span class="eyebrow">Invalid</span><strong>{{ count($credentials['invalid'] ?? []) }}</strong><span>needs correction</span></div>
        </div>
        @foreach($orderedGroups as $category => $items)
            <details class="panel" style="margin-top:18px;padding:0" open>
                <summary style="cursor:pointer;list-style:none;padding:16px 18px;border-bottom:1px solid #22344b;display:flex;align-items:center;justify-content:space-between">
                    <strong>{{ $category }}</strong>
                    <span class="muted">{{ count($items) }} fields</span>
                </summary>
                <div class="stack" style="padding:16px 18px">
                @foreach($items as $item)
                    @php
                        $fieldType = $item['field_type'] ?? 'text';
                        $options = $item['options'] ?? [];
                        $currentForEdit = (!$item['sensitive'] && !empty($item['configured'])) ? ($item['masked_value'] ?? '') : '';
                        $currentLabel = !empty($item['configured']) ? ($item['masked_value'] ?? 'configured') : 'not configured';
                    @endphp
                    <div class="panel" style="box-shadow:none">
                        <div class="row cols-4">
                            <div><strong>{{ $item['label'] }}</strong><p>{{ $item['name'] }} · {{ !empty($item['required']) ? 'required' : 'optional' }}</p></div>
                            <div><span class="muted">Current</span><div class="masked">{{ $currentLabel }}</div></div>
                            <span class="badge {{ !empty($item['configured']) ? 'ok' : 'warn' }}">{{ !empty($item['configured']) ? ($item['source'] ?? 'configured') : 'missing' }}</span>
                            <span>{{ $item['validation_status'] ?? 'unknown' }}</span>
                        </div>
                        <form class="form-grid" method="POST" action="{{ route('credentials.update', $item['name']) }}" style="margin-top:10px">
                            @csrf
                            @if($fieldType === 'boolean' || $fieldType === 'select')
                                <label>New value<select name="value"><option value="">Not configured</option>@foreach($options as $option)<option value="{{ $option }}" @selected($currentForEdit === $option)>{{ $option }}</option>@endforeach</select></label>
                            @else
                                <label>New value<input name="value" type="{{ $item['sensitive'] ? 'password' : 'text' }}" value="{{ $currentForEdit }}" placeholder="{{ !empty($item['sensitive']) ? 'Enter replacement value' : 'Enter value' }}" autocomplete="off"></label>
                            @endif
                            <span></span><span></span><button type="submit">Save</button>
                        </form>
                        <div class="actions" style="margin-top:10px">
                            @if(!empty($item['generator']))<form method="POST" action="{{ route('credentials.generate', $item['name']) }}">@csrf<button class="secondary small" type="submit">Generate</button></form>@endif
                            @if(!empty($item['configured']))<form method="POST" action="{{ route('credentials.reveal', $item['name']) }}">@csrf<button class="secondary small" type="submit">Reveal Current</button></form>@endif
                        </div>
                    </div>
                @endforeach
                </div>
            </details>
        @endforeach
    @endif
</section>
@endsection
