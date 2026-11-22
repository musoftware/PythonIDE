<?php

namespace App\Controllers;

class Auth extends BaseController
{
    public function login()
    {
        if ($this->request->is('post')) {
            if ($this->request->getPost('username') === 'admin'
                && hash_equals('secret', (string) $this->request->getPost('password'))) {
                session()->regenerate();
                session()->set('user', 'admin');
                $next = (string) $this->request->getPost('next');
                return redirect()->to(str_starts_with($next, '/') ? $next : '/products');
            }
            return $this->response->setStatusCode(401)->setBody(view('store/login', [
                'error' => 'Invalid user name or password', 'next' => $this->request->getPost('next')]));
        }
        return view('store/login', ['error' => '', 'next' => $this->request->getGet('next') ?? '/products']);
    }

    public function logout()
    {
        session()->remove('user');
        return redirect()->to('/');
    }
}
