@extends('layouts.control', ['title' => 'Pair Detail', 'description' => 'Dedicated per-pair status with signal, strategy, trend, candle condition, and timeframe breakdown.'])

@section('content')
@php
    $detail = $pairDetail['item'] ?? null;
    $timeframes = $detail['timeframe_breakdown'] ?? [];
@endphp

@if(!$detail)
    <section class="panel">
        <h2>{{ $symbol }} not found</h2>
        <p class="empty">This pair is not configured yet. Add it in Trading Pairs, then run analysis.</p>
    </section>
@else
    <section class="grid-4" data-live-section="pair-{{ strtolower($detail['symbol']) }}-cards">
        <div class="metric {{ !empty($detail['enabled']) ? 'status-ok' : 'status-warn' }}">
            <span class="eyebrow">Pair Status</span>
            <strong>{{ $detail['symbol'] }}</strong>
            <span>{{ !empty($detail['enabled']) ? 'enabled for processing' : 'disabled and skipped' }}</span>
        </div>
        <div class="metric {{ ($detail['data_freshness_status'] ?? 'stale') === 'fresh' ? 'status-ok' : 'status-bad' }}">
            <span class="eyebrow">Freshness</span>
            <strong>{{ strtoupper($detail['data_freshness_status'] ?? 'stale') }}</strong>
            <span>Last update <span class="local-time" data-utc="{{ $detail['last_updated_time'] ?? '' }}">{{ $detail['last_updated_time'] ?? 'unknown' }}</span></span>
        </div>
        <div class="metric">
            <span class="eyebrow">Trend / Bias</span>
            <strong>{{ strtoupper($detail['trend_status'] ?? 'unclear') }}</strong>
            <span>{{ strtoupper($detail['current_bias'] ?? 'neutral') }}</span>
        </div>
        <div class="metric">
            <span class="eyebrow">Latest Signal</span>
            <strong>{{ strtoupper($detail['signal']['direction'] ?? 'hold') }}</strong>
            <span>{{ $detail['signal_status'] ?? 'no_signal' }} · {{ $detail['signal_confidence'] ?? 0 }}%</span>
        </div>
    </section>

    <section class="panel" data-live-section="pair-{{ strtolower($detail['symbol']) }}-summary">
        <div class="panel-head">
            <div>
                <h2>{{ $detail['symbol'] }} Summary</h2>
                <p>This page explains what this pair is doing, why it is bullish/bearish/neutral, and what is blocking execution.</p>
            </div>
            <div class="actions">
                <a class="button secondary small" href="{{ route('dashboard.trading-pairs') }}">Trading Pairs</a>
                <a class="button secondary small" href="{{ route('dashboard.signals') }}">Signals</a>
            </div>
        </div>
        <div class="table-wrap"><div class="table">
            <div class="row cols-2"><strong>Display Name</strong><span>{{ $detail['display_name'] ?? $detail['symbol'] }}</span></div>
            <div class="row cols-2"><strong>Assigned Strategy</strong><span>{{ $detail['strategy_id'] ?? $detail['signal']['strategy_used'] ?? 'not assigned' }}</span></div>
            <div class="row cols-2"><strong>Candle Status</strong><span>{{ $detail['candle_status'] ?? 'unknown' }}</span></div>
            <div class="row cols-2"><strong>Risk Summary</strong><span>{{ $detail['risk_summary'] ?? 'n/a' }}</span></div>
            <div class="row cols-2"><strong>Technical Summary</strong><span>{{ $detail['technical_summary'] ?? 'n/a' }}</span></div>
            <div class="row cols-2"><strong>Fundamental Summary</strong><span>{{ $detail['fundamental_summary'] ?? 'n/a' }}</span></div>
        </div></div>
    </section>

    <section class="panel" data-live-section="pair-{{ strtolower($detail['symbol']) }}-timeframes">
        <div class="panel-head">
            <div>
                <h2>Timeframe Breakdown</h2>
                <p>Every configured timeframe for this pair is analyzed separately, then merged into final decisioning.</p>
            </div>
        </div>
        <div class="table-wrap"><div class="table">
            @forelse($timeframes as $tf)
                <div class="row" style="grid-template-columns:.5fr .75fr .75fr .75fr .95fr 1.7fr">
                    <strong>{{ $tf['timeframe'] ?? '-' }}</strong>
                    <span class="badge {{ ($tf['freshness'] ?? 'stale') === 'fresh' ? 'ok' : 'bad' }}">{{ $tf['freshness'] ?? 'stale' }}</span>
                    <span>{{ $tf['trend_status'] ?? 'unclear' }}</span>
                    <span>{{ $tf['bias'] ?? 'neutral' }}</span>
                    <span>{{ $tf['signal_status'] ?? 'no_signal' }} · {{ $tf['signal_confidence'] ?? 0 }}%</span>
                    <span>{{ $tf['candle_summary'] ?? 'No candle summary' }}</span>
                </div>
            @empty
                <p class="empty">No timeframe rows available yet. Run market ingest and analysis first.</p>
            @endforelse
        </div></div>
    </section>
@endif

<script>
document.addEventListener('DOMContentLoaded', function () {
    const formatLocal = function (raw) {
        if (!raw) return '';
        const date = new Date(raw);
        if (Number.isNaN(date.getTime())) return raw;
        return date.toLocaleString('en-US', {
            timeZone: 'Asia/Kuala_Lumpur',
            hour12: true,
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        }) + ' GMT+8';
    };
    const refreshTimes = function () {
        document.querySelectorAll('.local-time[data-utc]').forEach(function (node) {
            node.textContent = formatLocal(node.getAttribute('data-utc'));
        });
    };
    refreshTimes();
    window.fxAfterSectionRefresh = function () {
        refreshTimes();
    };
});
</script>
@endsection
