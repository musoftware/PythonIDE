<x-app-layout>
    <x-slot name="header">
        <div class="flex items-center justify-between">
            <h2 class="font-semibold text-xl text-gray-800 leading-tight">{{ __('blog.posts') }}</h2>
            @auth
                <a href="{{ route('posts.create') }}" class="inline-flex items-center px-4 py-2 bg-gray-800 rounded-md text-xs text-white uppercase tracking-widest hover:bg-gray-700">
                    {{ __('blog.new_post') }}
                </a>
            @endauth
        </div>
    </x-slot>

    <div class="py-8">
        <div class="max-w-4xl mx-auto sm:px-6 lg:px-8 space-y-4">
            @if (session('status'))
                <x-alert :message="session('status')" />
            @endif

            <form method="GET" action="{{ route('posts.index') }}" class="flex gap-2">
                <x-text-input name="q" :value="$search" placeholder="Search titles..." class="flex-1" />
                <x-primary-button>Search</x-primary-button>
            </form>

            @forelse ($posts as $post)
                <x-post-card :post="$post" />
            @empty
                <x-alert type="info">{{ __('blog.no_posts') }}</x-alert>
            @endforelse

            {{ $posts->links() }}
        </div>
    </div>
</x-app-layout>
