from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Category, Product
from orders.models import Order
from decimal import Decimal

User = get_user_model()


class CategoryModelTest(TestCase):
    def test_category_str(self):
        cat = Category(name='Electronics', slug='electronics')
        self.assertEqual(str(cat), 'Electronics')

    def test_category_absolute_url(self):
        cat = Category(name='Books', slug='books')
        url = cat.get_absolute_url()
        self.assertIn('category=books', url)


class ProductModelTest(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Laptop',
            description='A used laptop',
            price=Decimal('15000.00'),
            location='kumari_hall',
            status='APPROVED',
        )

    def test_product_str(self):
        self.assertEqual(str(self.product), 'Laptop')

    def test_product_location_display(self):
        self.assertEqual(self.product.location_display, 'Kumari Hall')

    def test_average_rating_no_reviews(self):
        self.assertEqual(self.product.average_rating(), 0.0)

    def test_review_count(self):
        self.assertEqual(self.product.review_count, 0)

    def test_stock_default_and_sold_out(self):
        self.assertEqual(self.product.stock, 1)
        self.assertFalse(self.product.is_sold_out)
        self.product.stock = 0
        self.assertTrue(self.product.is_sold_out)

    def test_absolute_url(self):
        url = self.product.get_absolute_url()
        self.assertIn(f'/marketplace/product/{self.product.pk}/', url)


class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('marketplace:home')

    def test_home_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class ProductListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('marketplace:product_list')
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Books', slug='books')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Math Book',
            description='Advanced math',
            price=Decimal('500.00'),
            location='main_block',
            status='APPROVED',
        )

    def test_product_list_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_search_filter(self):
        response = self.client.get(self.url, {'q': 'Math'})
        self.assertEqual(response.status_code, 200)

    def test_category_filter(self):
        response = self.client.get(self.url, {'category': 'books'})
        self.assertEqual(response.status_code, 200)

    def test_location_filter(self):
        response = self.client.get(self.url, {'location': 'main_block'})
        self.assertEqual(response.status_code, 200)

    def test_price_filter(self):
        response = self.client.get(self.url, {'min_price': '100', 'max_price': '1000'})
        self.assertEqual(response.status_code, 200)


class ProductDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Clothing', slug='clothing')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Jacket',
            description='Warm jacket',
            price=Decimal('2000.00'),
            location='skill_block',
            status='APPROVED',
        )

    def test_detail_loads(self):
        response = self.client.get(reverse('marketplace:product_detail', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 200)

    def test_pending_product_not_visible(self):
        self.product.status = 'PENDING'
        self.product.save()
        response = self.client.get(reverse('marketplace:product_detail', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 404)

    def test_rejected_product_not_visible(self):
        self.product.status = 'REJECTED'
        self.product.save()
        response = self.client.get(reverse('marketplace:product_detail', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 404)


class CreateProductViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.buyer = User.objects.create_user(
            username='buyer', password='pass1234'
        )
        self.category = Category.objects.create(name='Furniture', slug='furniture')
        self.url = reverse('marketplace:create_product')

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_requires_seller(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_seller_can_access(self):
        self.client.login(username='seller', password='pass1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_create_product(self):
        self.client.login(username='seller', password='pass1234')
        response = self.client.post(self.url, {
            'name': 'Desk',
            'description': 'Wooden desk',
            'price': '3000.00',
            'category': self.category.pk,
            'location': 'main_block',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(name='Desk').exists())

    def test_created_product_is_pending(self):
        self.client.login(username='seller', password='pass1234')
        self.client.post(self.url, {
            'name': 'Chair',
            'description': 'Office chair',
            'price': '1500.00',
            'category': self.category.pk,
            'location': 'kumari_hall',
        })
        product = Product.objects.get(name='Chair')
        self.assertEqual(product.status, 'PENDING')


class IDORProtectionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.seller1 = User.objects.create_user(
            username='seller1', password='pass1234', is_seller=True
        )
        self.seller2 = User.objects.create_user(
            username='seller2', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product1 = Product.objects.create(
            seller=self.seller1,
            category=self.category,
            name='Product1',
            description='Desc',
            price=Decimal('1000.00'),
            location='kumari_hall',
            status='APPROVED',
        )
        self.product2 = Product.objects.create(
            seller=self.seller2,
            category=self.category,
            name='Product2',
            description='Desc',
            price=Decimal('2000.00'),
            location='main_block',
            status='APPROVED',
        )

    def test_edit_other_sellers_product_404(self):
        self.client.login(username='seller1', password='pass1234')
        response = self.client.get(
            reverse('marketplace:edit_product', kwargs={'pk': self.product2.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_other_sellers_product_404(self):
        self.client.login(username='seller1', password='pass1234')
        response = self.client.get(
            reverse('marketplace:delete_product', kwargs={'pk': self.product2.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_edit_own_product(self):
        self.client.login(username='seller1', password='pass1234')
        response = self.client.get(
            reverse('marketplace:edit_product', kwargs={'pk': self.product1.pk})
        )
        self.assertEqual(response.status_code, 200)


class AboutAndContactViewTest(TestCase):
    def test_about_loads(self):
        response = self.client.get(reverse('marketplace:about'))
        self.assertEqual(response.status_code, 200)

    def test_contact_loads(self):
        response = self.client.get(reverse('marketplace:contact'))
        self.assertEqual(response.status_code, 200)

    def test_contact_form_submission(self):
        response = self.client.post(reverse('marketplace:contact'), {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Hello',
            'message': 'This is a test message.',
        })
        self.assertEqual(response.status_code, 200)


class AdminRestrictionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin', password='pass1234', email='admin@example.com'
        )
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Laptop',
            description='A used laptop',
            price=Decimal('15000.00'),
            location='kumari_hall',
            status='PENDING',
        )

    def test_superuser_cannot_access_seller_product_form(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.get(reverse('marketplace:create_product'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:index'), response.url)

    def test_superuser_redirected_with_warning_message(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.get(reverse('marketplace:create_product'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin users cannot buy or sell products')

    def test_superuser_can_access_admin_index(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_approve_product_from_admin(self):
        self.client.login(username='admin', password='pass1234')
        changelist = reverse('admin:marketplace_product_changelist')
        response = self.client.post(changelist, {
            'action': 'approve_products',
            '_selected_action': [self.product.pk],
        })
        self.assertRedirects(response, changelist)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'APPROVED')

    def test_superuser_can_reject_product_from_admin(self):
        self.client.login(username='admin', password='pass1234')
        changelist = reverse('admin:marketplace_product_changelist')
        response = self.client.post(changelist, {
            'action': 'reject_products',
            '_selected_action': [self.product.pk],
        })
        self.assertRedirects(response, changelist)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'REJECTED')

    def test_superuser_can_delete_product_from_admin(self):
        self.client.login(username='admin', password='pass1234')
        delete_url = reverse('admin:marketplace_product_delete', args=[self.product.pk])
        response = self.client.post(delete_url, {'post': 'yes'})
        self.assertRedirects(response, reverse('admin:marketplace_product_changelist'))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_product_admin_has_no_add_permission(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.get(reverse('admin:marketplace_product_add'))
        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_access_admin(self):
        normal = User.objects.create_user(username='normal', password='pass1234')
        self.client.login(username='normal', password='pass1234')
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)


class AdminBlockingOtherStorefrontViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin', password='pass1234', email='admin@example.com'
        )
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.category = Category.objects.create(name='Books', slug='books')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Math Book',
            description='Advanced math',
            price=Decimal('500.00'),
            location='main_block',
            status='APPROVED',
        )
        self.client.login(username='admin', password='pass1234')

    def test_admin_blocked_from_seller_dashboard(self):
        response = self.client.get(reverse('seller_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:index'), response.url)

    def test_admin_blocked_from_buyer_dashboard(self):
        response = self.client.get(reverse('buyer_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:index'), response.url)

    def test_admin_blocked_from_buy(self):
        response = self.client.get(reverse('marketplace:buy_now', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:index'), response.url)

    def test_admin_blocked_from_become_seller(self):
        response = self.client.get(reverse('accounts:become_seller'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:index'), response.url)


class AdminNavbarTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin', password='pass1234', email='admin@example.com'
        )

    def test_admin_navbar_shows_admin_panel_button(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.get(reverse('marketplace:home'))
        self.assertContains(response, 'Admin Panel')
        self.assertContains(response, reverse('admin:index'))
        self.assertNotContains(response, 'Add Product')
        self.assertNotContains(response, 'Become a Seller')

    def test_admin_home_hides_seller_cta(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.get(reverse('marketplace:home'))
        self.assertNotContains(response, 'Become a Seller')
        self.assertNotContains(response, 'Sell an Item')


class OverviewViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.category = Category.objects.create(name='Books', slug='books')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Notebook',
            description='Notes',
            price=Decimal('300.00'),
            location='main_block',
            status='APPROVED',
        )

    def test_overview_renders_metrics(self):
        Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=Decimal('300.00'),
            status='CONFIRMED',
        )
        response = self.client.get(reverse('marketplace:overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Top-Selling Categories')
        self.assertContains(response, 'Recent Activity')

    def test_overview_excludes_cancelled_orders(self):
        Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product=self.product,
            price_at_purchase=Decimal('300.00'),
            status='CANCELLED',
        )
        response = self.client.get(reverse('marketplace:overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0</span>')
        self.assertContains(response, 'Rs. 0')


class RestockInventoryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.other = User.objects.create_user(
            username='other', password='pass1234', is_seller=True
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
            stock=1,
        )

    def test_seller_can_restock_own_product(self):
        self.client.login(username='seller', password='pass1234')
        response = self.client.post(
            reverse('marketplace:restock_product', kwargs={'pk': self.product.pk}),
            {'restock_amount': '5'},
        )
        self.product.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.product.stock, 6)

    def test_seller_cannot_restock_others_product(self):
        self.client.login(username='other', password='pass1234')
        response = self.client.post(
            reverse('marketplace:restock_product', kwargs={'pk': self.product.pk}),
            {'restock_amount': '5'},
        )
        self.product.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.product.stock, 1)

    def test_restock_reactivates_sold_out_product(self):
        self.product.stock = 0
        self.product.is_available = False
        self.product.status = 'SOLD'
        self.product.save()
        self.client.login(username='seller', password='pass1234')
        self.client.post(
            reverse('marketplace:restock_product', kwargs={'pk': self.product.pk}),
            {'restock_amount': '2'},
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertTrue(self.product.is_available)
        self.assertEqual(self.product.status, 'APPROVED')


class BuyNowStockTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.seller = User.objects.create_user(
            username='seller', password='pass1234', is_seller=True
        )
        self.buyer = User.objects.create_user(username='buyer', password='pass1234')
        self.category = Category.objects.create(name='Books', slug='books')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Novel',
            description='A great novel',
            price=Decimal('400.00'),
            location='kumari_hall',
            status='APPROVED',
            stock=2,
        )

    def test_buy_does_not_decrement_stock_until_payment(self):
        self.client.login(username='buyer', password='pass1234')
        response = self.client.post(
            reverse('marketplace:buy_now', kwargs={'pk': self.product.pk})
        )
        self.product.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.product.stock, 2)
        self.assertFalse(self.product.is_sold_out)
        order = Order.objects.get(product=self.product, buyer=self.buyer)
        self.assertEqual(order.status, 'PENDING')

    def test_buy_sets_quantity_on_order(self):
        self.client.login(username='buyer', password='pass1234')
        self.client.post(
            reverse('marketplace:buy_now', kwargs={'pk': self.product.pk}),
            {'quantity': 2},
        )
        order = Order.objects.get(product=self.product, buyer=self.buyer)
        self.assertEqual(order.quantity, 2)
        self.assertEqual(order.total_price, Decimal('800.00'))
        self.assertEqual(order.deposit_amount, Decimal('500.00'))

    def test_buy_last_unit_not_marked_sold_until_payment(self):
        self.product.stock = 1
        self.product.save()
        self.client.login(username='buyer', password='pass1234')
        self.client.post(
            reverse('marketplace:buy_now', kwargs={'pk': self.product.pk})
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertFalse(self.product.is_sold_out)
        self.assertEqual(self.product.status, 'APPROVED')

    def test_sold_out_product_not_buyable(self):
        self.product.stock = 0
        self.product.is_available = False
        self.product.status = 'SOLD'
        self.product.save()
        self.client.login(username='buyer', password='pass1234')
        response = self.client.post(
            reverse('marketplace:buy_now', kwargs={'pk': self.product.pk})
        )
        self.assertEqual(response.status_code, 404)

