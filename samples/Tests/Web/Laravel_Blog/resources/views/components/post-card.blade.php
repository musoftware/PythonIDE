@props(['post'])

<article {{ $attributes->merge(['class' => 'bg-white shadow-sm sm:rounded-lg p-6']) }}>
    <h3 class="text-lg font-semibold text-gray-900">
        <a href="{{ route('posts.show', $post) }}" class="hover:underline">{{ $post->title }}</a>
        @unless ($post->published)
            <span class="ml-2 text-xs text-yellow-700 bg-yellow-100 rounded px-2 py-0.5">{{ __('blog.draft') }}</span>
        @endunless
    </h3>
    <p class="text-sm text-gray-500 mt-1">
        {{ $post->user->name }} &middot; {{ $post->published_at?->diffForHumans() }}
        @isset($post->comments_count)
            &middot; {{ trans_choice('blog.comments', $post->comments_count) }}
        @endisset
    </p>
    <p class="mt-3 text-gray-700">{{ $post->excerpt }}</p>
</article>
