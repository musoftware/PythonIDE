"""manage.py seed_store - demo rows + the admin account on a new host."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Product


class Command(BaseCommand):
    help = "Create the RAD Store demo products and the admin / secret account when missing"

    def handle(self, *args, **options):
        if not Product.objects.exists():
            Product.objects.create(name="Laptop", price=999.5)
            Product.objects.create(name="Phone", price=450)
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "secret")
        self.stdout.write(f"{Product.objects.count()} products")
