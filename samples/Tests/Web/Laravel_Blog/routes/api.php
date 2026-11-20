<?php

use App\Http\Controllers\Api\PostApiController;
use Illuminate\Support\Facades\Route;

// JSON API (prefix /api, see bootstrap/app.php) - try it in the REST client or the Preview
Route::get('/posts', [PostApiController::class, 'index'])->name('api.posts.index');
Route::get('/posts/{post}', [PostApiController::class, 'show'])->name('api.posts.show');
Route::get('/status', fn () => [
    'app' => config('app.name'),
    'laravel' => app()->version(),
    'posts' => \App\Models\Post::count(),
])->name('api.status');
