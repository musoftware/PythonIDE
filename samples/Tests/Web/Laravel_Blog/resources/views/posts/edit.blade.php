<x-app-layout>
    <x-slot name="header">
        <h2 class="font-semibold text-xl text-gray-800 leading-tight">{{ __('blog.edit_post') }}</h2>
    </x-slot>

    <div class="py-8">
        <div class="max-w-4xl mx-auto sm:px-6 lg:px-8">
            <form method="POST" action="{{ route('posts.update', $post) }}" class="bg-white shadow-sm sm:rounded-lg p-6 space-y-4">
                @method('PUT')
                @include('posts.partials.form')
            </form>
        </div>
    </div>
</x-app-layout>
