from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch
from .models import Order
from marketplace.models import Product, Category
from decimal import Decimal

User = get_user_model()


class OrderModelTest(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Phone',
            description='Smartphone',
            price=Decimal('10000.00'),
            location='kumari_hall',
            status='APPROVED',
        )
        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=self.product.price,
            status='CONFIRMED',
        )

    def test_order_str(self):
        self.assertIn('Phone', str(self.order))

    def test_order_absolute_url(self):
        url = self.order.get_absolute_url()
        self.assertIn(f'/orders/{self.order.pk}/', url)

    def test_payment_fields_defaults(self):
        self.assertEqual(self.order.amount_paid, Decimal('0.00'))
        self.assertEqual(self.order.payment_type, 'FULL')
        self.assertEqual(self.order.transaction_id, '')
        self.assertFalse(self.order.is_paid)

    def test_deposit_amount_is_500_rupees(self):
        self.assertEqual(self.order.deposit_amount, Decimal('500.00'))

    def test_remaining_balance_at_checkout(self):
        self.assertEqual(self.order.remaining_balance, Decimal('9500.00'))

    def test_deposit_is_full_price_below_500(self):
        cheap = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=Decimal('200.00'),
            status='PENDING',
        )
        self.assertEqual(cheap.deposit_amount, Decimal('200.00'))
        self.assertEqual(cheap.remaining_balance, Decimal('0.00'))


class PriceSnapshotTest(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Books', slug='books')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Notebook',
            description='College notebook',
            price=Decimal('200.00'),
            location='brit_cafe',
            status='APPROVED',
        )

    def test_price_snapshot_not_affected_by_product_change(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.post(
            reverse('marketplace:buy_now', kwargs={'pk': self.product.pk})
        )
        self.assertEqual(response.status_code, 302)
        order = Order.objects.first()
        self.assertEqual(order.price_at_purchase, Decimal('200.00'))

        self.product.price = Decimal('500.00')
        self.product.save()

        order.refresh_from_db()
        self.assertEqual(order.price_at_purchase, Decimal('200.00'))

    def test_price_snapshot_stored_at_creation(self):
        self.client.login(username='buyer', password='pass1234')
        self.client.post(reverse('marketplace:buy_now', kwargs={'pk': self.product.pk}))
        order = Order.objects.first()
        self.assertEqual(order.price_at_purchase, self.product.price)


class BuyNowViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Food', slug='food')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Snacks',
            description='Homemade snacks',
            price=Decimal('150.00'),
            location='brit_cafe',
            status='APPROVED',
        )

    def test_requires_login(self):
        response = self.client.get(reverse('marketplace:buy_now', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 302)

    def test_cannot_buy_own_product(self):
        self.client.login(username='seller', password='pass1234')
        response = self.client.get(reverse('marketplace:buy_now', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 302)

    def test_buy_confirm_page(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(reverse('marketplace:buy_now', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 200)

    def test_buy_success(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.post(reverse('marketplace:buy_now', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.filter(buyer=self.buyer, product=self.product).exists())

    def test_product_stock_not_reserved_until_payment(self):
        self.client.login(username='buyer', password='pass1234')
        self.client.post(reverse('marketplace:buy_now', kwargs={'pk': self.product.pk}))
        self.product.refresh_from_db()
        order = Order.objects.first()
        self.assertEqual(self.product.status, 'APPROVED')
        self.assertTrue(self.product.is_available)
        self.assertEqual(order.status, 'PENDING')
        self.assertEqual(order.quantity, 1)


class OrderListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Stationery', slug='stationery')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Pen',
            description='Ballpoint pen',
            price=Decimal('50.00'),
            location='main_block',
            status='SOLD',
        )
        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=Decimal('50.00'),
            status='COMPLETED',
        )

    def test_order_list_requires_login(self):
        response = self.client.get(reverse('orders:order_list'))
        self.assertEqual(response.status_code, 302)

    def test_buyer_sees_own_orders(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(reverse('orders:order_list'))
        self.assertEqual(response.status_code, 200)

    def test_seller_sees_own_orders(self):
        self.client.login(username='seller', password='pass1234')
        response = self.client.get(reverse('orders:order_list'))
        self.assertEqual(response.status_code, 200)

    def test_order_detail_access(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(reverse('orders:order_detail', kwargs={'pk': self.order.pk}))
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_order_detail_redirects(self):
        other = User.objects.create_user(username='other', password='pass1234')
        self.client.login(username='other', password='pass1234')
        response = self.client.get(reverse('orders:order_detail', kwargs={'pk': self.order.pk}))
        self.assertEqual(response.status_code, 302)


class KhaltiPaymentTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.buyer = User.objects.create_user(
            username='pay_buyer', password='pass1234', email='buyer@example.com'
        )
        self.seller = User.objects.create_user(
            username='pay_seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Gadgets', slug='gadgets')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Headphones',
            description='Wireless headphones',
            price=Decimal('5000.00'),
            location='main_block',
            status='APPROVED',
        )
        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=self.product.price,
            status='CONFIRMED',
        )

    def test_initiate_requires_login(self):
        response = self.client.get(
            reverse('orders:initiate_khalti_payment', kwargs={'order_id': self.order.pk})
        )
        self.assertEqual(response.status_code, 302)

    @patch('orders.views.requests.post')
    def test_initiate_sends_500_deposit_in_paisa(self, mock_post):
        self.client.login(username='pay_buyer', password='pass1234')
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'pidx': 'mock-pidx-123',
            'payment_url': 'https://pay.khalti.com/mock',
        }

        response = self.client.get(
            reverse('orders:initiate_khalti_payment', kwargs={'order_id': self.order.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, 'https://pay.khalti.com/mock', fetch_redirect_response=False)

        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['amount'], int(self.order.deposit_amount * 100))
        self.assertEqual(payload['amount'], 50000)
        self.assertEqual(payload['purchase_order_id'], str(self.order.pk))

        self.order.refresh_from_db()
        self.assertEqual(self.order.transaction_id, 'mock-pidx-123')

    @patch('orders.views.requests.post')
    def test_initiate_500_deposit_rounds_to_paisa(self, mock_post):
        self.order.price_at_purchase = Decimal('999.99')
        self.order.save()
        self.client.login(username='pay_buyer', password='pass1234')
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'pidx': 'mock-pidx-456',
            'payment_url': 'https://pay.khalti.com/mock2',
        }

        response = self.client.get(
            reverse('orders:initiate_khalti_payment', kwargs={'order_id': self.order.pk})
        )
        self.assertEqual(response.status_code, 302)

        payload = mock_post.call_args.kwargs['json']
        expected_deposit = Decimal('500.00')
        self.assertEqual(payload['amount'], int(expected_deposit * 100))

    @patch('orders.views.requests.post')
    def test_verify_completes_advance_payment(self, mock_post):
        self.client.login(username='pay_buyer', password='pass1234')
        self.order.transaction_id = 'mock-pidx-123'
        self.order.save()

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'pidx': 'mock-pidx-123',
            'status': 'Completed',
            'amount': 50000,
        }

        response = self.client.get(
            reverse('orders:khalti_verify'),
            {'pidx': 'mock-pidx-123', 'status': 'Completed'},
        )

        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_paid, Decimal('500.00'))
        self.assertEqual(self.order.payment_type, 'SPLIT_INITIAL')
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.status, 'COMPLETED')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertEqual(self.product.status, 'SOLD')

    @patch('orders.views.requests.post')
    def test_verify_failed_payment_keeps_stock(self, mock_post):
        self.client.login(username='pay_buyer', password='pass1234')
        self.order.transaction_id = 'mock-pidx-999'
        self.order.save()

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'pidx': 'mock-pidx-999',
            'status': 'User canceled',
        }

        response = self.client.get(
            reverse('orders:khalti_verify'),
            {'pidx': 'mock-pidx-999', 'status': 'User canceled'},
        )

        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertFalse(self.order.is_paid)
        self.assertEqual(self.order.status, 'CONFIRMED')
        self.assertEqual(self.order.amount_paid, Decimal('0.00'))
        self.assertEqual(self.product.stock, 1)

    def test_checkout_page_requires_login(self):
        response = self.client.get(reverse('orders:checkout', kwargs={'pk': self.order.pk}))
        self.assertEqual(response.status_code, 302)
