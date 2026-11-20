<?php

namespace Database\Seeders;

use App\Models\Comment;
use App\Models\Post;
use App\Models\User;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    /** php artisan db:seed - a demo author (demo@example.com / password) with posts and comments. */
    public function run(): void
    {
        $demo = User::firstOrCreate(['email' => 'demo@example.com'], [
            'name' => 'Demo Author',
            'password' => 'password',
            'email_verified_at' => now(),
        ]);

        Post::factory(8)->for($demo)
            ->has(Comment::factory()->count(3))
            ->create();

        Post::factory()->for($demo)->create([
            'title' => 'Welcome to the Laravel Blog',
            'slug' => 'welcome',
            'body' => "This sample was made in RAD IDE.\n\nTry IntelliSense: route('|'), view('|'), config('blog.|'), \$post->| and @fo| in a Blade file.",
            'published_at' => now(),
        ]);
    }
}
