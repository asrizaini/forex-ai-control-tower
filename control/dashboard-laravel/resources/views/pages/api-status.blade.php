@extends('layouts.control', ['title' => 'API Status', 'description' => 'Health endpoints, readiness, config status, and service-level checks.'])

@section('content')
<section class="panel">
    <div class="panel-head"><div><h2>API Health Matrix</h2><p>Dashboard values come from health endpoints, not hardcoded status.</p></div><span class="badge {{ ($apiStatus['status'] ?? '') === 'ok' ? 'ok' : 'warn' }}">{{ $apiStatus['status'] ?? 'unknown' }}</span></div>
    @foreach(($apiStatus['services'] ?? []) as $name => $service)
        <div class="row cols-3"><strong>{{ $name }}</strong><span class="badge {{ ($service['status'] ?? '') === 'ok' ? 'ok' : 'warn' }}">{{ $service['status'] ?? 'unknown' }}</span><span></span></div>
    @endforeach
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Configured Endpoints</h2><p>/health, /ready, /metrics, /api/status, /api/v1/workers/status, /api/v1/calendar/status, /api/v1/news/status, and /api/v1/config/status.</p></div></div>
    <div class="row cols-2"><strong>API base URL</strong><span>{{ $links['api'] }}</span></div>
    <div class="row cols-2"><strong>Docs</strong><span>{{ $links['docs'] }}</span></div>
</section>
@endsection
