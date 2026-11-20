"""python manage.py seed_blog - a demo user (demo / demo-pass-123) and three posts."""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from blog.models import Comment, Post


class Command(BaseCommand):
    help = "Create a demo user and a few posts"

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
        if created:
            user.set_password("demo-pass-123")
            user.save()
        for i, (title, body) in enumerate([
            ("Welcome to the Django Blog", "This blog was built with RAD IDE: models, admin, views, templates."),
            ("Debugging Django in RAD IDE", "Set a breakpoint in blog/views.py and press F5."),
            ("Templates with IntelliSense", "Type {% url ' in a template: the URL names come from the project."),
        ]):
            post, _ = Post.objects.get_or_create(title=title, defaults={"body": body, "author": user})
            if i == 0 and not post.comments.exists():
                Comment.objects.create(post=post, author=user, body="First comment!")
        self.stdout.write(self.style.SUCCESS("Demo data ready: user demo / demo-pass-123"))
