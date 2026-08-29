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
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_TYPE_CHOICES = [
        ('FULL', 'Full Payment'),
        ('SPLIT_INITIAL', 'Split - Initial Deposit Paid'),
        ('COMPLETED', 'Split - Balance Paid at Delivery'),
    ]

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_buyer')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_seller')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='FULL')
    transaction_id = models.CharField(max_length=255, blank=True)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
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
    def deposit_amount(self):
        """50% of the purchase price payable now as the initial deposit."""
        return (self.price_at_purchase * Decimal('0.50')).quantize(Decimal('0.01'))

    @property
    def remaining_balance(self):
        """Remaining balance due at delivery (price minus amount paid)."""
        return (self.price_at_purchase - self.amount_paid).quantize(Decimal('0.01'))
