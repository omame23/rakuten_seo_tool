"""
URL configuration for inspice_seo_tool project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.views.generic import TemplateView
from seo_ranking import views
from accounts.views_signup import CustomSignupView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/signup/', CustomSignupView.as_view(), name='account_signup'),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('seo/', include('seo_ranking.urls')),
    path('webhooks/', include('accounts.webhook_urls')),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'inspice_seo_tool.views.custom_404'
handler500 = 'inspice_seo_tool.views.custom_500'
handler403 = 'inspice_seo_tool.views.custom_403'
handler400 = 'inspice_seo_tool.views.custom_400'
