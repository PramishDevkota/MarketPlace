from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

ADMIN_ACTION_BLOCKED_MESSAGE = (
    'Admin users cannot buy or sell products. Use the Admin Dashboard for moderation.'
)


def admin_users_forbidden(view_func):
    """Block admin (staff/superuser) accounts from buyer/seller storefront actions.

    Admins are redirected to the Django Admin panel with a warning message.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            messages.warning(request, ADMIN_ACTION_BLOCKED_MESSAGE)
            return redirect('admin:index')
        return view_func(request, *args, **kwargs)

    return _wrapped_view
