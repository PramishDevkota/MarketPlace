from django.db import models
from django.urls import reverse
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User


class Category(models.Model):
    """Product categories managed via admin/database."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_category'
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('marketplace:product_list') + f'?category={self.slug}'


class Product(models.Model):
    """Products listed by approved sellers."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SOLD', 'Sold'),
        ('UNAVAILABLE', 'Unavailable'),
    ]

    LOCATION_CHOICES = [
        ('kumari_hall', 'Kumari Hall'),
        ('brit_cafe', 'BRIT Cafe'),
        ('main_block', 'Main Block'),
        ('skill_block', 'Skill Block'),
    ]

    PROGRAMME_CHOICES = [
        ('BSC_COMPUTING', 'BSc (Hons) Computing'),
        ('BSC_NETWORKING', 'BSc (Hons) Computer Networking & IT Security'),
        ('BSC_MULTIMEDIA', 'BSc (Hons) Multimedia Technologies'),
        ('BBA', 'BBA (International Business)'),
        ('OTHER', 'General Campus / Non-Academic'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES)
    programme = models.CharField(max_length=50, choices=PROGRAMME_CHOICES, default='BSC_COMPUTING')
    module_code = models.CharField(max_length=20, blank=True, help_text="e.g., CS4001, CS5002, CU4055")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    stock = models.PositiveIntegerField(default=1)
    is_available = models.BooleanField(default=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_product'
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            models.Index(fields=['status', 'is_available']),
            models.Index(fields=['created_at']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('marketplace:product_detail', kwargs={'pk': self.pk})

    @property
    def is_sold_out(self):
        return self.stock <= 0

    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0.0

    @property
    def review_count(self):
        return self.reviews.count()

    @property
    def location_display(self):
        return dict(self.LOCATION_CHOICES).get(self.location, self.location)

    @property
    def programme_display(self):
        return dict(self.PROGRAMME_CHOICES).get(self.programme, self.programme)


class ProductImage(models.Model):
    """Additional gallery pictures for a product."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='product_gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_productimage'
        ordering = ['created_at']

    def __str__(self):
        return f"Image for {self.product.name}"


class Cart(models.Model):
    """A shopping cart associated with a user (or session for guests)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_cart'
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        return f"Cart ({self.user.username if self.user else 'Anonymous'})"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """A single product line inside a cart."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_cartitem'
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ('cart', 'product')

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
