@csrf
<div>
    <x-input-label for="title" value="Title" />
    <x-text-input id="title" name="title" :value="old('title', $post->title)" class="block w-full mt-1" required autofocus />
    <x-input-error :messages="$errors->get('title')" class="mt-2" />
</div>

<div>
    <x-input-label for="body" value="Text" />
    <textarea id="body" name="body" rows="10" class="block w-full mt-1 border-gray-300 rounded-md">{{ old('body', $post->body) }}</textarea>
    <x-input-error :messages="$errors->get('body')" class="mt-2" />
</div>

<label class="inline-flex items-center gap-2">
    <input type="checkbox" name="published" value="1" @checked(old('published', $post->published)) class="rounded border-gray-300">
    <span>Published</span>
</label>

<div class="flex items-center gap-4">
    <x-primary-button>Save</x-primary-button>
    <a href="{{ route('posts.index') }}" class="text-gray-600 hover:underline">Cancel</a>
</div>
