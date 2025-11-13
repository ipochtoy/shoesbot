"""
URL configuration for shoessite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from apps.marketplaces.ebay import views as ebay_views

urlpatterns = [
    path('', RedirectView.as_view(url='/photos/sorting/', permanent=False)),
    path('admin/', admin.site.urls),
    path('photos/', include('photos.urls')),
    path('about/', TemplateView.as_view(template_name='static/about.html'), name='about'),
    path('privacy/', TemplateView.as_view(template_name='static/privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='static/terms.html'), name='terms'),

    # eBay marketplace integration
    path('oauth/ebay/success/', ebay_views.ebay_oauth_success, name='ebay-oauth-success'),
    path('oauth/ebay/cancel/', ebay_views.ebay_oauth_cancel, name='ebay-oauth-cancel'),
    path('api/ebay/', include('apps.marketplaces.ebay.urls')),
    path('ebay/', include('apps.marketplaces.ebay.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
