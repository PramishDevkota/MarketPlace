from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from marketplace.models import Product, Category
from decimal import Decimal

User = get_user_model()


class ConversationModelTest(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Other', slug='other')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Item',
            description='A nice item',
            price=Decimal('500.00'),
            location='kumari_hall',
            status='APPROVED',
        )
        self.conversation = Conversation.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
        )

    def test_conversation_str(self):
        s = str(self.conversation)
        self.assertIn('buyer', s)
        self.assertIn('seller', s)

    def test_last_message(self):
        self.assertIsNone(self.conversation.last_message)
        msg = Message.objects.create(
            conversation=self.conversation,
            sender=self.buyer,
            content='Hello!',
        )
        self.assertEqual(self.conversation.last_message, msg)


class MessagingViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Other', slug='other')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Item',
            description='Nice item',
            price=Decimal('500.00'),
            location='kumari_hall',
            status='APPROVED',
        )
        self.conversation = Conversation.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
        )

    def test_conversation_list_requires_login(self):
        response = self.client.get(reverse('messaging:conversation_list'))
        self.assertEqual(response.status_code, 302)

    def test_conversation_list(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(reverse('messaging:conversation_list'))
        self.assertEqual(response.status_code, 200)

    def test_conversation_detail_requires_auth(self):
        response = self.client.get(
            reverse('messaging:conversation_detail', kwargs={'pk': self.conversation.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_conversation_detail_buyer(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(
            reverse('messaging:conversation_detail', kwargs={'pk': self.conversation.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_conversation_detail_seller(self):
        self.client.login(username='seller', password='pass1234')
        response = self.client.get(
            reverse('messaging:conversation_detail', kwargs={'pk': self.conversation.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_conversation_access(self):
        other = User.objects.create_user(username='other', password='pass1234')
        self.client.login(username='other', password='pass1234')
        response = self.client.get(
            reverse('messaging:conversation_detail', kwargs={'pk': self.conversation.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_send_message(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.post(
            reverse('messaging:conversation_detail', kwargs={'pk': self.conversation.pk}),
            {'content': 'Is this still available?'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Message.objects.filter(
            conversation=self.conversation,
            sender=self.buyer,
            content='Is this still available?'
        ).exists())

    def test_start_conversation(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(
            reverse('messaging:start_conversation', kwargs={'product_id': self.product.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_cannot_message_self(self):
        self.client.login(username='seller', password='pass1234')
        response = self.client.get(
            reverse('messaging:start_conversation', kwargs={'product_id': self.product.pk})
        )
        self.assertEqual(response.status_code, 302)
