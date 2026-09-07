from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from unittest.mock import patch

from marketplace.models import Product, Category
from orders.models import Order
from notifications.services import notify_seller_of_payment, send_email, send_whatsapp

User = get_user_model()


class NotifySellerOfPaymentTest(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username='nbuyer', password='pass1234', email='nbuyer@example.com'
        )
        self.seller = User.objects.create_user(
            username='nseller', password='pass1234', is_seller=True, email='nseller@gmail.com'
        )
        self.seller.phone_number = '9800000001'
        self.seller.save()
        self.category = Category.objects.create(name='Books', slug='books')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Textbook',
            description='Campus textbook',
            price=Decimal('1200.00'),
            location='main_block',
            status='APPROVED',
        )
        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=self.product.price,
            amount_paid=Decimal('500.00'),
            is_paid=True,
            status='COMPLETED',
        )

    @override_settings(EMAIL_HOST='smtp.gmail.com', WHATSAPP_TOKEN='', WHATSAPP_PHONE_ID='')
    @patch('orders.views.notify_seller_of_payment')
    @patch('notifications.services.send_mail')
    def test_notify_seller_emails_seller(self, mock_mail, _mock_notify_view):
        notify_seller_of_payment(self.order)
        mock_mail.assert_called_once()
        args = mock_mail.call_args
        self.assertEqual(args[0][0], 'You received a payment for "Textbook"')
        self.assertEqual(args[0][3], ['nseller@gmail.com'])
        self.assertIn('advance deposit', args[0][1].lower())

    @override_settings(EMAIL_HOST='')
    def test_email_skipped_when_smtp_unconfigured(self):
        result = send_email('someone@example.com', 'Hi', 'Body')
        self.assertFalse(result)

    @override_settings(WHATSAPP_TOKEN='', WHATSAPP_PHONE_ID='')
    def test_whatsapp_stub_returns_false_without_credentials(self):
        result = send_whatsapp('9800000001', 'Hello')
        self.assertFalse(result)