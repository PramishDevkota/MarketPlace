from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    """Custom user model for Islington Marketplace."""

    is_buyer = models.BooleanField(default=True)
    is_seller = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_image = models.ImageField(upload_to='avatars/', blank=True, null=True)

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'pk': self.pk})


class SellerRequest(models.Model):
    """Tracks requests from users who want to become sellers."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seller_requests')
    business_name = models.CharField(max_length=200)
    description = models.TextField(help_text='Tell us about what you plan to sell')
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_seller_request'
        ordering = ['-created_at']
        verbose_name = 'Seller Request'
        verbose_name_plural = 'Seller Requests'

    def __str__(self):
        return f"Seller Request by {self.user.username} - {self.status}"

    def approve(self):
        self.status = 'APPROVED'
        self.user.is_seller = True
        self.user.save()
        self.save()

    def reject(self, reason=''):
        self.status = 'REJECTED'
        self.admin_notes = reason
        self.save()
