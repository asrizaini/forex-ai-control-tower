@extends('layouts.control', ['title' => 'Alert Rules', 'description' => 'Create, edit, test, and audit event/news alert rules with duplicate-fire tracking.'])

@section('content')
<section class="panel">
    <div class="panel-head"><div><h2>Create / Update Rule</h2><p>Rule ID can be reused to update an existing rule.</p></div></div>
    <form class="stack" method="POST" action="{{ route('alert-rules.update', 'calendar_high_impact_default') }}">
        @csrf
        <div class="form-grid">
            <label>Name<input name="name" value="High impact event warning"></label>
            <label>Enabled<select name="enabled"><option value="1">true</option><option value="0">false</option></select></label>
            <label>Severity<select name="severity"><option>warning</option><option>critical</option><option>normal</option><option>info</option></select></label>
            <label>Minutes before<input name="minutes_before" type="number" value="45"></label>
        </div>
        <div class="form-grid">
            <label>Currencies<input name="currencies" value="USD,EUR,GBP,JPY"></label>
            <label>Impacts<input name="impacts" value="high"></label>
            <label>Keywords<input name="event_keywords" value="CPI,FOMC,NFP,rate"></label>
            <label>Delivery targets<input name="delivery_targets" value="dashboard,telegram"></label>
        </div>
        <button type="submit">Save Rule</button>
    </form>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Rules</h2><p>Match by currency, impact, keyword, exact event, weekday, source, and trading pair.</p></div></div>
    @forelse(($rules['items'] ?? []) as $rule)
        <div class="row cols-5"><strong>{{ $rule['name'] }}</strong><span>{{ implode(',', $rule['currencies'] ?? []) }}</span><span>{{ implode(',', $rule['impacts'] ?? []) }}</span><span class="badge {{ !empty($rule['enabled']) ? 'ok' : 'warn' }}">{{ !empty($rule['enabled']) ? 'enabled' : 'disabled' }}</span><form method="POST" action="{{ route('alert-rules.test', $rule['rule_id']) }}">@csrf<button class="secondary small">Test</button></form></div>
    @empty
        <p class="empty">No alert rules yet.</p>
    @endforelse
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Delivery History</h2><p>Delivery state is tracked to prevent duplicate alerts.</p></div></div>
    @forelse(($history['items'] ?? []) as $item)
        <div class="row cols-5"><strong>{{ $item['delivery_id'] }}</strong><span>{{ $item['rule_id'] }}</span><span>{{ $item['target'] }}</span><span class="badge {{ $item['status'] === 'sent' ? 'ok' : 'warn' }}">{{ $item['status'] }}</span><span>{{ $item['created_at'] }}</span></div>
    @empty
        <p class="empty">No delivery history.</p>
    @endforelse
</section>
@endsection
