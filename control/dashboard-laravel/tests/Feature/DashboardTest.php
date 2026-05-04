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
            'control-api.test/api/v1/api/status' => Http::response(['status' => 'ok', 'services' => ['api' => ['status' => 'ok']]]),
            'control-api.test/api/v1/calendar/status' => Http::response(['status' => 'needs_configuration', 'events_count' => 0, 'sources' => []]),
            'control-api.test/api/v1/news/status' => Http::response(['risk_status' => 'news_safe_mode', 'news_halt_active' => true]),
            'control-api.test/api/v1/workers/status' => Http::response(['workers' => [['name' => 'Calendar Worker', 'worker_type' => 'calendar', 'status' => 'degraded']]]),
            'control-api.test/api/v1/logs/audit?limit=8' => Http::response(['items' => []]),
        ]);

        $this->get('/')
            ->assertOk()
            ->assertSee('Overview / Home')
            ->assertSee('fx-control dashboard')
            ->assertSee('blocked')
            ->assertSee('Secure Login')
            ->assertSee('Calendar Worker');
    }

    public function test_authenticated_admin_can_request_password_change(): void
    {
        config(['control_tower.api_url' => 'http://control-api.test']);

        Http::fake([
            'control-api.test/api/v1/auth/password' => Http::response(['ok' => true]),
        ]);

        $this->withSession([
            'control_tower_token' => 'session-token',
            'control_tower_user' => 'admin',
        ])->post('/password', [
            'password' => 'new-admin-password-123',
            'password_confirmation' => 'new-admin-password-123',
        ])->assertRedirect('/');

        Http::assertSent(fn ($request) => $request->url() === 'http://control-api.test/api/v1/auth/password'
            && $request->hasHeader('Authorization', 'Bearer session-token')
            && $request['user_id'] === 'admin');
    }

    public function test_generate_credential_stages_value_before_apply(): void
    {
        config(['control_tower.api_url' => 'http://control-api.test']);

        Http::fake([
            'control-api.test/api/v1/credentials/JWT_SECRET_KEY/generate' => Http::response([
                'value' => 'generated-review-value',
            ]),
            'control-api.test/api/v1/credentials/status' => Http::response([
                'items' => [[
                    'name' => 'JWT_SECRET_KEY',
                    'label' => 'JWT Secret Key',
                    'category' => 'Core Security',
                    'configured' => true,
                    'masked_value' => '************abcd',
                    'sensitive' => true,
                ]],
            ]),
        ]);

        $this->withSession([
            'control_tower_token' => 'session-token',
            'control_tower_user' => 'admin',
        ])->post('/credentials/JWT_SECRET_KEY/generate')
            ->assertRedirect('/')
            ->assertSessionHas('pending_generated_credential.name', 'JWT_SECRET_KEY')
            ->assertSessionHas('pending_generated_credential.current', '************abcd');
    }

    public function test_apply_generated_credential_saves_staged_value(): void
    {
        config(['control_tower.api_url' => 'http://control-api.test']);

        Http::fake([
            'control-api.test/api/v1/credentials/JWT_SECRET_KEY' => Http::response(['ok' => true]),
        ]);

        $this->withSession([
            'control_tower_token' => 'session-token',
            'control_tower_user' => 'admin',
            'pending_generated_credential' => [
                'name' => 'JWT_SECRET_KEY',
                'value' => 'generated-review-value',
            ],
        ])->post('/credentials/JWT_SECRET_KEY/apply-generated')
            ->assertRedirect('/')
            ->assertSessionMissing('pending_generated_credential');

        Http::assertSent(fn ($request) => $request->url() === 'http://control-api.test/api/v1/credentials/JWT_SECRET_KEY'
            && $request->method() === 'PUT'
            && $request->hasHeader('Authorization', 'Bearer session-token'));
    }

    public function test_agent_theater_page_renders_chatroom(): void
    {
        config(['control_tower.api_url' => 'http://control-api.test']);

        Http::fake([
            'control-api.test/api/v1/agent-theater/events?limit=80' => Http::response([
                'events' => [[
                    'agent' => 'Orchestrator Agent',
                    'stream' => 'Orchestrator Chat',
                    'summary' => 'The current fx-control time is 2026-05-04 23:18:25 Asia/Kuala_Lumpur.',
                    'timestamp' => '2026-05-04 23:18:25 Asia/Kuala_Lumpur',
                    'risk_status' => 'read_only_no_trade_execution',
                    'result' => 'safe_reply',
                ]],
                'modes' => ['Live Chat View'],
            ]),
            'control-api.test/api/v1/agent-theater/modes' => Http::response([
                'modes' => [['name' => 'Live Chat View', 'description' => 'Human-readable room feed']],
            ]),
        ]);

        $this->get('/agent-theater')
            ->assertOk()
            ->assertSee('Agent Theater / Orchestrator Console')
            ->assertSee('Talk To Orchestrator')
            ->assertSee('Asia/Kuala_Lumpur');
    }

    public function test_authenticated_admin_can_send_orchestrator_chat(): void
    {
        config(['control_tower.api_url' => 'http://control-api.test']);

        Http::fake([
            'control-api.test/api/v1/agent-theater/chat' => Http::response(['accepted' => true]),
        ]);

        $this->withSession([
            'control_tower_token' => 'session-token',
            'control_tower_user' => 'admin',
        ])->post('/agent-theater/chat', [
            'message' => 'What is the current time and date?',
            'language' => 'en',
        ])->assertRedirect('/');

        Http::assertSent(fn ($request) => $request->url() === 'http://control-api.test/api/v1/agent-theater/chat'
            && $request->method() === 'POST'
            && $request->hasHeader('Authorization', 'Bearer session-token')
            && $request['session_id'] === 'laravel-orchestrator-console');
    }
}
