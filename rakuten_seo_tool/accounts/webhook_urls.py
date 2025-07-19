from django.urls import path
from .webhook_views import stripe_webhook

urlpatterns = [
    path('stripe/', stripe_webhook, name='stripe_webhook'),
]