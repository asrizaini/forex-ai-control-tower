<?php

return [
    'api_url' => rtrim(env('CONTROL_TOWER_API_URL', 'http://10.10.1.81:8000'), '/'),
    'docs_url' => env('CONTROL_TOWER_DOCS_URL', 'http://10.10.1.81:8000/docs'),
    'grafana_url' => env('CONTROL_TOWER_GRAFANA_URL', 'http://10.10.1.81:3000'),
];
