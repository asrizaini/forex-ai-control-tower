<?php

use App\Http\Controllers\DashboardController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DashboardController::class, 'index'])->name('dashboard');
Route::post('/login', [DashboardController::class, 'login'])->name('login');
Route::post('/logout', [DashboardController::class, 'logout'])->name('logout');
Route::post('/password', [DashboardController::class, 'updatePassword'])->name('password.update');
Route::post('/credentials/discard-generated', [DashboardController::class, 'discardGeneratedCredential'])->name('credentials.discard-generated');
Route::post('/credentials/{name}', [DashboardController::class, 'updateCredential'])->name('credentials.update');
Route::post('/credentials/{name}/generate', [DashboardController::class, 'generateCredential'])->name('credentials.generate');
Route::post('/credentials/{name}/apply-generated', [DashboardController::class, 'applyGeneratedCredential'])->name('credentials.apply-generated');
Route::post('/credentials/{name}/reveal', [DashboardController::class, 'revealCredential'])->name('credentials.reveal');
