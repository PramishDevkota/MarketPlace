from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from marketplace.models import Product


class Review(models.Model):
    """Reviews from verified buyers on completed orders."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_reviews')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reviews_review'
        ordering = ['-created_at']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        unique_together = ('product', 'user', 'order')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}★)"
