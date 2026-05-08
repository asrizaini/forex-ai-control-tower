<?php
require '/opt/forex-ai-control-tower/dashboard-laravel/vendor/autoload.php';
$app = require '/opt/forex-ai-control-tower/dashboard-laravel/bootstrap/app.php';
$app->make('Illuminate\Contracts\Console\Kernel')->bootstrap();

$responses = Illuminate\Support\Facades\Http::pool([
    'health' => function($pool) {
        return $pool->timeout(5)->get('http://10.10.1.81:8000/health');
    },
    'status' => function($pool) {
        return $pool->timeout(5)->get('http://10.10.1.81:8000/api/v1/api/status');
    },
]);

echo "health: " . $responses['health']->status() . "\n";
echo "status: " . $responses['status']->status() . "\n";
echo "health body: " . $responses['health']->body() . "\n";