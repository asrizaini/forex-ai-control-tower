@extends('layouts.control', ['title' => 'Risk Validation', 'description' => 'Per-pair risk/fundamental blockers and execution-safe validation summary.'])

@section('content')
<section class="panel">
    <div class="panel-head"><div><h2>Pair Risk Gates</h2><p>Risk validation is monitor-only here; MT5 execution remains blocked without approval and Execution Guard token.</p></div></div>
    <div class="table">
        @forelse(($summaries['items'] ?? []) as $item)
            <div class="row" style="grid-template-columns:.7fr .8fr .8fr 2fr">
                <strong>{{ $item['symbol'] }}</strong>
                <span class="badge {{ $item['final_conclusion'] === 'Blocked' ? 'bad' : ($item['data_freshness_status'] === 'fresh' ? 'ok' : 'warn') }}">{{ $item['final_conclusion'] }}</span>
                <span>{{ $item['signal_status'] }}</span>
                <span>{{ $item['risk_summary'] }}</span>
            </div>
        @empty
            <p class="empty">No risk validation output yet.</p>
        @endforelse
    </div>
</section>
@endsection
