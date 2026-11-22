<?php

use CodeIgniter\Router\RouteCollection;

/**
 * @var RouteCollection $routes
 */
$routes->get('/', 'Products::home');
$routes->get('products', 'Products::index');
$routes->match(['GET', 'POST'], 'products/add', 'Products::add', ['filter' => 'csrf']);
$routes->match(['GET', 'POST'], 'products/(:num)/edit', 'Products::edit/$1', ['filter' => 'csrf']);
$routes->post('products/(:num)/delete', 'Products::delete/$1', ['filter' => 'csrf']);
$routes->match(['GET', 'POST'], 'login', 'Auth::login', ['filter' => 'csrf']);
$routes->post('logout', 'Auth::logout', ['filter' => 'csrf']);
$routes->get('api/products', 'Products::api');
