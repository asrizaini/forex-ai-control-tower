@extends('layouts.control', ['title' => 'Logs & Audit', 'description' => 'Centralized safe audit summaries for configuration, workers, alerts, API errors, and scraper events.'])

@section('content')
<section class="panel">
    <div class="panel-head"><div><h2>Audit Filters</h2><p>Secret values are not logged or rendered.</p></div></div>
    <form class="form-grid" method="GET" action="{{ route('dashboard.logs') }}">
        <label>Service / resource type<input name="service" value="{{ $filters['service'] ?? '' }}"></label>
        <label>Keyword<input name="keyword" value="{{ $filters['keyword'] ?? '' }}"></label>
        <label>Limit<input name="limit" type="number" min="1" max="500" value="{{ $filters['limit'] ?? 100 }}"></label>
        <button type="submit">Filter</button>
    </form>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Audit Log</h2><p>Configuration changes, worker actions, alert tests, and credential updates are audited.</p></div></div>
    @forelse(($logs['items'] ?? []) as $log)
        <div class="row cols-5"><strong>{{ $log['action'] }}</strong><span>{{ $log['actor'] }}</span><span>{{ $log['resource_type'] }}</span><span>{{ $log['resource_id'] }}</span><span data-utc="{{ $log['created_at'] ?? '' }}">{{ $log['created_at'] }}</span></div>
    @empty
        <p class="empty">No audit records found.</p>
    @endforelse
</section>
@endsection
