<?php

namespace App\Services;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;

class ControlTowerClient
{
    public function get(string $path, ?string $token = null, array $fallback = []): array
    {
        try {
            $response = $this->request($token)->get($this->url($path));
        } catch (ConnectionException) {
            return $fallback;
        }

        return $response->successful() ? ($response->json() ?? $fallback) : $fallback;
    }

    public function post(string $path, array $payload = [], ?string $token = null): Response
    {
        return $this->request($token)->post($this->url($path), $payload);
    }

    public function put(string $path, array $payload = [], ?string $token = null): Response
    {
        return $this->request($token)->put($this->url($path), $payload);
    }

    public function delete(string $path, array $payload = [], ?string $token = null): Response
    {
        return $this->request($token)->delete($this->url($path), $payload);
    }

    private function request(?string $token)
    {
        $request = Http::timeout(8)->acceptJson()->asJson();
        if ($token) {
            $request = $request->withToken($token);
        }
        return $request;
    }

    private function url(string $path): string
    {
        return rtrim(config('control_tower.api_url'), '/') . '/' . ltrim($path, '/');
    }
}
