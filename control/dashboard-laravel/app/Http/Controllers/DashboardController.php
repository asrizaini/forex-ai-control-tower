<?php

namespace App\Http\Controllers;

use App\Services\ControlTowerClient;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

class DashboardController extends Controller
{
    public function __construct(private readonly ControlTowerClient $client)
    {
    }

    public function overview(Request $request): View
    {
        return $this->render($request, 'pages.overview', 'overview', [
            'health' => $this->client->get('/health', null, ['status' => 'unavailable']),
            'apiStatus' => $this->client->get('/api/v1/api/status', null, ['status' => 'unavailable', 'services' => []]),
            'healthStatus' => $this->client->get('/api/v1/system/health/status', null, ['healthy' => false, 'services' => []]),
            'calendarStatus' => $this->client->get('/api/v1/calendar/status', null, ['status' => 'unavailable', 'sources' => []]),
            'newsStatus' => $this->client->get('/api/v1/news/status', null, ['risk_status' => 'unavailable']),
            'workers' => $this->client->get('/api/v1/workers/status', null, ['workers' => []]),
            'readiness' => $this->client->get('/api/v1/system/production-readiness', null, []),
            'auditLogs' => $this->client->get('/api/v1/logs/audit?limit=8', null, ['items' => []]),
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
        $request->session()->put('control_tower_token', $body['access_token'] ?? '');
        $request->session()->put('control_tower_user', $validated['user_id']);
        $request->session()->regenerate();

        return redirect()->route('dashboard.overview')->with('status', 'Logged in.');
    }

    public function logout(Request $request): RedirectResponse
    {
        $request->session()->forget(['control_tower_token', 'control_tower_user']);
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

        return back()->with('generated_secret', [
            'name' => $name,
            'value' => $body['value'] ?? '',
            'message' => 'Revealed for this browser session. Audit record created.',
        ]);
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
        return $this->redirectResponse($response, 'Worker action queued.', 'Worker action failed.');
    }

    public function sendOrchestratorChat(Request $request): RedirectResponse|JsonResponse
    {
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

        if ($request->expectsJson()) {
            if (! $response->successful()) {
                return response()->json(['ok' => false, 'message' => $this->errorMessage($response->json() ?? [], 'Orchestrator chat failed.')], 422);
            }
            return response()->json(['ok' => true, 'message' => 'Orchestrator replied.']);
        }

        return $this->redirectResponse($response, 'Orchestrator replied. The dedicated console feed has been updated.', 'Orchestrator chat failed.');
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

    private function render(Request $request, string $view, string $active, array $data = []): View
    {
        return view($view, array_merge($data, [
            'active' => $active,
            'authenticated' => (bool) $request->session()->get('control_tower_token'),
            'userId' => $request->session()->get('control_tower_user'),
            'links' => [
                'api' => config('control_tower.api_url'),
                'docs' => config('control_tower.docs_url'),
                'grafana' => config('control_tower.grafana_url'),
            ],
        ]));
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
        abort_if($token === null, 403, 'Login required.');
        return $token;
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
            return back()->with('error', $this->errorMessage($response->json() ?? [], $fallback));
        }
        return back()->with('status', $success);
    }

    private function errorMessage(array $body, string $fallback): string
    {
        $detail = $body['detail'] ?? null;
        return is_string($detail) ? $detail : $fallback;
    }
}
