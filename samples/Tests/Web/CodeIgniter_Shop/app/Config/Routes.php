<?php

use CodeIgniter\Router\RouteCollection;

/**
 * CodeIgniter Shop - routes.
 *
 * In RAD IDE: View > CodeIgniter > Routes lists them (double-click opens the controller method);
 * route_to('products.edit', 5) / url_to(...) complete the names below, F12 on a name jumps here.
 *
 * @var RouteCollection $routes
 */
$routes->get('/', 'Home::index', ['as' => 'home']);

// sign in / out (a simple session login, CSRF protected - see Config/Filters.php)
$routes->get('login', 'Auth::login', ['as' => 'login']);
$routes->post('login', 'Auth::attempt', ['as' => 'login.attempt']);
$routes->post('logout', 'Auth::logout', ['as' => 'logout']);

// products CRUD - only for signed-in users (the 'auth' filter, app/Filters/AuthFilter.php)
$routes->group('products', ['filter' => 'auth'], static function (RouteCollection $routes) {
    $routes->get('/', 'Products::index', ['as' => 'products.index']);
    $routes->get('new', 'Products::new', ['as' => 'products.new']);
    $routes->post('/', 'Products::create', ['as' => 'products.create']);
    $routes->get('(:num)/edit', 'Products::edit/$1', ['as' => 'products.edit']);
    $routes->post('(:num)', 'Products::update/$1', ['as' => 'products.update']);
    $routes->post('(:num)/delete', 'Products::delete/$1', ['as' => 'products.delete']);
});

// JSON API (no CSRF for api/*)
$routes->get('api/products', 'Api\Products::index', ['as' => 'api.products']);
$routes->get('api/products/(:num)', 'Api\Products::show/$1', ['as' => 'api.products.show']);
