from django.db import models
from django.urls import reverse
from decimal import Decimal
from accounts.models import User
from marketplace.models import Product


class Order(models.Model):
    """Orders tracking purchases made on the marketplace."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PAID', 'Deposit Paid'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_TYPE_CHOICES = [
        ('FULL', 'Full Payment'),
        ('SPLIT_INITIAL', 'Split - Initial Deposit Paid'),
        ('COMPLETED', 'Split - Balance Paid at Delivery'),
    ]

    MEETUP_LOCATION_CHOICES = [
        ('BLOCK_A_HALLWAY', 'Block A - Ground Floor Hallway'),
        ('BLOCK_B_CAFETERIA', 'Block B - Cafeteria'),
        ('COFFEE_STATION', 'The Coffee Station / Juice Bar'),
        ('LIBRARY_ENTRANCE', 'Library Entrance'),
        ('LECTURE_THEATRE_LOUNGE', 'Lecture Theatre Lounge'),
    ]

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_buyer')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_seller')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='FULL')
    transaction_id = models.CharField(max_length=255, blank=True)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    meetup_location = models.CharField(max_length=50, choices=MEETUP_LOCATION_CHOICES, default='BLOCK_A_HALLWAY')
    meetup_time_notes = models.CharField(max_length=255, blank=True, help_text="e.g., Between 12:00 PM and 1:00 PM after Lecture")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders_order'
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"Order #{self.pk} - {self.product.name} by {self.buyer.username}"

    def get_absolute_url(self):
        return reverse('orders:order_detail', kwargs={'pk': self.pk})

    @property
    def total_price(self):
        """Total purchase price (unit price x quantity)."""
        return (self.price_at_purchase * Decimal(self.quantity or 1)).quantize(Decimal('0.01'))

    @property
    def deposit_amount(self):
        """Advance deposit due now: Rs. 500, or the full price if it is below Rs. 500."""
        return Decimal(min(self.total_price, Decimal('500.00'))).quantize(Decimal('0.01'))

    @property
    def remaining_amount(self):
        """Remaining balance due at delivery (total price minus the advance deposit)."""
        return (self.total_price - self.deposit_amount).quantize(Decimal('0.01'))

    @property
    def remaining_balance(self):
        """Alias kept for template compatibility."""
        return self.remaining_amount
