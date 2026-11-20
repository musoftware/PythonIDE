# Django Blog (RAD IDE sample)

A small but complete **Django 5.2** blog made with RAD IDE's *New Project > Web > Django App* template
(`django-admin startproject config .` + `manage.py startapp core`) and `manage.py startapp blog`.

| Feature | Where |
|---|---|
| Models `Post` (unique slug made from the title, author, draft flag) and `Comment` | `blog/models.py`, `blog/migrations/` |
| Admin: list / filters / search, prepopulated slug, comments inline | `blog/admin.py` |
| Class-based views: list with search (`?q=`) and pagination, create / update / delete (only the author, `LoginRequiredMixin` + `UserPassesTestMixin`) | `blog/views.py` |
| A function view with a comment form, flash messages | `blog/views.py` (`post_detail`), `templates/base.html` |
| Sign up (`UserCreationForm`), log in / log out (`django.contrib.auth.urls`) | `blog/forms.py`, `config/urls.py`, `templates/registration/` |
| Templates with inheritance, `{% url %}`, `{% static %}`, filters | `templates/` |
| 6 unit tests | `blog/tests.py` |
| A management command with demo data | `blog/management/commands/seed_blog.py` |

Not in the sample: `.venv` and `db.sqlite3` (both are made on the first run).

## Try it in RAD IDE

1. **File > Open Project** and choose this folder.
2. **Ctrl+F5** (run): the first run creates `.venv`, installs Django (`requirements.txt`) and runs `migrate`,
   then `manage.py runserver` starts behind the IDE's server: the **Preview** shows the blog and **Requests**
   lists every request. Save a template and the Preview reloads; save a `.py` file and Django's auto-reloader
   restarts the app, then the Preview reloads.
3. **View > Django** (the Django panel): *More > Run command...* `seed_blog` adds the demo user
   **demo / demo-pass-123** and three posts. *createsuperuser...* makes an admin user (then *Open Admin*).
   *makemigrations* / *migrate* / *startapp...* / *shell* (in the Terminal) / *check* / *test* (6 tests) /
   *collectstatic*. The *URL names* tab lists every URL name (double-click = open in the Preview, right-click =
   go to the view), *Models* every model and field, *Templates* every template.
4. **F5** = debug: put a breakpoint (F9) in `blog/views.py` on `post = get_object_or_404(...)` and open a post in
   the Preview - Locals show `post` and `slug`, Immediate evaluates `post.title`, F10 / F11 / Shift+F11 work.
   Saving a `.py` file while debugging restarts the debug session.
5. IntelliSense read from this project: `redirect('` / `reverse('` / `{% url '` list `blog:post_detail`,
   `signup`, `login`, `admin:index` ...; `render(request, '` / `{% extends '` list the templates;
   `Post.objects.filter(` lists `title`, `slug`, `author__username`, `comments__body`, `title__icontains` ...;
   in `post_list.html` `{{ post.` lists the Post fields (`posts` comes from the ListView's
   `context_object_name`), `{{ post.author.` the User fields; `{% ` lists tags (+ the `endfor` / `endblock`
   that closes the open block), `|` the filters. **F12** on `'blog/post_detail.html'`, `'blog:post_list'` or
   `{% extends 'base.html' %}` opens the template / the `path(...)` line in `blog/urls.py`.
