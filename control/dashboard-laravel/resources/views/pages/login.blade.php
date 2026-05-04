@extends('layouts.control', [
    'title' => 'Forex AI Control Tower',
    'description' => 'Secure operator login for fx-control.',
    'eyebrow' => 'Authentication',
])

@section('content')
<section class="panel" style="max-width:720px;margin:auto">
    <div class="panel-head">
        <div>
            <h2>Secure Login</h2>
            <p>Sign in to manage trading pairs, analysis, signals, strategies, testing, workers, credentials, and monitoring.</p>
        </div>
        <span class="badge warn">required</span>
    </div>
    <form class="stack" method="POST" action="{{ route('login') }}">
        @csrf
        <label>User ID
            <input name="user_id" value="admin" autocomplete="username" aria-label="User ID">
        </label>
        <label>Password
            <input name="password" type="password" autocomplete="current-password" aria-label="Password">
        </label>
        <label>2FA Code
            <input name="totp_code" autocomplete="one-time-code" placeholder="Only if enabled" aria-label="2FA code">
        </label>
        <button type="submit">Login</button>
    </form>
</section>
@endsection
