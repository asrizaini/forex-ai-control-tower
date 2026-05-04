@extends('layouts.control', ['title' => 'Grafana / Monitoring', 'description' => 'Troubleshoot Grafana, Prometheus, API metrics, dashboard provisioning, and service networking.'])

@section('content')
<section class="grid-3">
    <div class="metric"><span class="eyebrow">Grafana</span><strong>{{ $healthStatus['services']['grafana']['status'] ?? 'unknown' }}</strong><span><a href="{{ $links['grafana'] }}" target="_blank" rel="noreferrer">Open Grafana</a></span></div>
    <div class="metric"><span class="eyebrow">Prometheus</span><strong>{{ $healthStatus['services']['prometheus']['status'] ?? 'unknown' }}</strong><span>metrics datasource</span></div>
    <div class="metric"><span class="eyebrow">API Metrics</span><strong>{{ $apiStatus['services']['api']['status'] ?? 'unknown' }}</strong><span>/metrics exposed</span></div>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Service Checks</h2><p>Use this to identify missing panels, datasource errors, and API connectivity issues.</p></div></div>
    @foreach(($healthStatus['services'] ?? []) as $name => $service)
        <div class="row cols-4"><strong>{{ $name }}</strong><span class="badge {{ ($service['status'] ?? '') === 'ok' ? 'ok' : 'warn' }}">{{ $service['status'] ?? 'unknown' }}</span><span>{{ $service['url'] ?? '' }}</span><span>{{ !empty($service['required_runtime_secrets_present']) ? 'configured' : '' }}</span></div>
    @endforeach
</section>
@endsection
