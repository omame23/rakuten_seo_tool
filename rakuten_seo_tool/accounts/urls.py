from django.urls import path
from .views import DashboardView, account_settings, billing_info

app_name = 'accounts'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('settings/', account_settings, name='settings'),
    path('billing/', billing_info, name='billing'),
    # confirm_email はallauthのデフォルト処理に任せる
]