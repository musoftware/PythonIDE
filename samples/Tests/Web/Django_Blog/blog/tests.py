from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Comment, Post


class BlogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ada", password="Lovelace-1815")
        self.post = Post.objects.create(title="Hello World", body="First post", author=self.user)

    def test_slug_and_list(self):
        self.assertEqual(self.post.slug, "hello-world")
        r = self.client.get(reverse("blog:post_list"))
        self.assertContains(r, "Hello World")

    def test_search(self):
        r = self.client.get(reverse("blog:post_list") + "?q=nothing-like-this")
        self.assertNotContains(r, "Hello World")

    def test_create_needs_login(self):
        r = self.client.get(reverse("blog:post_create"))
        self.assertEqual(r.status_code, 302)

    def test_create_edit_delete(self):
        self.client.login(username="ada", password="Lovelace-1815")
        r = self.client.post(reverse("blog:post_create"), {"title": "Second", "body": "x", "published": "on"})
        self.assertEqual(r.status_code, 302)
        p = Post.objects.get(title="Second")
        r = self.client.post(reverse("blog:post_update", args=[p.slug]), {"title": "Second!", "body": "y",
                                                                         "published": "on"})
        p.refresh_from_db()
        self.assertEqual(p.title, "Second!")
        self.client.post(reverse("blog:post_delete", args=[p.slug]))
        self.assertFalse(Post.objects.filter(pk=p.pk).exists())

    def test_comment(self):
        self.client.login(username="ada", password="Lovelace-1815")
        self.client.post(self.post.get_absolute_url(), {"body": "Nice!"})
        self.assertEqual(Comment.objects.filter(post=self.post).count(), 1)

    def test_other_user_cannot_edit(self):
        User.objects.create_user("bob", password="Builder-2000")
        self.client.login(username="bob", password="Builder-2000")
        r = self.client.get(reverse("blog:post_update", args=[self.post.slug]))
        self.assertEqual(r.status_code, 403)
