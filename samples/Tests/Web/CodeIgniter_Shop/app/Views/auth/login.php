<?= $this->extend('layouts/main') ?>

<?= $this->section('content') ?>
<h1><?= lang('Shop.login.title') ?></h1>

<?= form_open(url_to('login.attempt'), ['class' => 'form narrow']) ?>
    <label><?= lang('Shop.login.email') ?>
        <input type="email" name="email" value="<?= old('email') ?>" required autofocus>
    </label>
    <label><?= lang('Shop.login.password') ?>
        <input type="password" name="password" required>
    </label>
    <button type="submit"><?= lang('Shop.login.submit') ?></button>
    <p class="muted"><?= lang('Shop.login.demo') ?></p>
<?= form_close() ?>
<?= $this->endSection() ?>
