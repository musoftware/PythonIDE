<?php

namespace App\Http\Controllers;

use App\Models\Post;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\View\View;

class PostController extends Controller
{
    /** GET /posts - published posts, newest first, with a search box. */
    public function index(Request $request): View
    {
        $search = trim((string) $request->query('q', ''));
        $posts = Post::published()
            ->with('user')
            ->withCount('comments')
            ->when($search !== '', fn ($q) => $q->where('title', 'like', "%{$search}%"))
            ->latest('published_at')
            ->paginate(config('blog.per_page'))
            ->withQueryString();

        return view('posts.index', compact('posts', 'search'));
    }

    /** GET /posts/{post:slug} */
    public function show(Post $post): View
    {
        abort_unless($post->published || $post->user_id === auth()->id(), 404);
        $post->load('user', 'comments');

        return view('posts.show', ['post' => $post]);
    }

    /** GET /posts/create */
    public function create(): View
    {
        return view('posts.create', ['post' => new Post(['published' => true])]);
    }

    /** POST /posts */
    public function store(Request $request): RedirectResponse
    {
        $data = $this->validated($request);
        $post = $request->user()->posts()->create($data + [
            'slug' => $this->uniqueSlug($data['title']),
            'published_at' => ($data['published'] ?? false) ? now() : null,
        ]);

        return redirect()->route('posts.show', $post)->with('status', __('blog.created'));
    }

    /** GET /posts/{post:slug}/edit */
    public function edit(Post $post): View
    {
        $this->authorizeOwner($post);

        return view('posts.edit', compact('post'));
    }

    /** PUT /posts/{post:slug} */
    public function update(Request $request, Post $post): RedirectResponse
    {
        $this->authorizeOwner($post);
        $data = $this->validated($request);
        if (($data['published'] ?? false) && ! $post->published_at) {
            $data['published_at'] = now();
        }
        $post->update($data);

        return redirect()->route('posts.show', $post)->with('status', __('blog.updated'));
    }

    /** DELETE /posts/{post:slug} */
    public function destroy(Post $post): RedirectResponse
    {
        $this->authorizeOwner($post);
        $post->delete();

        return to_route('posts.index')->with('status', __('blog.deleted'));
    }

    private function validated(Request $request): array
    {
        $data = $request->validate([
            'title' => 'required|string|min:3|max:150',
            'body' => 'required|string|min:10',
            'published' => 'sometimes|boolean',
        ]);
        $data['published'] = $request->boolean('published');

        return $data;
    }

    private function authorizeOwner(Post $post): void
    {
        abort_unless($post->user_id === auth()->id(), 403, __('blog.not_owner'));
    }

    private function uniqueSlug(string $title): string
    {
        $base = Str::slug($title) ?: 'post';
        $slug = $base;
        for ($i = 2; Post::where('slug', $slug)->exists(); $i++) {
            $slug = "{$base}-{$i}";
        }

        return $slug;
    }
}
