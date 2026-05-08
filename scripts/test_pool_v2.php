<?php
require_once '/opt/forex-ai-control-tower/dashboard-laravel/vendor/autoload.php';
$app = require_once '/opt/forex-ai-control-tower/dashboard-laravel/bootstrap/app.php';
$app->make('Illuminate\Contracts\Console\Kernel')->bootstrap();

use Illuminate\Support\Facades\Http;
use Illuminate\Http\Client\Pool;

// Test 1: Simple pool with as() key naming
echo "=== Test 1: Simple pool with as() key naming ===\n";
try {
    $responses = Http::pool(function (Pool $pool) {
        $pool->as('health')->timeout(15)->acceptJson()->get('http://10.10.1.81:8000/health');
        $pool->as('auth_me')->timeout(15)->acceptJson()->withToken('test')->get('http://10.10.1.81:8000/api/v1/auth/me');
    });
    echo "Responses type: " . gettype($responses) . "\n";
    echo "Responses keys: " . json_encode(array_keys($responses)) . "\n";
    foreach ($responses as $key => $response) {
        if ($response instanceof \Illuminate\Http\Client\Response) {
            echo "  $key: status=" . $response->status() . " body=" . substr($response->body(), 0, 100) . "\n";
        } else {
            echo "  $key: type=" . gettype($response) . " value=" . substr((string)$response, 0, 100) . "\n";
        }
    }
} catch (\Throwable $e) {
    echo "Error: " . get_class($e) . " - " . $e->getMessage() . "\n";
}

// Test 2: Pool without as() key naming (numeric keys)
echo "\n=== Test 2: Pool without as() key naming ===\n";
try {
    $responses = Http::pool(function (Pool $pool) {
        return [
            $pool->timeout(15)->acceptJson()->get('http://10.10.1.81:8000/health'),
        ];
    });
    echo "Responses type: " . gettype($responses) . "\n";
    echo "Responses keys: " . json_encode(array_keys($responses)) . "\n";
    foreach ($responses as $key => $response) {
        if ($response instanceof \Illuminate\Http\Client\Response) {
            echo "  $key: status=" . $response->status() . " body=" . substr($response->body(), 0, 100) . "\n";
        } else {
            echo "  $key: type=" . gettype($response) . " value=" . substr((string)$response, 0, 100) . "\n";
        }
    }
} catch (\Throwable $e) {
    echo "Error: " . get_class($e) . " - " . $e->getMessage() . "\n";
}

// Test 3: ControlTowerClient getPool
echo "\n=== Test 3: ControlTowerClient getPool ===\n";
try {
    $client = app(\App\Services\ControlTowerClient::class);
    $result = $client->getPool([
        'health' => '/health',
        '__fallback_health' => ['status' => 'unavailable'],
        'auth_me' => '/api/v1/auth/me',
        '__fallback_auth_me' => ['status' => 'unavailable'],
    ]);
    echo "Result keys: " . json_encode(array_keys($result)) . "\n";
    echo "Result: " . json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n";
} catch (\Throwable $e) {
    echo "Error: " . get_class($e) . " - " . $e->getMessage() . "\n";
    echo "Trace: " . $e->getTraceAsString() . "\n";
}