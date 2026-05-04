<?php

use App\Http\Controllers\DashboardController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DashboardController::class, 'loginPage'])->name('dashboard');
Route::get('/overview', [DashboardController::class, 'overview'])->name('dashboard.overview');
Route::get('/trading-pairs', [DashboardController::class, 'tradingPairs'])->name('dashboard.trading-pairs');
Route::get('/pair-summary', [DashboardController::class, 'pairSummary'])->name('dashboard.pair-summary');
Route::get('/signals', [DashboardController::class, 'signals'])->name('dashboard.signals');
Route::get('/strategy', [DashboardController::class, 'strategy'])->name('dashboard.strategy');
Route::get('/candle-analysis', [DashboardController::class, 'candleAnalysis'])->name('dashboard.candle-analysis');
Route::get('/trend-analysis', [DashboardController::class, 'trendAnalysis'])->name('dashboard.trend-analysis');
Route::get('/risk-validation', [DashboardController::class, 'riskValidation'])->name('dashboard.risk-validation');
Route::get('/testing', [DashboardController::class, 'testing'])->name('dashboard.testing');
Route::get('/credentials', [DashboardController::class, 'credentials'])->name('dashboard.credentials');
Route::get('/data-sources', [DashboardController::class, 'dataSources'])->name('dashboard.data-sources');
Route::get('/calendar', [DashboardController::class, 'calendar'])->name('dashboard.calendar');
Route::get('/news', [DashboardController::class, 'news'])->name('dashboard.news');
Route::get('/alert-rules', [DashboardController::class, 'alertRules'])->name('dashboard.alert-rules');
Route::get('/workers', [DashboardController::class, 'workers'])->name('dashboard.workers');
Route::get('/agent-theater', [DashboardController::class, 'agentTheater'])->name('dashboard.agent-theater');
Route::get('/agent-theater/feed', [DashboardController::class, 'agentTheaterFeed'])->name('agent-theater.feed');
Route::get('/orchestrator-console', [DashboardController::class, 'orchestratorConsole'])->name('dashboard.orchestrator-console');
Route::get('/orchestrator-console/feed', [DashboardController::class, 'orchestratorConsoleFeed'])->name('orchestrator-console.feed');
Route::get('/technical-analysis', [DashboardController::class, 'technical'])->name('dashboard.technical');
Route::get('/fundamental-analysis', [DashboardController::class, 'fundamental'])->name('dashboard.fundamental');
Route::get('/monitoring', [DashboardController::class, 'monitoring'])->name('dashboard.monitoring');
Route::get('/api-status', [DashboardController::class, 'apiStatus'])->name('dashboard.api-status');
Route::get('/logs', [DashboardController::class, 'logs'])->name('dashboard.logs');
Route::get('/settings', [DashboardController::class, 'settings'])->name('dashboard.settings');

Route::post('/login', [DashboardController::class, 'login'])->name('login');
Route::post('/logout', [DashboardController::class, 'logout'])->name('logout');
Route::post('/password', [DashboardController::class, 'updatePassword'])->name('password.update');
Route::post('/trading-pairs', [DashboardController::class, 'createTradingPair'])->name('trading-pairs.create');
Route::post('/trading-pairs/{symbol}', [DashboardController::class, 'updateTradingPair'])->name('trading-pairs.update');
Route::post('/analysis/run', [DashboardController::class, 'runAnalysis'])->name('analysis.run');
Route::post('/testing/backtests/run', [DashboardController::class, 'runBacktest'])->name('testing.backtests.run');
Route::post('/credentials/discard-generated', [DashboardController::class, 'discardGeneratedCredential'])->name('credentials.discard-generated');
Route::post('/credentials/{name}', [DashboardController::class, 'updateCredential'])->name('credentials.update');
Route::post('/credentials/{name}/generate', [DashboardController::class, 'generateCredential'])->name('credentials.generate');
Route::post('/credentials/{name}/apply-generated', [DashboardController::class, 'applyGeneratedCredential'])->name('credentials.apply-generated');
Route::post('/credentials/{name}/reveal', [DashboardController::class, 'revealCredential'])->name('credentials.reveal');

Route::post('/data-sources/{sourceId}', [DashboardController::class, 'updateDataSource'])->name('data-sources.update');
Route::post('/calendar/scrape', [DashboardController::class, 'scrapeCalendar'])->name('calendar.scrape');
Route::post('/alert-rules/{ruleId}', [DashboardController::class, 'updateAlertRule'])->name('alert-rules.update');
Route::post('/alert-rules/{ruleId}/test', [DashboardController::class, 'testAlertRule'])->name('alert-rules.test');
Route::post('/workers/{workerId}/{action}', [DashboardController::class, 'workerAction'])->name('workers.action');
Route::post('/agent-theater/chat', [DashboardController::class, 'sendOrchestratorChat'])->name('agent-theater.chat');
Route::post('/agent-theater/rooms/{roomName}/seed', [DashboardController::class, 'seedAgentRoom'])->name('agent-theater.rooms.seed');
Route::post('/settings/{settingKey}', [DashboardController::class, 'updateSetting'])->name('settings.update');
Route::post('/analysis/{analysisType}/seed', [DashboardController::class, 'seedAnalysis'])->name('analysis.seed');
