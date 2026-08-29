from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from accounts.decorators import admin_users_forbidden
from .models import Conversation, Message
from .forms import MessageForm
from marketplace.models import Product


@login_required
@admin_users_forbidden
def conversation_list_view(request):
    conversations = Conversation.objects.filter(
        buyer=request.user
    ) | Conversation.objects.filter(
        seller=request.user
    )
    conversations = conversations.select_related('buyer', 'seller', 'product').distinct()
    context = {
        'conversations': conversations,
    }
    return render(request, 'messaging/conversation_list.html', context)


@login_required
@admin_users_forbidden
def conversation_detail_view(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related('buyer', 'seller', 'product'),
        pk=pk,
    )
    if request.user != conversation.buyer and request.user != conversation.seller:
        return HttpResponseForbidden('You are not part of this conversation.')

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            conversation.save()
            return redirect('messaging:conversation_detail', pk=conversation.pk)
    else:
        form = MessageForm()

    unread_messages = conversation.messages.filter(
        is_read=False
    ).exclude(sender=request.user)
    unread_messages.update(is_read=True)

    chat_messages = conversation.messages.select_related('sender').all()
    context = {
        'conversation': conversation,
        'messages_list': chat_messages,
        'form': form,
    }
    return render(request, 'messaging/conversation_detail.html', context)


@login_required
@admin_users_forbidden
def start_conversation_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, status='APPROVED')

    if request.user == product.seller:
        messages.error(request, 'You cannot message yourself about your own product.')
        return redirect('marketplace:product_detail', pk=product.pk)

    conversation, created = Conversation.objects.get_or_create(
        buyer=request.user,
        seller=product.seller,
        product=product,
    )

    return redirect('messaging:conversation_detail', pk=conversation.pk)
