<?php

// lang('Shop.title'), lang('Shop.products.saved', [$name]) ... (RAD IDE completes these keys)
return [
    'title'    => 'CodeIgniter Shop',
    'welcome'  => 'Welcome to the shop',
    'catalog'  => 'Catalog',
    'products' => [
        'title'   => 'Products',
        'new'     => 'New product',
        'edit'    => 'Edit product',
        'saved'   => 'Product "{0}" saved.',
        'deleted' => 'Product deleted.',
        'empty'   => 'No products yet.',
        'confirm' => 'Delete this product?',
    ],
    'fields' => [
        'name'        => 'Name',
        'sku'         => 'SKU',
        'price'       => 'Price',
        'stock'       => 'Stock',
        'description' => 'Description',
    ],
    'stock' => [
        'ok'  => 'in stock',
        'low' => 'only {0} left',
        'out' => 'sold out',
    ],
    'login' => [
        'title'    => 'Sign in',
        'email'    => 'E-mail',
        'password' => 'Password',
        'submit'   => 'Sign in',
        'failed'   => 'Wrong e-mail or password.',
        'required' => 'Please sign in first.',
        'hello'    => 'Hello, {0}',
        'logout'   => 'Sign out',
        'demo'     => 'Demo account: admin@example.com / secret123',
    ],
    'save'   => 'Save',
    'cancel' => 'Cancel',
    'delete' => 'Delete',
    'edit'   => 'Edit',
];
