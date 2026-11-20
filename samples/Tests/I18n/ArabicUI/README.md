# ArabicUI - the IDE's own user interface in Arabic

Tests `radide/i18n` and `radide/features/ui_language.py`: live switch English -> العربية -> English,
right-to-left layout with left-to-right code editors / designer, translated menus, docks, tabs, Options
dialog, message boxes and Qt standard buttons, English kept for the code (`QAction.text()` etc.), the saved
setting used by a new window, and that nothing Arabic is left after switching back.

Run (from the repository root, uses a temporary copy of `samples/HelloPython` and test settings):

    .venv\Scripts\python -u samples\Tests\I18n\ArabicUI\test_ui_language.py

Try it by hand: Tools > Options > Environment > Language = العربية (or Tools > Language), OK.
