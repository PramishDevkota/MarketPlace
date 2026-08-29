from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from marketplace.models import Category

User = get_user_model()

DEFAULT_CATEGORIES = [
    {'name': 'Electronics', 'slug': 'electronics', 'description': 'Phones, laptops, gadgets, and more'},
    {'name': 'Books', 'slug': 'books', 'description': 'Textbooks, novels, and study materials'},
    {'name': 'Clothing', 'slug': 'clothing', 'description': 'Apparel, shoes, and accessories'},
    {'name': 'Stationery', 'slug': 'stationery', 'description': 'Pens, notebooks, and school supplies'},
    {'name': 'Accessories', 'slug': 'accessories', 'description': 'Bags, watches, jewelry, and more'},
    {'name': 'Furniture', 'slug': 'furniture', 'description': 'Desks, chairs, shelves, and home items'},
    {'name': 'Food', 'slug': 'food', 'description': 'Snacks, beverages, and homemade food items'},
    {'name': 'Services', 'slug': 'services', 'description': 'Tutoring, design, and other services'},
    {'name': 'Other', 'slug': 'other', 'description': 'Everything else'},
]


class Command(BaseCommand):
    help = 'Seed the database with an admin superuser and default categories'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@islingtonmarketplace.com',
                password='admin123',
                is_buyer=True,
                is_seller=True,
            )
            self.stdout.write(self.style.SUCCESS('Admin superuser created: admin / admin123'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists, skipping.'))

        created_count = 0
        for cat_data in DEFAULT_CATEGORIES:
            _, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description'],
                },
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f'{created_count} new categories created ({len(DEFAULT_CATEGORIES)} total default categories).'))
