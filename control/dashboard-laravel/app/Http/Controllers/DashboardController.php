<?php

namespace App\Http\Controllers;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use Illuminate\View\View;

class DashboardController extends Controller
{
    public function index(): View
    {
        return view('dashboard', [
            'health' => $this->getJson('/health'),
            'readiness' => $this->getJson('/api/v1/system/production-readiness'),
            'market' => $this->getJson('/api/v1/telemetry/market/latest?limit=8', []),
            'links' => [
                'api' => config('control_tower.api_url'),
                'docs' => config('control_tower.docs_url'),
                'grafana' => config('control_tower.grafana_url'),
            ],
        ]);
    }

    private function getJson(string $path, array $fallback = ['status' => 'unavailable']): array
    {
        try {
            $response = Http::timeout(4)->acceptJson()->get(config('control_tower.api_url') . $path);
        } catch (ConnectionException) {
            return $fallback;
        }

        if (! $response->successful()) {
            return $fallback;
        }

        return $response->json() ?? $fallback;
    }
}
