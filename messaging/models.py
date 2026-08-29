from django.db import models
from django.urls import reverse
from accounts.models import User
from marketplace.models import Product


class Conversation(models.Model):
    """A conversation between a buyer and seller about a product."""

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_buyer')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_seller')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messaging_conversation'
        ordering = ['-updated_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        unique_together = ['buyer', 'seller', 'product']

    def __str__(self):
        return f"Conversation: {self.buyer.username} & {self.seller.username} about {self.product.name}"

    def get_absolute_url(self):
        return reverse('messaging:conversation_detail', kwargs={'pk': self.pk})

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()


class Message(models.Model):
    """Individual messages within a conversation."""

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messaging_message'
        ordering = ['created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at}"
