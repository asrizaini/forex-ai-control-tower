<?php

use App\Http\Controllers\DashboardController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DashboardController::class, 'index'])->name('dashboard');
Route::post('/login', [DashboardController::class, 'login'])->name('login');
Route::post('/logout', [DashboardController::class, 'logout'])->name('logout');
Route::post('/credentials/{name}', [DashboardController::class, 'updateCredential'])->name('credentials.update');
Route::post('/credentials/{name}/generate', [DashboardController::class, 'generateCredential'])->name('credentials.generate');
Route::post('/credentials/{name}/reveal', [DashboardController::class, 'revealCredential'])->name('credentials.reveal');
