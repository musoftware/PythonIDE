<?php

namespace App\Controllers;

use App\Models\UserModel;
use CodeIgniter\HTTP\RedirectResponse;

/**
 * A simple session login: password_hash / password_verify, session id regenerated on sign-in,
 * CSRF token checked by the global 'csrf' filter (csrf_field() in the form).
 */
class Auth extends BaseController
{
    public function login(): string|RedirectResponse
    {
        if (session('user_id')) {
            return redirect()->route('products.index');
        }

        return view('auth/login', ['title' => lang('Shop.login.title')]);
    }

    public function attempt(): RedirectResponse
    {
        $rules = [
            'email'    => 'required|valid_email',
            'password' => 'required|min_length[6]',
        ];
        if (! $this->validate($rules)) {
            return redirect()->back()->withInput()->with('errors', $this->validator->getErrors());
        }

        $user = model(UserModel::class)->check(
            (string) $this->request->getPost('email'),
            (string) $this->request->getPost('password'),
        );
        if ($user === null) {
            return redirect()->back()->withInput()->with('error', lang('Shop.login.failed'));
        }

        $this->session->regenerate(true);
        $this->session->set(['user_id' => $user['id'], 'user_name' => $user['name']]);

        return redirect()->route('products.index')->with('message', lang('Shop.login.hello', [$user['name']]));
    }

    public function logout(): RedirectResponse
    {
        $this->session->destroy();

        return redirect()->route('home');
    }
}
