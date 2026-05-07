<?php

namespace App\Http\Controllers;

use App\Services\ControlTowerClient;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Session;
use Throwable;
use Illuminate\View\View;

class DashboardController extends Controller
{
    public function __construct(private readonly ControlTowerClient $client)
    {
    }

    public function loginPage(Request $request): View|RedirectResponse
    {
        if ($request->session()->get('control_tower_token')) {
            return redirect()->route('dashboard.overview');
        }

        return $this->render($request, 'pages.login', 'login');
    }

    public function overview(Request $request): View
    {
        $poolResults = $this->client->getPool([
            'health' => '/health',
            '__fallback_health' => ['status' => 'unavailable'],
            'apiStatus' => '/api/v1/api/status',
            '__fallback_apiStatus' => ['status' => 'unavailable', 'services' => []],
            'runtimeStatus' => '/api/v1/system/runtime',
            '__fallback_runtimeStatus' => ['orchestrator' => ['status' => 'down']],
            'healthStatus' => '/api/v1/system/health/status',
            '__fallback_healthStatus' => ['healthy' => false, 'services' => []],
            'calendarStatus' => '/api/v1/calendar/status',
            '__fallback_calendarStatus' => ['status' => 'unavailable', 'sources' => []],
            'newsStatus' => '/api/v1/news/status',
            '__fallback_newsStatus' => ['risk_status' => 'unavailable'],
            'workers' => '/api/v1/workers/status',
            '__fallback_workers' => ['workers' => []],
            'pairSummaries' => '/api/v1/pair-summaries',
            '__fallback_pairSummaries' => ['items' => [], 'summary' => []],
            'signals' => '/api/v1/signals/summary',
            '__fallback_signals' => ['items' => [], 'summary' => []],
            'signalRecords' => '/api/v1/signals/records?limit=12',
            '__fallback_signalRecords' => ['items' => []],
            'accounts' => '/api/v1/accounts/records',
            '__fallback_accounts' => [],
            'accountSnapshots' => '/api/v1/telemetry/accounts/latest?limit=5',
            '__fallback_accountSnapshots' => [],
            'readiness' => '/api/v1/system/production-readiness',
            '__fallback_readiness' => [],
            'auditLogs' => '/api/v1/logs/audit?limit=8',
            '__fallback_auditLogs' => ['items' => []],
        ]);

        return $this->render($request, 'pages.overview', 'overview', $poolResults);
    }

    public function tradingPairs(Request $request): View
    {
        return $this->render($request, 'pages.trading-pairs', 'trading-pairs', [
            'pairs' => $this->client->get('/api/v1/trading-pairs', null, ['items' => []]),
            'strategies' => $this->client->get('/api/v1/strategies/summary', null, ['items' => []]),
        ]);
    }

    public function pairSummary(Request $request): View
    {
        return $this->render($request, 'pages.pair-summary', 'pair-summary', [
            'summaries' => $this->client->get('/api/v1/pair-summaries', null, ['items' => [], 'summary' => []]),
        ]);
    }

    public function pairDetail(Request $request, string $symbol): View
    {
        $safeSymbol = strtoupper(trim($symbol));
        return $this->render($request, 'pages.pair-detail', 'pair-summary', [
            'pairDetail' => $this->client->get('/api/v1/pair-summaries/' . rawurlencode($safeSymbol), null, ['status' => 'not_found']),
            'symbol' => $safeSymbol,
        ]);
    }

    public function signals(Request $request): View
    {
        return $this->render($request, 'pages.signals', 'signals', [
            'signals' => $this->client->get('/api/v1/signals/summary', null, ['items' => [], 'summary' => []]),
            'records' => $this->client->get('/api/v1/signals/records?limit=100', null, ['items' => []]),
        ]);
    }

    public function strategy(Request $request): View
    {
        return $this->render($request, 'pages.strategy', 'strategy', [
            'strategies' => $this->client->get('/api/v1/strategies/summary', null, ['items' => []]),
            'plugins' => $this->client->get('/api/v1/strategies/plugins', null, ['plugins' => []]),
        ]);
    }

    public function candleAnalysis(Request $request): View
    {
        return $this->render($request, 'pages.pair-analysis', 'candle-analysis', [
            'title' => 'Candle Analysis',
            'analysisKey' => 'candle_analysis',
            'summaries' => $this->client->get('/api/v1/pair-summaries', null, ['items' => [], 'summary' => []]),
        ]);
    }

    public function trendAnalysis(Request $request): View
    {
        return $this->render($request, 'pages.pair-analysis', 'trend-analysis', [
            'title' => 'Trend Analysis',
            'analysisKey' => 'trend_analysis',
            'summaries' => $this->client->get('/api/v1/pair-summaries', null, ['items' => [], 'summary' => []]),
        ]);
    }

    public function riskValidation(Request $request): View
    {
        $token = $this->optionalToken($request);
        $poolRequests = [
            'summaries' => '/api/v1/pair-summaries',
            '__fallback_summaries' => ['items' => [], 'summary' => []],
            'accounts' => '/api/v1/accounts/records',
            '__fallback_accounts' => [],
            'accountSnapshots' => '/api/v1/telemetry/accounts/latest?limit=5',
            '__fallback_accountSnapshots' => [],
            'executions' => '/api/v1/trades/executions?limit=80',
            '__fallback_executions' => ['items' => []],
        ];
        if ($token) {
            $poolRequests['demoStatus'] = '/api/v1/trades/demo-auto/status';
            $poolRequests['__fallback_demoStatus'] = [];
            $poolRequests['demoActivity'] = '/api/v1/trades/demo-auto/activity?limit=40';
            $poolRequests['__fallback_demoActivity'] = ['items' => []];
        }
        $poolResults = $this->client->getPool($poolRequests, $token);

        return $this->render($request, 'pages.risk-validation', 'risk-validation', $poolResults);
    }

    public function testing(Request $request): View
    {
        return $this->render($request, 'pages.testing', 'testing', [
            'pairs' => $this->client->get('/api/v1/trading-pairs', null, ['items' => []]),
            'strategies' => $this->client->get('/api/v1/strategies/summary', null, ['items' => []]),
            'backtests' => $this->client->get('/api/v1/testing/backtests', null, ['items' => []]),
        ]);
    }

    public function credentials(Request $request): View
    {
        $token = $this->optionalToken($request);
        $credentials = $token
            ? $this->client->get('/api/v1/credentials/status', $token, ['items' => [], 'healthy' => false])
            : ['items' => [], 'healthy' => false, 'notes' => 'Login required.'];

        return $this->render($request, 'pages.credentials', 'credentials', [
            'credentials' => $credentials,
            'credentialGroups' => $this->groupCredentials($credentials['items'] ?? []),
        ]);
    }

    public function dataSources(Request $request): View
    {
        return $this->render($request, 'pages.data-sources', 'data-sources', [
            'sources' => $this->client->get('/api/v1/data-sources', null, ['items' => []]),
            'calendarStatus' => $this->client->get('/api/v1/calendar/status', null, ['sources' => []]),
        ]);
    }

    public function calendar(Request $request): View
    {
        $query = http_build_query(array_filter([
            'currency' => $request->query('currency'),
            'impact' => $request->query('impact'),
            'source' => $request->query('source'),
            'keyword' => $request->query('keyword'),
            'status' => $request->query('status'),
            'limit' => $request->query('limit', 50),
            'offset' => $request->query('offset', 0),
        ], fn ($value) => $value !== null && $value !== ''));

        return $this->render($request, 'pages.calendar', 'calendar', [
            'status' => $this->client->get('/api/v1/calendar/status', null, ['sources' => []]),
            'events' => $this->client->get('/api/v1/calendar/events' . ($query ? '?' . $query : ''), null, ['results' => [], 'total' => 0]),
            'filters' => $request->query(),
        ]);
    }

    public function news(Request $request): View
    {
        $query = http_build_query(array_filter([
            'keyword' => $request->query('keyword'),
            'currency' => $request->query('currency'),
            'source' => $request->query('source'),
            'limit' => $request->query('limit', 50),
            'offset' => $request->query('offset', 0),
        ], fn ($value) => $value !== null && $value !== ''));

        return $this->render($request, 'pages.news', 'news', [
            'status' => $this->client->get('/api/v1/news/status', null, []),
            'items' => $this->client->get('/api/v1/news/items' . ($query ? '?' . $query : ''), null, ['results' => [], 'total' => 0]),
            'providerEvents' => $this->client->get('/api/v1/news/events' . ($query ? '?' . $query : ''), null, ['events' => []]),
            'filters' => $request->query(),
        ]);
    }

    public function alertRules(Request $request): View
    {
        return $this->render($request, 'pages.alert-rules', 'alert-rules', [
            'rules' => $this->client->get('/api/v1/alert-rules', null, ['items' => []]),
            'history' => $this->client->get('/api/v1/alert-rules/history', null, ['items' => []]),
        ]);
    }

    public function workers(Request $request): View
    {
        return $this->render($request, 'pages.workers', 'workers', [
            'workers' => $this->client->get('/api/v1/workers/status', null, ['workers' => []]),
            'agentRuntime' => $this->client->get('/api/v1/agents/runtime-summary', null, [
                'orchestrator_health' => 'unknown',
                'queued_tasks' => 0,
                'running_tasks' => 0,
                'retrying_tasks' => 0,
                'failed_tasks' => 0,
                'completed_tasks' => 0,
                'stale_agents_count' => 0,
                'last_failed_task' => null,
            ]),
            'runtimeStatus' => $this->client->get('/api/v1/system/runtime', null, [
                'orchestrator' => ['status' => 'unknown', 'reason' => 'unavailable', 'last_success_run' => null, 'last_failed_run' => null, 'retry_status' => 'unknown'],
            ]),
        ]);
    }

    public function agentTheater(Request $request): View
    {
        $query = $this->agentTheaterQuery($request);
        return $this->render($request, 'pages.agent-theater', 'agent-theater', [
            'events' => $this->client->get('/api/v1/agent-theater/events' . ($query ? '?' . $query : ''), null, ['events' => [], 'modes' => [], 'agents' => [], 'streams' => []]),
            'modes' => $this->client->get('/api/v1/agent-theater/modes', null, ['modes' => []]),
            'filters' => $request->query(),
        ]);
    }

    public function agentTheaterFeed(Request $request): JsonResponse
    {
        $query = $this->agentTheaterQuery($request);
        return response()->json($this->client->get('/api/v1/agent-theater/events' . ($query ? '?' . $query : ''), null, ['events' => [], 'modes' => [], 'agents' => [], 'streams' => []]));
    }

    public function orchestratorConsole(Request $request): View
    {
        return $this->render($request, 'pages.orchestrator-console', 'orchestrator-console', [
            'events' => $this->client->get('/api/v1/agent-theater/events?limit=80&stream=Orchestrator%20Console&agent=Operator&agent=Orchestrator%20Agent', null, ['events' => []]),
            'orchestratorHealth' => $this->client->get('/api/v1/agent-theater/orchestrator/health', null, []),
        ]);
    }

    public function orchestratorConsoleFeed(): JsonResponse
    {
        return response()->json($this->client->get('/api/v1/agent-theater/events?limit=80&stream=Orchestrator%20Console&agent=Operator&agent=Orchestrator%20Agent', null, ['events' => []]));
    }

    public function technical(Request $request): View
    {
        return $this->render($request, 'pages.analysis', 'technical', [
            'analysisType' => 'technical',
            'title' => 'Technical Analysis',
            'snapshots' => $this->client->get('/api/v1/analysis/technical/latest', null, ['items' => []]),
        ]);
    }

    public function fundamental(Request $request): View
    {
        return $this->render($request, 'pages.analysis', 'fundamental', [
            'analysisType' => 'fundamental',
            'title' => 'Fundamental Analysis',
            'snapshots' => $this->client->get('/api/v1/analysis/fundamental/latest', null, ['items' => []]),
        ]);
    }

    public function monitoring(Request $request): View
    {
        return $this->render($request, 'pages.monitoring', 'monitoring', [
            'healthStatus' => $this->client->get('/api/v1/system/health/status', null, ['services' => []]),
            'apiStatus' => $this->client->get('/api/v1/api/status', null, ['services' => []]),
        ]);
    }

    public function apiStatus(Request $request): View
    {
        return $this->render($request, 'pages.api-status', 'api-status', [
            'apiStatus' => $this->client->get('/api/v1/api/status', null, ['services' => []]),
            'configStatus' => $this->client->get('/api/v1/config/status', null, ['settings' => []]),
        ]);
    }

    public function logs(Request $request): View
    {
        $query = http_build_query(array_filter([
            'service' => $request->query('service'),
            'keyword' => $request->query('keyword'),
            'limit' => $request->query('limit', 100),
        ], fn ($value) => $value !== null && $value !== ''));

        return $this->render($request, 'pages.logs', 'logs', [
            'logs' => $this->client->get('/api/v1/logs/audit' . ($query ? '?' . $query : ''), null, ['items' => []]),
            'filters' => $request->query(),
        ]);
    }

    public function settings(Request $request): View
    {
        return $this->render($request, 'pages.settings', 'settings', [
            'configStatus' => $this->client->get('/api/v1/config/status', null, ['settings' => []]),
        ]);
    }

    public function openclaw(Request $request): View
    {
        return $this->render($request, 'pages.openclaw', 'openclaw', [
            'status' => $this->client->get('/api/v1/openclaw/status', null, []),
            'runtimeHealth' => $this->client->get('/api/v1/openclaw/runtime/health', null, []),
            'contract' => $this->client->get('/api/v1/openclaw/contract', null, []),
            'runtime' => $this->client->get('/api/v1/system/runtime', null, []),
            'allowedTargets' => ['system', 'risk', 'signals', 'workers', 'news', 'accounts', 'pairs'],
            'allowedPaths' => [
                '/api/v1/system/runtime',
                '/api/v1/system/health/status',
                '/api/v1/workers/status',
                '/api/v1/news/status',
                '/api/v1/calendar/status',
                '/api/v1/signals/summary',
                '/api/v1/pair-summaries',
            ],
        ]);
    }

    public function login(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'user_id' => ['required', 'string', 'max:120'],
            'password' => ['required', 'string'],
            'totp_code' => ['nullable', 'string', 'max:16'],
        ]);

        $response = $this->client->post('/api/v1/auth/login', [
            'user_id' => $validated['user_id'],
            'password' => $validated['password'],
            'totp_code' => $validated['totp_code'] ?: null,
        ]);

        if (! $response->successful()) {
            return back()->with('error', 'Invalid credentials or 2FA code.');
        }

        $body = $response->json() ?? [];
        $request->session()->regenerate();
        $request->session()->put('control_tower_token', $body['access_token'] ?? '');
        $request->session()->put('control_tower_refresh_token', $body['refresh_token'] ?? '');
        $request->session()->put('control_tower_user', $validated['user_id']);

        return redirect()->route('dashboard.overview')->with('status', 'Logged in.');
    }

    public function logout(Request $request): RedirectResponse
    {
        $request->session()->forget(['control_tower_token', 'control_tower_refresh_token', 'control_tower_user']);
        $request->session()->regenerateToken();

        return redirect()->route('dashboard.overview')->with('status', 'Logged out.');
    }

    public function updatePassword(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $validated = $request->validate(['password' => ['required', 'string', 'min:12', 'max:256', 'confirmed']]);
        $response = $this->client->post('/api/v1/auth/password', [
            'user_id' => (string) $request->session()->get('control_tower_user', 'admin'),
            'password' => $validated['password'],
        ], $token);

        return $this->redirectResponse($response, 'Admin password updated. Sign out and back in with the new password when ready.', 'Password update failed.');
    }

    public function createTradingPair(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $payload = $this->tradingPairCreatePayload($request);
        $response = $this->client->post('/api/v1/trading-pairs', $payload, $token);

        return $this->redirectResponse($response, 'Trading pair added.', 'Trading pair create failed.');
    }

    public function updateTradingPair(Request $request, string $symbol): RedirectResponse
    {
        $token = $this->requireToken($request);
        $payload = $this->tradingPairUpdatePayload($request);
        $response = $this->client->put('/api/v1/trading-pairs/' . rawurlencode($symbol), $payload, $token);

        return $this->redirectResponse($response, 'Trading pair saved.', 'Trading pair update failed.');
    }

    public function runAnalysis(Request $request): RedirectResponse
    {
        $response = $this->client->post('/api/v1/analysis/run', [], $this->requireToken($request));
        return $this->redirectResponse($response, 'Analysis and monitor-only signal generation completed.', 'Analysis run failed.');
    }

    public function runBacktest(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $payload = $request->validate([
            'symbol' => ['required', 'string', 'max:40'],
            'timeframe' => ['required', 'string', 'max:20'],
            'strategy_id' => ['required', 'string', 'max:100'],
            'date_from' => ['nullable', 'string', 'max:40'],
            'date_to' => ['nullable', 'string', 'max:40'],
        ]);
        $response = $this->client->post('/api/v1/testing/backtests/run', $payload, $token);

        return $this->redirectResponse($response, 'Backtest completed.', 'Backtest failed.');
    }

    public function updateCredential(Request $request, string $name): RedirectResponse
    {
        $token = $this->requireToken($request);
        $validated = $request->validate(['value' => ['nullable', 'string']]);
        $response = $this->client->put('/api/v1/credentials/' . rawurlencode($name), ['value' => $validated['value'] ?? ''], $token);

        return $this->redirectResponse($response, "{$name} saved. Secret value was not logged.", 'Credential update failed.');
    }

    public function generateCredential(Request $request, string $name): RedirectResponse
    {
        $token = $this->requireToken($request);
        $response = $this->client->post('/api/v1/credentials/' . rawurlencode($name) . '/generate', [], $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'Credential generation failed.'));
        }
        $body = $response->json() ?? [];
        $status = $this->client->get('/api/v1/credentials/status', $token, ['items' => []]);
        $item = $this->findCredential($status['items'] ?? [], $name);

        return back()->with('pending_generated_credential', [
            'name' => $name,
            'label' => $item['label'] ?? $name,
            'category' => $item['category'] ?? 'Credentials',
            'current' => $item['masked_value'] ?? 'not configured',
            'value' => $body['value'] ?? '',
            'message' => 'Generated value is staged only. Review it, copy it if needed, then apply to save.',
        ]);
    }

    public function applyGeneratedCredential(Request $request, string $name): RedirectResponse
    {
        $token = $this->requireToken($request);
        $pending = $request->session()->get('pending_generated_credential', []);
        if (($pending['name'] ?? '') !== $name || empty($pending['value'])) {
            return back()->with('error', 'No staged generated value is available for this credential.');
        }
        $response = $this->client->put('/api/v1/credentials/' . rawurlencode($name), ['value' => $pending['value']], $token);
        if ($response->successful()) {
            $request->session()->forget('pending_generated_credential');
        }

        return $this->redirectResponse($response, "{$name} generated value applied. Secret value was not logged.", 'Credential update failed.');
    }

    public function discardGeneratedCredential(Request $request): RedirectResponse
    {
        $request->session()->forget('pending_generated_credential');
        return back()->with('status', 'Staged generated value discarded.');
    }

    public function revealCredential(Request $request, string $name): RedirectResponse
    {
        $token = $this->requireToken($request);
        $response = $this->client->post('/api/v1/credentials/' . rawurlencode($name) . '/reveal', ['confirm' => true], $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'Credential reveal failed.'));
        }
        $body = $response->json() ?? [];
        $source = is_string($body['source'] ?? null) ? $body['source'] : 'credential_store';
        $sourceLabel = $source === 'runtime_env' ? 'runtime environment' : 'credential manager';

        return back()->with('generated_secret', [
            'name' => $name,
            'value' => $body['value'] ?? '',
            'message' => "Revealed from {$sourceLabel} for this browser session. Audit record created.",
        ]);
    }

    public function migrateRuntimeCredentials(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $response = $this->client->post('/api/v1/credentials/migrate-runtime', [], $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'Credential migration failed.'));
        }
        $body = $response->json() ?? [];
        $count = (int)($body['migrated_count'] ?? 0);
        return back()->with('status', "Runtime-to-DB credential migration complete. Migrated {$count} credential(s).");
    }

    public function updateDataSource(Request $request, string $sourceId): RedirectResponse
    {
        $token = $this->requireToken($request);
        $payload = $this->typedPayload($request, [
            'name', 'source_type', 'provider', 'date_range_mode', 'timezone',
        ], [
            'enabled' => 'boolean',
            'priority' => 'integer',
            'refresh_interval_minutes' => 'integer',
            'timeout_seconds' => 'integer',
            'retry_count' => 'integer',
            'backoff_seconds' => 'integer',
            'allowed_currencies' => 'csv',
            'allowed_impacts' => 'csv',
            'config_json' => 'json',
        ]);
        $response = $this->client->put('/api/v1/data-sources/' . rawurlencode($sourceId), $payload, $token);

        return $this->redirectResponse($response, 'Data source saved.', 'Data source update failed.');
    }

    public function scrapeCalendar(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $query = $request->input('source_id') ? '?source_id=' . rawurlencode((string) $request->input('source_id')) : '';
        $response = $this->client->post('/api/v1/calendar/scrape' . $query, [], $token);

        return $this->redirectResponse($response, 'Manual calendar scrape requested.', 'Calendar scrape request failed.');
    }

    public function updateAlertRule(Request $request, string $ruleId): RedirectResponse
    {
        $token = $this->requireToken($request);
        $payload = $this->typedPayload($request, ['name', 'severity'], [
            'enabled' => 'boolean',
            'currencies' => 'csv',
            'impacts' => 'csv',
            'event_keywords' => 'csv',
            'exact_event_names' => 'csv',
            'weekdays' => 'csv',
            'sources' => 'csv',
            'trading_pairs' => 'csv',
            'minutes_before' => 'integer',
            'delivery_targets' => 'csv',
        ]);
        $response = $this->client->put('/api/v1/alert-rules/' . rawurlencode($ruleId), $payload, $token);

        return $this->redirectResponse($response, 'Alert rule saved.', 'Alert rule update failed.');
    }

    public function testAlertRule(Request $request, string $ruleId): RedirectResponse
    {
        $response = $this->client->post('/api/v1/alert-rules/' . rawurlencode($ruleId) . '/test', [], $this->requireToken($request));
        return $this->redirectResponse($response, 'Test alert queued.', 'Test alert failed.');
    }

    public function workerAction(Request $request, string $workerId, string $action): RedirectResponse
    {
        $response = $this->client->post('/api/v1/workers/' . rawurlencode($workerId) . '/' . rawurlencode($action), [], $this->requireToken($request));
        return $this->redirectResponse($response, 'Worker action applied.', 'Worker action failed.');
    }

    public function recoverStaleAgents(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $validated = $request->validate([
            'stale_after_seconds' => ['nullable', 'integer', 'min:30', 'max:3600'],
            'queue_watchdog_review' => ['nullable', 'string'],
        ]);
        $staleAfter = (int)($validated['stale_after_seconds'] ?? 180);
        $queueWatchdog = $request->boolean('queue_watchdog_review');
        $query = http_build_query([
            'stale_after_seconds' => $staleAfter,
            'queue_watchdog_review' => $queueWatchdog ? 'true' : 'false',
        ]);
        $response = $this->client->post('/api/v1/agents/recover-stale?' . $query, [], $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'Stale recovery failed.'));
        }
        $body = $response->json() ?? [];
        $count = (int)($body['recovered_count'] ?? 0);
        return back()->with('status', "Stale recovery completed. Recovered {$count} agent states.");
    }

    public function setDemoTradingMode(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $validated = $request->validate([
            'account_id' => ['required', 'string', 'max:80'],
            'trading_mode' => ['required', 'string', 'in:monitor_only,demo_auto'],
        ]);
        $response = $this->client->post('/api/v1/risk/demo-trading-mode', $validated, $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'Unable to update demo trading mode.'));
        }

        $message = $validated['trading_mode'] === 'demo_auto'
            ? 'Demo auto-trading mode enabled (still guarded by Execution Guard and approvals).'
            : 'Demo trading set to monitor_only.';
        return back()->with('status', $message);
    }

    public function runDemoExecutionCycle(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $response = $this->client->post('/api/v1/trades/demo-auto/run', [], $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'Unable to run demo execution cycle.'));
        }
        $body = $response->json() ?? [];
        $sent = (int)($body['sent'] ?? 0);
        $blocked = (int)($body['blocked'] ?? 0);
        $failed = (int)($body['failed'] ?? 0);
        $skipped = (int)($body['skipped'] ?? 0);
        return back()->with('status', "Demo execution cycle completed. Sent {$sent}, blocked {$blocked}, failed {$failed}, skipped {$skipped}.");
    }

    public function sendOrchestratorChat(Request $request): RedirectResponse|JsonResponse
    {
        try {
            $token = $this->requireToken($request);
            $validated = $request->validate([
                'message' => ['required', 'string', 'min:1', 'max:800'],
                'language' => ['required', 'string', 'in:en,ms-MY,auto'],
            ]);
            $response = $this->client->post('/api/v1/agent-theater/chat', [
                'message' => $validated['message'],
                'language' => $validated['language'],
                'session_id' => 'laravel-orchestrator-console',
                'orchestrator_only' => true,
            ], $token);
        } catch (Throwable) {
            if ($request->expectsJson()) {
                return response()->json(['ok' => false, 'message' => 'Orchestrator request failed before reaching control API.'], 503);
            }
            return back()->with('error', 'Orchestrator request failed before reaching control API.');
        }

        if ($request->expectsJson()) {
            if (! $response->successful()) {
                $status = in_array($response->status(), [401, 403], true) ? 401 : 422;
                return response()->json(['ok' => false, 'message' => $this->errorMessage($response->json() ?? [], 'Orchestrator chat failed.')], $status);
            }
            $body = $response->json() ?? [];
            return response()->json([
                'ok' => true,
                'message' => 'Orchestrator replied.',
                'provider' => $body['provider'] ?? null,
                'fallback_reason' => $body['fallback_reason'] ?? null,
                'latency_ms' => $body['latency_ms'] ?? null,
            ]);
        }

        return $this->redirectResponse($response, 'Orchestrator replied. The dedicated console feed has been updated.', 'Orchestrator chat failed.');
    }

    public function seedAgentRoom(Request $request, string $roomName): RedirectResponse
    {
        $response = $this->client->post('/api/v1/agent-theater/rooms/' . rawurlencode($roomName) . '/seed', [], $this->requireToken($request));
        return $this->redirectResponse($response, "{$roomName} opened in Agent Theater.", 'Unable to open Agent Theater room.');
    }

    public function updateSetting(Request $request, string $settingKey): RedirectResponse
    {
        $token = $this->requireToken($request);
        $payload = $request->validate([
            'setting_value' => ['nullable', 'string', 'max:2000'],
            'value_type' => ['required', 'string', 'max:40'],
            'category' => ['required', 'string', 'max:80'],
        ]);
        $response = $this->client->put('/api/v1/config/settings/' . rawurlencode($settingKey), $payload, $token);

        return $this->redirectResponse($response, 'Setting saved.', 'Setting update failed.');
    }

    public function seedAnalysis(Request $request, string $analysisType): RedirectResponse
    {
        $response = $this->client->post('/api/v1/analysis/' . rawurlencode($analysisType) . '/seed-demo', [], $this->requireToken($request));
        return $this->redirectResponse($response, 'Analysis snapshot seed requested.', 'Analysis seed failed.');
    }

    public function openclawChat(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $validated = $request->validate([
            'role' => ['required', 'string', 'in:admin,user'],
            'language' => ['required', 'string', 'in:en,ms-MY,auto'],
            'message' => ['required', 'string', 'max:1200'],
        ]);
        $response = $this->client->post('/api/v1/openclaw/chat', $validated, $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'OpenClaw chat failed.'));
        }
        return back()->with('openclaw_result', $response->json() ?? [])->with('status', 'OpenClaw response received.');
    }

    public function openclawStatusQuery(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $validated = $request->validate([
            'target' => ['required', 'string', 'in:system,risk,signals,workers,news,accounts,pairs'],
            'language' => ['required', 'string', 'in:en,ms-MY,auto'],
        ]);
        $response = $this->client->post('/api/v1/openclaw/status/query', $validated, $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'OpenClaw status query failed.'));
        }
        return back()->with('openclaw_result', $response->json() ?? [])->with('status', 'OpenClaw status summary generated.');
    }

    public function openclawDailySummary(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $validated = $request->validate([
            'language' => ['required', 'string', 'in:en,ms-MY,auto'],
        ]);
        $response = $this->client->post('/api/v1/openclaw/summary/daily', $validated, $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'OpenClaw daily summary failed.'));
        }
        return back()->with('openclaw_result', $response->json() ?? [])->with('status', 'OpenClaw daily summary generated.');
    }

    public function openclawApprovedApiCall(Request $request): RedirectResponse
    {
        $token = $this->requireToken($request);
        $validated = $request->validate([
            'path' => ['required', 'string', 'in:/api/v1/system/runtime,/api/v1/system/health/status,/api/v1/workers/status,/api/v1/news/status,/api/v1/calendar/status,/api/v1/signals/summary,/api/v1/pair-summaries'],
            'reason' => ['nullable', 'string', 'max:300'],
        ]);
        $response = $this->client->post('/api/v1/openclaw/api-call', [
            'path' => $validated['path'],
            'approved' => true,
            'reason' => $validated['reason'] ?? '',
        ], $token);
        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'OpenClaw approved API call failed.'));
        }
        return back()->with('openclaw_result', $response->json() ?? [])->with('status', 'OpenClaw approved API call completed.');
    }

    private function render(Request $request, string $view, string $active, array $data = []): View
    {
        $token = $this->optionalToken($request);
        $authenticated = $token !== null;
        if ($authenticated && !app()->runningUnitTests()) {
            $me = $this->client->get('/api/v1/auth/me', $token, []);
            if (!isset($me['user_id']) || !is_string($me['user_id']) || $me['user_id'] === '') {
                $request->session()->forget(['control_tower_token', 'control_tower_refresh_token', 'control_tower_user']);
                $token = null;
                $authenticated = false;
            }
        }
        if (! $authenticated && $active !== 'login') {
            $view = 'pages.login';
            $active = 'login';
            $data = [];
        }
        // Use health data from page data if already fetched (e.g. overview pool), otherwise fetch it
        $runtime = $data['health'] ?? $this->client->get('/health', null, [
            'status' => 'unavailable',
            'environment' => 'demo',
            'trading_mode' => 'monitor_only',
            'live_auto_trading' => false,
        ]);

        return view($view, array_merge($data, [
            'active' => $active,
            'authenticated' => $authenticated,
            'userId' => $request->session()->get('control_tower_user'),
            'runtime' => $runtime,
            'links' => [
                'api' => config('control_tower.api_url'),
                'docs' => config('control_tower.docs_url'),
                'grafana' => config('control_tower.grafana_url'),
            ],
        ]));
    }

    private function tradingPairCreatePayload(Request $request): array
    {
        $validated = $request->validate([
            'symbol' => ['required', 'string', 'max:40'],
            'display_name' => ['nullable', 'string', 'max:80'],
            'enabled' => ['nullable', 'string'],
            'default_timeframe' => ['required', 'string', 'max:20'],
            'assigned_strategy_id' => ['nullable', 'string', 'max:100'],
            'additional_timeframes' => ['nullable', 'string', 'max:200'],
        ]);
        $defaultTimeframe = strtoupper($validated['default_timeframe']);
        $additionalTimeframes = $this->timeframeList($validated['additional_timeframes'] ?? '', $defaultTimeframe);
        return [
            'symbol' => strtoupper(trim($validated['symbol'])),
            'display_name' => $validated['display_name'] ?: strtoupper(trim($validated['symbol'])),
            'enabled' => $request->boolean('enabled'),
            'default_timeframe' => $defaultTimeframe,
            'assigned_strategy_id' => $validated['assigned_strategy_id'] ?: null,
            'status' => $request->boolean('enabled') ? 'enabled' : 'disabled',
            'metadata_json' => [
                'analysis_timeframes' => $additionalTimeframes,
            ],
        ];
    }

    private function tradingPairUpdatePayload(Request $request): array
    {
        $validated = $request->validate([
            'display_name' => ['nullable', 'string', 'max:80'],
            'enabled' => ['nullable', 'string'],
            'default_timeframe' => ['nullable', 'string', 'max:20'],
            'assigned_strategy_id' => ['nullable', 'string', 'max:100'],
            'additional_timeframes' => ['nullable', 'string', 'max:200'],
        ]);
        $defaultTimeframe = !empty($validated['default_timeframe']) ? strtoupper($validated['default_timeframe']) : 'M1';
        $additionalTimeframes = $this->timeframeList($validated['additional_timeframes'] ?? '', $defaultTimeframe);
        $payload = [
            'display_name' => $validated['display_name'] ?: null,
            'enabled' => $request->boolean('enabled'),
            'assigned_strategy_id' => $validated['assigned_strategy_id'] ?: null,
            'status' => $request->boolean('enabled') ? 'enabled' : 'disabled',
            'metadata_json' => [
                'analysis_timeframes' => $additionalTimeframes,
            ],
        ];
        if (!empty($validated['default_timeframe'])) {
            $payload['default_timeframe'] = $defaultTimeframe;
        }
        return $payload;
    }

    private function agentTheaterQuery(Request $request): string
    {
        $query = http_build_query(array_filter([
            'limit' => $request->query('limit', 100),
            'stream' => $request->query('stream'),
            'language' => $request->query('language', 'en'),
        ], fn ($value) => $value !== null && $value !== ''));
        foreach ((array) $request->query('agent', []) as $agent) {
            if ($agent !== '') {
                $query .= ($query ? '&' : '') . 'agent=' . rawurlencode((string) $agent);
            }
        }
        return $query;
    }

    private function optionalToken(Request $request): ?string
    {
        $token = (string) $request->session()->get('control_tower_token', '');
        return $token === '' ? null : $token;
    }

    private function requireToken(Request $request): string
    {
        $token = $this->optionalToken($request);
        if ($token === null && $this->refreshSessionToken($request)) {
            $token = $this->optionalToken($request);
        }
        abort_if($token === null, 403, 'Login required.');
        return $token;
    }

    private function refreshSessionToken(Request $request): bool
    {
        $refreshToken = (string) $request->session()->get('control_tower_refresh_token', '');
        if ($refreshToken === '') {
            return false;
        }
        $response = $this->client->post('/api/v1/auth/refresh', ['refresh_token' => $refreshToken], null);
        if (! $response->successful()) {
            $request->session()->forget(['control_tower_token', 'control_tower_refresh_token', 'control_tower_user']);
            return false;
        }
        $body = $response->json() ?? [];
        if (!is_string($body['access_token'] ?? null) || $body['access_token'] === '') {
            return false;
        }
        $request->session()->put('control_tower_token', $body['access_token']);
        if (is_string($body['refresh_token'] ?? null) && $body['refresh_token'] !== '') {
            $request->session()->put('control_tower_refresh_token', $body['refresh_token']);
        }
        return true;
    }

    private function typedPayload(Request $request, array $strings, array $typed): array
    {
        $payload = [];
        foreach ($strings as $field) {
            $payload[$field] = (string) $request->input($field, '');
        }
        foreach ($typed as $field => $type) {
            $value = $request->input($field);
            $payload[$field] = match ($type) {
                'boolean' => $request->boolean($field),
                'integer' => (int) $value,
                'csv' => $this->csv($value),
                'json' => $this->jsonObject($value),
                default => $value,
            };
        }
        return $payload;
    }

    private function csv(mixed $value): array
    {
        return array_values(array_filter(array_map(fn ($item) => trim((string) $item), explode(',', (string) $value))));
    }

    private function timeframeList(string $raw, string $defaultTimeframe): array
    {
        $allowed = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];
        $tokens = array_values(array_unique(array_map(
            fn ($item) => strtoupper(trim((string) $item)),
            explode(',', $raw)
        )));
        $selected = array_values(array_filter($tokens, fn ($item) => in_array($item, $allowed, true)));
        if (!in_array($defaultTimeframe, $selected, true)) {
            array_unshift($selected, $defaultTimeframe);
        }
        return array_values(array_unique($selected));
    }

    private function jsonObject(mixed $value): array
    {
        if (is_array($value)) {
            return $value;
        }
        $decoded = json_decode((string) $value, true);
        return is_array($decoded) ? $decoded : [];
    }

    private function groupCredentials(array $items): array
    {
        $groups = [];
        foreach ($items as $item) {
            $groups[$item['category'] ?? 'Other'][] = $item;
        }
        return $groups;
    }

    private function findCredential(array $items, string $name): array
    {
        foreach ($items as $item) {
            if (($item['name'] ?? '') === $name) {
                return $item;
            }
        }
        return [];
    }

    private function redirectResponse($response, string $success, string $fallback): RedirectResponse
    {
        if (! $response->successful()) {
            if (in_array($response->status(), [401, 403], true)) {
                Session::forget(['control_tower_token', 'control_tower_refresh_token', 'control_tower_user']);
                return redirect()->route('dashboard')->with('error', 'Session expired. Please login again.');
            }
            return back()->with('error', $this->errorMessage($response->json() ?? [], $fallback));
        }
        return back()->with('status', $success);
    }

    private function errorMessage(array $body, string $fallback): string
    {
        $detail = $body['detail'] ?? null;
        if (is_string($detail) && $detail !== '') {
            return $detail;
        }
        if (is_array($detail)) {
            $first = $detail[0] ?? null;
            if (is_array($first)) {
                $field = is_array($first['loc'] ?? null) ? implode('.', $first['loc']) : 'request';
                $msg = is_string($first['msg'] ?? null) ? $first['msg'] : 'invalid input';
                return "{$field}: {$msg}";
            }
        }
        return $fallback;
    }
}
