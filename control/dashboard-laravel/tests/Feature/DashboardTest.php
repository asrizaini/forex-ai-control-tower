<?php

namespace Tests\Feature;

use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class DashboardTest extends TestCase
{
    public function test_dashboard_renders_control_tower_readiness(): void
    {
        config(['control_tower.api_url' => 'http://control-api.test']);

        Http::fake([
            'control-api.test/health' => Http::response([
                'status' => 'ok',
                'environment' => 'demo',
                'trading_mode' => 'monitor_only',
            ]),
            'control-api.test/api/v1/system/production-readiness' => Http::response([
                'environment' => 'demo',
                'trading_mode' => 'monitor_only',
                'live_trading_allowed' => false,
                'restricted_live_auto_allowed' => false,
                'gates' => [
                    'market_data_quality_gates_passed' => true,
                    'security_review_completed' => false,
                ],
                'next_required_actions' => [
                    'Complete the pre-live security review checklist.',
                ],
            ]),
            'control-api.test/api/v1/telemetry/market/latest?limit=8' => Http::response([
                [
                    'symbol' => 'EURUSD',
                    'trend' => 'bearish',
                    'spread' => 0.00011,
                    'feed_fresh' => true,
                    'rates_count' => 100,
                ],
            ]),
            'control-api.test/api/v1/system/health/status' => Http::response([
                'healthy' => true,
                'services' => [
                    'api' => ['status' => 'ok'],
                    'credentials' => ['status' => 'ok', 'required_runtime_secrets_present' => true],
                ],
            ]),
            'control-api.test/api/v1/telemetry/accounts/latest?limit=1' => Http::response([]),
            'control-api.test/api/v1/agent-theater/events?limit=8' => Http::response(['events' => []]),
        ]);

        $this->get('/')
            ->assertOk()
            ->assertSee('Forex AI Control Tower')
            ->assertSee('Laravel primary dashboard')
            ->assertSee('blocked')
            ->assertSee('Secure Login')
            ->assertSee('EURUSD');
    }
}
