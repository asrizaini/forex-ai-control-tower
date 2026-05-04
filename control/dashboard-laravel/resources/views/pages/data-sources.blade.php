@extends('layouts.control', ['title' => 'Data Sources', 'description' => 'Configure calendar, news, and market-data source priority, filters, rate limits, and source health.'])

@section('content')
<section class="grid-3">
    <div class="metric"><span class="eyebrow">Enabled Calendar Sources</span><strong>{{ $calendarStatus['enabled_sources'] ?? 0 }}</strong><span>priority and fallback enabled</span></div>
    <div class="metric"><span class="eyebrow">Last Success</span><strong>{{ $calendarStatus['last_success_at'] ?? 'none' }}</strong><span>calendar scrape</span></div>
    <div class="metric"><span class="eyebrow">Last Failure</span><strong>{{ $calendarStatus['last_failure_at'] ?? 'none' }}</strong><span>calendar scrape</span></div>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Source Configuration</h2><p>Use conservative intervals and source-specific adapters. Direct scraping remains disabled until configured deliberately.</p></div><span class="badge ok">provider pattern</span></div>
    @forelse(($sources['items'] ?? []) as $source)
        <div class="panel" style="box-shadow:none;margin-bottom:12px">
            <div class="row cols-5"><strong>{{ $source['name'] }}</strong><span>{{ $source['source_type'] }}</span><span>{{ $source['provider'] }}</span><span class="badge {{ !empty($source['enabled']) ? 'ok' : 'warn' }}">{{ !empty($source['enabled']) ? 'enabled' : 'disabled' }}</span><span>{{ $source['last_status'] }}</span></div>
            <form class="stack" method="POST" action="{{ route('data-sources.update', $source['source_id']) }}" style="margin-top:10px">
                @csrf
                <div class="form-grid">
                    <label>Name<input name="name" value="{{ $source['name'] }}"></label>
                    <label>Type<select name="source_type"><option @selected($source['source_type']==='calendar')>calendar</option><option @selected($source['source_type']==='news')>news</option><option @selected($source['source_type']==='market_data')>market_data</option></select></label>
                    <label>Provider<input name="provider" value="{{ $source['provider'] }}"></label>
                    <label>Enabled<select name="enabled"><option value="1" @selected($source['enabled'])>true</option><option value="0" @selected(!$source['enabled'])>false</option></select></label>
                </div>
                <div class="form-grid">
                    <label>Priority<input name="priority" type="number" min="1" max="1000" value="{{ $source['priority'] }}"></label>
                    <label>Refresh minutes<input name="refresh_interval_minutes" type="number" min="1" value="{{ $source['refresh_interval_minutes'] }}"></label>
                    <label>Timeout seconds<input name="timeout_seconds" type="number" min="3" value="{{ $source['timeout_seconds'] }}"></label>
                    <label>Retries<input name="retry_count" type="number" min="0" value="{{ $source['retry_count'] }}"></label>
                </div>
                <div class="form-grid">
                    <label>Backoff seconds<input name="backoff_seconds" type="number" min="1" value="{{ $source['backoff_seconds'] }}"></label>
                    <label>Currencies<input name="allowed_currencies" value="{{ implode(',', $source['allowed_currencies'] ?? []) }}"></label>
                    <label>Impacts<input name="allowed_impacts" value="{{ implode(',', $source['allowed_impacts'] ?? []) }}"></label>
                    <label>Timezone<input name="timezone" value="{{ $source['timezone'] }}"></label>
                </div>
                <label>Adapter config JSON<textarea name="config_json">{{ json_encode($source['config_json'] ?? [], JSON_PRETTY_PRINT) }}</textarea></label>
                <div class="actions"><button type="submit">Save Source</button><span class="muted">{{ $source['last_error'] }}</span></div>
            </form>
        </div>
    @empty
        <p class="empty">No data sources registered.</p>
    @endforelse
</section>
@endsection
