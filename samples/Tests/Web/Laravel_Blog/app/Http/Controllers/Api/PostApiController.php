<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Post;
use Illuminate\Http\JsonResponse;

class PostApiController extends Controller
{
    /** GET /api/posts - JSON list (paginated). */
    public function index(): JsonResponse
    {
        $posts = Post::published()->with('user:id,name')->withCount('comments')
            ->latest('published_at')->paginate(config('blog.per_page'));

        return response()->json($posts);
    }

    /** GET /api/posts/{post:slug} */
    public function show(Post $post): JsonResponse
    {
        abort_unless($post->published, 404);

        return response()->json($post->load('user:id,name', 'comments'));
    }
}
