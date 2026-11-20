<?php if (session()->getFlashdata('message')): ?>
    <p class="flash ok"><?= esc(session()->getFlashdata('message')) ?></p>
<?php endif ?>
<?php if (session()->getFlashdata('error')): ?>
    <p class="flash err"><?= esc(session()->getFlashdata('error')) ?></p>
<?php endif ?>
<?php if ($errors = session()->getFlashdata('errors')): ?>
    <ul class="flash err">
        <?php foreach ($errors as $e): ?>
            <li><?= esc($e) ?></li>
        <?php endforeach ?>
    </ul>
<?php endif ?>
