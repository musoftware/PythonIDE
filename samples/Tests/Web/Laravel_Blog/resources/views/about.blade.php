<x-app-layout>
    <x-slot name="header">
        <h2 class="font-semibold text-xl text-gray-800 leading-tight">About</h2>
    </x-slot>

    <div class="py-8">
        <div class="max-w-4xl mx-auto sm:px-6 lg:px-8 bg-white shadow-sm sm:rounded-lg p-6 space-y-3">
            <p>{{ config('blog.title') }} is a sample Laravel {{ app()->version() }} application made with RAD IDE.</p>
            <p>JSON API: <a class="text-indigo-600 hover:underline" href="{{ route('api.posts.index') }}">/api/posts</a>,
               <a class="text-indigo-600 hover:underline" href="{{ route('api.status') }}">/api/status</a></p>
        </div>
    </div>
</x-app-layout>
