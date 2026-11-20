<x-app-layout>
    <x-slot name="header">
        <h2 class="font-semibold text-xl text-gray-800 leading-tight">{{ $post->title }}</h2>
    </x-slot>

    <div class="py-8">
        <div class="max-w-4xl mx-auto sm:px-6 lg:px-8 space-y-6">
            @if (session('status'))
                <x-alert :message="session('status')" />
            @endif

            <article class="bg-white shadow-sm sm:rounded-lg p-6">
                <p class="text-sm text-gray-500">
                    {{ $post->user->name }} &middot; {{ $post->published_at?->toFormattedDateString() ?? __('blog.draft') }}
                </p>
                <div class="mt-4 space-y-4 text-gray-800">
                    @foreach (preg_split("/\n\s*\n/", $post->body) as $paragraph)
                        <p>{{ $paragraph }}</p>
                    @endforeach
                </div>

                @if (auth()->id() === $post->user_id)
                    <div class="mt-6 flex gap-3">
                        <a href="{{ route('posts.edit', $post) }}" class="text-indigo-600 hover:underline">{{ __('blog.edit_post') }}</a>
                        <form method="POST" action="{{ route('posts.destroy', $post) }}" onsubmit="return confirm('Delete this post?')">
                            @csrf
                            @method('DELETE')
                            <button class="text-red-600 hover:underline">Delete</button>
                        </form>
                    </div>
                @endif
            </article>

            <section id="comments" class="bg-white shadow-sm sm:rounded-lg p-6">
                <h3 class="font-semibold text-lg">{{ trans_choice('blog.comments', $post->comments->count()) }}</h3>
                @foreach ($post->comments as $comment)
                    <div class="border-t mt-3 pt-3">
                        <p class="text-sm text-gray-500">{{ $comment->author }} &middot; {{ $comment->created_at->diffForHumans() }}</p>
                        <p>{{ $comment->body }}</p>
                    </div>
                @endforeach

                @if (config('blog.comments.enabled'))
                    <form method="POST" action="{{ route('posts.comments.store', $post) }}" class="mt-4 space-y-3">
                        @csrf
                        @guest
                            <div>
                                <x-input-label for="author" value="Name" />
                                <x-text-input id="author" name="author" :value="old('author')" class="block w-full" />
                                <x-input-error :messages="$errors->get('author')" />
                            </div>
                        @endguest
                        <div>
                            <x-input-label for="body" value="Comment" />
                            <textarea id="body" name="body" rows="3" class="block w-full border-gray-300 rounded-md">{{ old('body') }}</textarea>
                            <x-input-error :messages="$errors->get('body')" />
                        </div>
                        <x-primary-button>Add comment</x-primary-button>
                    </form>
                @endif
            </section>
        </div>
    </div>
</x-app-layout>
