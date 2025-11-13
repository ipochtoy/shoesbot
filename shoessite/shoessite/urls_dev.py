"""
URL configuration for shoessite project - DEV version with /dev/ prefix.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from apps.marketplaces.ebay import views as ebay_views

urlpatterns = [
    path('dev/', include([
        path('', RedirectView.as_view(url='/dev/photos/sorting/', permanent=False)),
        path('admin/', admin.site.urls),
        path('photos/', include('photos.urls')),
        path('about/', TemplateView.as_view(template_name='static/about.html'), name='dev-about'),
        path('privacy/', TemplateView.as_view(template_name='static/privacy.html'), name='dev-privacy'),
        path('terms/', TemplateView.as_view(template_name='static/terms.html'), name='dev-terms'),
        path('oauth/ebay/success/', ebay_views.ebay_oauth_success, name='dev-ebay-oauth-success'),
        path('oauth/ebay/cancel/', ebay_views.ebay_oauth_cancel, name='dev-ebay-oauth-cancel'),
        path('api/ebay/', include('apps.marketplaces.ebay.urls')),
        path('ebay/', include('apps.marketplaces.ebay.urls')),
    ])),
    # Also include non-prefixed URLs for API calls from JavaScript
    path('admin/', admin.site.urls),
    path('about/', TemplateView.as_view(template_name='static/about.html'), name='about'),
    path('privacy/', TemplateView.as_view(template_name='static/privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='static/terms.html'), name='terms'),
    path('oauth/ebay/success/', ebay_views.ebay_oauth_success, name='ebay-oauth-success'),
    path('oauth/ebay/cancel/', ebay_views.ebay_oauth_cancel, name='ebay-oauth-cancel'),
    path('api/ebay/', include('apps.marketplaces.ebay.urls')),
    path('ebay/', include('apps.marketplaces.ebay.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

