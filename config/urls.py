from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from marketplace.views import seller_dashboard_view, buyer_dashboard_view
from accounts.views import admin_logout_view

urlpatterns = [
    path('admin/logout/', admin_logout_view),
    path('admin/', admin.site.urls),
    path('seller/dashboard/', seller_dashboard_view, name='seller_dashboard'),
    path('dashboard/', buyer_dashboard_view, name='buyer_dashboard'),
    path('', include('marketplace.urls')),
    path('accounts/', include('accounts.urls')),
    path('orders/', include('orders.urls')),
    path('messages/', include('messaging.urls')),
    path('reviews/', include('reviews.urls')),
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
