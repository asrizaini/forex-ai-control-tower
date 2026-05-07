<?php

namespace App\Services;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Session;

class ControlTowerClient
{
    public function get(string $path, ?string $token = null, array $fallback = []): array
    {
        try {
            $response = $this->send('GET', $path, [], $token);
        } catch (ConnectionException) {
            return $fallback;
        }

        return $response->successful() ? ($response->json() ?? $fallback) : $fallback;
    }

    public function post(string $path, array $payload = [], ?string $token = null): Response
    {
        return $this->send('POST', $path, $payload, $token);
    }

    public function put(string $path, array $payload = [], ?string $token = null): Response
    {
        return $this->send('PUT', $path, $payload, $token);
    }

    public function delete(string $path, array $payload = [], ?string $token = null): Response
    {
        return $this->send('DELETE', $path, $payload, $token);
    }

    /**
     * Fetch multiple API endpoints concurrently using HTTP pool.
     * Returns an associative array keyed by the provided keys.
     * Each value is either the decoded JSON response or the provided fallback.
     */
    public function getPool(array $requests, ?string $token = null): array
    {
        $resolvedToken = $this->resolveToken($token);
        $baseUrl = rtrim(config('control_tower.api_url'), '/');
        $pending = [];
        foreach ($requests as $key => $path) {
            $url = $baseUrl . '/' . ltrim($path, '/');
            $pending[$key] = $this->buildPoolRequest($url, $resolvedToken);
        }
        try {
            $responses = Http::pool($pending);
        } catch (\Throwable) {
            $responses = [];
        }
        $results = [];
        foreach ($requests as $key => $path) {
            $response = $responses[$key] ?? null;
            $fallback = $requests['__fallback_' . $key] ?? [];
            if ($response instanceof Response && $response->successful()) {
                $results[$key] = $response->json() ?? $fallback;
            } else {
                $results[$key] = $fallback;
            }
        }
        return $results;
    }

    private function buildPoolRequest(string $url, ?string $token): \Closure
    {
        return function ($pool) use ($url, $token) {
            $request = $pool->timeout(5)->acceptJson()->asJson();
            if ($token) {
                $request = $request->withToken($token);
            }
            return $request->get($url);
        };
    }

    private function send(string $method, string $path, array $payload = [], ?string $token = null, bool $allowRefresh = true): Response
    {
        $resolvedToken = $this->resolveToken($token);
        $request = $this->request($resolvedToken);
        $url = $this->url($path);
        $response = match (strtoupper($method)) {
            'GET' => $request->get($url),
            'POST' => $request->post($url, $payload),
            'PUT' => $request->put($url, $payload),
            'DELETE' => $request->delete($url, $payload),
            default => $request->send($method, $url, ['json' => $payload]),
        };

        if ($response->status() === 401 && $allowRefresh && $this->refreshSessionToken()) {
            return $this->send($method, $path, $payload, $this->resolveToken(null), false);
        }

        if ($response->status() === 401) {
            $this->clearSessionToken();
        }
        return $response;
    }

    private function request(?string $token)
    {
        $request = Http::timeout(5)->acceptJson()->asJson();
        if ($token) {
            $request = $request->withToken($token);
        }
        return $request;
    }

    private function url(string $path): string
    {
        return rtrim(config('control_tower.api_url'), '/') . '/' . ltrim($path, '/');
    }

    private function resolveToken(?string $token): ?string
    {
        if ($token) {
            return $token;
        }
        $sessionToken = Session::get('control_tower_token');
        return is_string($sessionToken) && $sessionToken !== '' ? $sessionToken : null;
    }

    private function refreshSessionToken(): bool
    {
        $refreshToken = Session::get('control_tower_refresh_token');
        if (!is_string($refreshToken) || $refreshToken === '') {
            return false;
        }
        try {
            $response = Http::timeout(5)
                ->acceptJson()
                ->asJson()
                ->post($this->url('/api/v1/auth/refresh'), ['refresh_token' => $refreshToken]);
        } catch (ConnectionException) {
            return false;
        }
        if (!$response->successful()) {
            return false;
        }
        $body = $response->json() ?? [];
        $accessToken = $body['access_token'] ?? null;
        $newRefreshToken = $body['refresh_token'] ?? null;
        if (!is_string($accessToken) || $accessToken === '') {
            return false;
        }
        Session::put('control_tower_token', $accessToken);
        if (is_string($newRefreshToken) && $newRefreshToken !== '') {
            Session::put('control_tower_refresh_token', $newRefreshToken);
        }
        return true;
    }

    private function clearSessionToken(): void
    {
        Session::forget(['control_tower_token', 'control_tower_refresh_token', 'control_tower_user']);
    }
}
