<?php

namespace App\Http\Controllers;

use App\Services\ControlTowerClient;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

class DashboardController extends Controller
{
    public function __construct(private readonly ControlTowerClient $client)
    {
    }

    public function index(Request $request): View
    {
        $token = $request->session()->get('control_tower_token');
        $credentials = $token
            ? $this->client->get('/api/v1/credentials/status', $token, ['items' => [], 'healthy' => false])
            : ['items' => [], 'healthy' => false, 'notes' => 'Login required.'];

        return view('dashboard', [
            'authenticated' => (bool) $token,
            'health' => $this->client->get('/health', null, ['status' => 'unavailable']),
            'healthStatus' => $this->client->get('/api/v1/system/health/status', null, ['healthy' => false, 'services' => []]),
            'readiness' => $this->client->get('/api/v1/system/production-readiness', null, []),
            'market' => $this->client->get('/api/v1/telemetry/market/latest?limit=8', null, []),
            'accounts' => $this->client->get('/api/v1/telemetry/accounts/latest?limit=1', null, []),
            'agentEvents' => $this->client->get('/api/v1/agent-theater/events?limit=8', null, ['events' => []]),
            'credentials' => $credentials,
            'credentialGroups' => $this->groupCredentials($credentials['items'] ?? []),
            'links' => [
                'api' => config('control_tower.api_url'),
                'docs' => config('control_tower.docs_url'),
                'grafana' => config('control_tower.grafana_url'),
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
        $request->session()->put('control_tower_token', $body['access_token'] ?? '');
        $request->session()->put('control_tower_user', $validated['user_id']);
        $request->session()->regenerate();

        return redirect()->route('dashboard')->with('status', 'Logged in.');
    }

    public function logout(Request $request): RedirectResponse
    {
        $request->session()->forget(['control_tower_token', 'control_tower_user']);
        $request->session()->regenerateToken();

        return redirect()->route('dashboard')->with('status', 'Logged out.');
    }

    public function updateCredential(Request $request, string $name): RedirectResponse
    {
        $token = $this->requireToken($request);
        $validated = $request->validate([
            'value' => ['nullable', 'string'],
        ]);

        $response = $this->client->put('/api/v1/credentials/' . rawurlencode($name), [
            'value' => $validated['value'] ?? '',
        ], $token);

        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'Credential update failed.'));
        }

        return back()->with('status', "{$name} saved. Secret value was not logged.");
    }

    public function generateCredential(Request $request, string $name): RedirectResponse
    {
        $token = $this->requireToken($request);
        $response = $this->client->post('/api/v1/credentials/' . rawurlencode($name) . '/generate', [], $token);

        if (! $response->successful()) {
            return back()->with('error', $this->errorMessage($response->json() ?? [], 'Credential generation failed.'));
        }

        $body = $response->json() ?? [];

        return back()->with('generated_secret', [
            'name' => $name,
            'value' => $body['value'] ?? '',
            'message' => 'Generated value is shown once. Save it when ready.',
        ]);
    }

    public function revealCredential(Request $request, string $name): RedirectResponse
    {
        $token = $this->requireToken($request);
        $response = $this->client->post('/api/v1/credentials/' . rawurlencode($name) . '/reveal', [
            'confirm' => true,
        ], $token);

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

    private function requireToken(Request $request): string
    {
        $token = (string) $request->session()->get('control_tower_token', '');
        abort_if($token === '', 403, 'Login required.');
        return $token;
    }

    private function groupCredentials(array $items): array
    {
        $groups = [];
        foreach ($items as $item) {
            $groups[$item['category'] ?? 'Other'][] = $item;
        }
        return $groups;
    }

    private function errorMessage(array $body, string $fallback): string
    {
        $detail = $body['detail'] ?? null;
        return is_string($detail) ? $detail : $fallback;
    }
}
