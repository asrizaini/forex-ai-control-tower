@extends('layouts.control', ['title' => 'Settings', 'description' => 'Global timezone, default filters, refresh intervals, retention, URLs, and worker concurrency.'])

@section('content')
<section class="panel">
    <div class="panel-head"><div><h2>Global Configuration</h2><p>Normal runtime settings are managed here after deployment.</p></div><span class="badge ok">{{ $configStatus['status'] ?? 'ok' }}</span></div>
    @forelse(($configStatus['settings'] ?? []) as $setting)
        <form class="row cols-4" method="POST" action="{{ route('settings.update', $setting['setting_key']) }}">
            @csrf
            <div><strong>{{ $setting['setting_key'] }}</strong><p>{{ $setting['category'] }}</p></div>
            <input name="setting_value" value="{{ $setting['setting_value'] }}">
            <select name="value_type"><option @selected($setting['value_type']==='string')>string</option><option @selected($setting['value_type']==='integer')>integer</option><option @selected($setting['value_type']==='csv')>csv</option><option @selected($setting['value_type']==='url')>url</option></select>
            <input type="hidden" name="category" value="{{ $setting['category'] }}"><button class="secondary small" type="submit">Save</button>
        </form>
    @empty
        <p class="empty">No settings registered.</p>
    @endforelse
</section>
@endsection
