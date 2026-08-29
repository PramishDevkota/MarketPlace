from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Review
from orders.models import Order
from marketplace.models import Product, Category
from decimal import Decimal

User = get_user_model()


class ReviewModelTest(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Books', slug='books')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Physics Book',
            description='College physics',
            price=Decimal('500.00'),
            location='kumari_hall',
            status='APPROVED',
        )
        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=Decimal('500.00'),
            status='COMPLETED',
        )
        self.review = Review.objects.create(
            product=self.product,
            user=self.buyer,
            order=self.order,
            rating=5,
            comment='Excellent book!',
        )

    def test_review_str(self):
        self.assertIn('buyer', str(self.review))
        self.assertIn('5★', str(self.review))


class ReviewRestrictionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Clothing', slug='clothing')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Shoes',
            description='Running shoes',
            price=Decimal('2000.00'),
            location='skill_block',
            status='APPROVED',
        )
        self.completed_order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=Decimal('2000.00'),
            status='COMPLETED',
        )

    def test_cannot_review_without_purchase(self):
        other = User.objects.create_user(username='other', password='pass1234')
        self.client.login(username='other', password='pass1234')
        response = self.client.get(
            reverse('reviews:create_review', kwargs={'product_id': self.product.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_can_review_with_completed_order(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(
            reverse('reviews:create_review', kwargs={'product_id': self.product.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_cannot_review_twice(self):
        Review.objects.create(
            product=self.product,
            user=self.buyer,
            order=self.completed_order,
            rating=4,
            comment='Good!',
        )
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(
            reverse('reviews:create_review', kwargs={'product_id': self.product.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_submit_review(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.post(
            reverse('reviews:create_review', kwargs={'product_id': self.product.pk}),
            {'rating': '5', 'comment': 'Great product!'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Review.objects.filter(
            product=self.product, user=self.buyer
        ).exists())

    def test_incomplete_order_cannot_review(self):
        self.completed_order.status = 'CONFIRMED'
        self.completed_order.save()
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(
            reverse('reviews:create_review', kwargs={'product_id': self.product.pk})
        )
        self.assertEqual(response.status_code, 302)


class AddReviewViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Headphones',
            description='Wireless headphones',
            price=Decimal('3000.00'),
            location='brit_cafe',
            status='APPROVED',
        )
        self.completed_order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=Decimal('3000.00'),
            status='COMPLETED',
        )

    def test_add_review_form_loads(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(
            reverse('reviews:add_review', kwargs={'order_id': self.completed_order.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_add_review_submit(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.post(
            reverse('reviews:add_review', kwargs={'order_id': self.completed_order.pk}),
            {'rating': '5', 'comment': 'Loved it!'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Review.objects.filter(
            product=self.product, user=self.buyer, order=self.completed_order
        ).exists())

    def test_add_review_only_for_buyer(self):
        other = User.objects.create_user(username='other', password='pass1234')
        self.client.login(username='other', password='pass1234')
        response = self.client.get(
            reverse('reviews:add_review', kwargs={'order_id': self.completed_order.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_add_review_only_for_completed_order(self):
        self.completed_order.status = 'CONFIRMED'
        self.completed_order.save()
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(
            reverse('reviews:add_review', kwargs={'order_id': self.completed_order.pk})
        )
        self.assertEqual(response.status_code, 404)

