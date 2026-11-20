@props(['type' => 'success', 'message' => null])

@php
    $colors = [
        'success' => 'bg-green-50 text-green-800 border-green-200',
        'error' => 'bg-red-50 text-red-800 border-red-200',
        'info' => 'bg-blue-50 text-blue-800 border-blue-200',
    ];
@endphp

<div {{ $attributes->merge(['class' => 'border rounded-md px-4 py-3 mb-4 '.($colors[$type] ?? $colors['info'])]) }} role="alert">
    {{ $message ?? $slot }}
</div>
