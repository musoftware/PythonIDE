<x-app-layout>
    <x-slot name="header">
        <h2 class="font-semibold text-xl text-gray-800 leading-tight">{{ __('Dashboard') }} - my posts</h2>
    </x-slot>

    <div class="py-8">
        <div class="max-w-4xl mx-auto sm:px-6 lg:px-8 space-y-4">
            <a href="{{ route('posts.create') }}" class="text-indigo-600 hover:underline">{{ __('blog.new_post') }}</a>
            @forelse ($posts as $post)
                <x-post-card :post="$post" />
            @empty
                <x-alert type="info">{{ __('blog.no_posts') }}</x-alert>
            @endforelse
        </div>
    </div>
</x-app-layout>
