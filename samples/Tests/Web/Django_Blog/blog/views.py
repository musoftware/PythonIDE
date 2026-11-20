from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import CommentForm, PostForm, SignUpForm
from .models import Post


class PostListView(ListView):
    """/ - published posts, newest first, with search (?q=) and pagination."""
    model = Post
    paginate_by = 5
    context_object_name = "posts"

    def get_queryset(self):
        qs = (Post.objects.filter(published=True).select_related("author")
              .annotate(n_comments=Count("comments")).order_by("-created"))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))
        return qs


def post_detail(request, slug):
    """/post/<slug>/ - one post with its comments; logged-in users can comment."""
    post = get_object_or_404(Post, slug=slug)
    if not post.published and post.author != request.user:
        return redirect("blog:post_list")
    form = CommentForm()
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{reverse_lazy('login')}?next={post.get_absolute_url()}")
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, "Comment added.")
            return redirect(post)
    comments = post.comments.select_related("author")
    return render(request, "blog/post_detail.html", {"post": post, "comments": comments, "form": form})


class AuthorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.get_object().author == self.request.user


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, "Post created.")
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, AuthorRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm

    def form_valid(self, form):
        messages.success(self.request, "Post saved.")
        return super().form_valid(form)


class PostDeleteView(LoginRequiredMixin, AuthorRequiredMixin, DeleteView):
    model = Post
    success_url = reverse_lazy("blog:post_list")

    def form_valid(self, form):
        messages.success(self.request, "Post deleted.")
        return super().form_valid(form)


def signup(request):
    """/accounts/signup/ - create an account and log in."""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect("blog:post_list")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})
