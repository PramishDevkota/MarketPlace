from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, SellerRequestForm
from .decorators import admin_users_forbidden
from .models import SellerRequest

User = get_user_model()


def register_view(request):
    if request.user.is_authenticated:
        return redirect('marketplace:home')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to Islington Marketplace.')
            return redirect('marketplace:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('marketplace:home')
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                if user.is_staff or user.is_superuser:
                    return redirect('admin:index')
                if user.is_seller:
                    return redirect('seller_dashboard')
                return redirect('buyer_dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('/')


def admin_logout_view(request):
    auth_logout(request)
    return redirect('/')


def profile_view(request, pk):
    profile_user = get_object_or_404(User, pk=pk)
    seller_requests = profile_user.seller_requests.all()
    products = profile_user.products.filter(status='APPROVED') if profile_user.is_seller else None
    context = {
        'profile_user': profile_user,
        'seller_requests': seller_requests,
        'products': products,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile', pk=request.user.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
@admin_users_forbidden
def become_seller_view(request):
    existing = SellerRequest.objects.filter(user=request.user).first()
    if existing and existing.status == 'PENDING':
        messages.info(request, 'Your seller request is already pending admin approval.')
        return render(request, 'accounts/become_seller.html', {'pending_request': existing})
    if request.user.is_seller:
        messages.info(request, 'You are already an approved seller.')
        return redirect('seller_dashboard')

    if request.method == 'POST':
        form = SellerRequestForm(request.POST)
        if form.is_valid():
            seller_request = form.save(commit=False)
            seller_request.user = request.user
            seller_request.save()
            messages.success(request, 'Seller request submitted successfully! Awaiting admin approval.')
            return redirect('marketplace:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SellerRequestForm()
    return render(request, 'accounts/become_seller.html', {'form': form})
