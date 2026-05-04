@extends('layouts.control', ['title' => 'Testing / Backtesting', 'description' => 'Run strategy tests before allowing strategy output into governed signal generation.'])

@section('content')
<section class="panel">
    <div class="panel-head"><div><h2>Run Backtest</h2><p>Select pair, timeframe, strategy, and date range.</p></div></div>
    <form class="form-grid" method="POST" action="{{ route('testing.backtests.run') }}">
        @csrf
        <select name="symbol">@foreach(($pairs['items'] ?? []) as $pair)<option value="{{ $pair['symbol'] }}">{{ $pair['symbol'] }}</option>@endforeach</select>
        <select name="timeframe">@foreach(['M1','M5','M15','M30','H1','H4','D1'] as $tf)<option value="{{ $tf }}">{{ $tf }}</option>@endforeach</select>
        <select name="strategy_id">
            @forelse(($strategies['items'] ?? []) as $strategy)<option value="{{ $strategy['strategy_id'] }}">{{ $strategy['strategy_id'] }}</option>@empty<option value="trend_pullback_v1">trend_pullback_v1</option>@endforelse
        </select>
        <input name="date_from" placeholder="2026-01-01">
        <input name="date_to" placeholder="2026-05-05">
        <button type="submit">Run Test</button>
    </form>
</section>
<section class="panel">
    <div class="panel-head"><div><h2>Backtest Results</h2><p>Quality score is deterministic scaffold output until historical execution engine is expanded.</p></div></div>
    <div class="table">
        @forelse(($backtests['items'] ?? []) as $job)
            @php $result = $job['result'] ?? []; @endphp
            <div class="row" style="grid-template-columns:.8fr .7fr .6fr .7fr .7fr 1.2fr">
                <strong>{{ $job['strategy_id'] }}</strong>
                <span>{{ $job['symbol'] }}</span>
                <span>{{ $job['timeframe'] }}</span>
                <span>Score {{ $job['quality_score'] ?? 0 }}</span>
                <span>{{ $job['status'] }}</span>
                <span>PF {{ $result['profit_factor'] ?? '-' }} · DD {{ $result['max_drawdown_pct'] ?? '-' }}%</span>
            </div>
        @empty
            <p class="empty">No backtest jobs yet.</p>
        @endforelse
    </div>
</section>
@endsection
