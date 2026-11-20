<?php

namespace App\Http\Controllers;

use App\Models\Post;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

class CommentController extends Controller
{
    /** POST /posts/{post:slug}/comments - guests give a name, signed-in users comment as themselves. */
    public function store(Request $request, Post $post): RedirectResponse
    {
        $data = $request->validate([
            'author' => auth()->check() ? 'nullable|string|max:80' : 'required|string|max:80',
            'body' => 'required|string|min:2|max:2000',
        ]);
        $post->comments()->create([
            'author' => $request->user()?->name ?? $data['author'],
            'body' => $data['body'],
            'user_id' => $request->user()?->id,
        ]);

        return redirect()->to(route('posts.show', $post).'#comments')->with('status', __('blog.commented'));
    }
}
