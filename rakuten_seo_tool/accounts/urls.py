from django.urls import path
from .views import (
    DashboardView, account_settings, billing_info,
    create_subscription, change_plan, cancel_subscription
)
from .views_master import (
    StoreListView, StoreDetailView, StoreCreateView, 
    StoreUpdateView, StoreDeleteView, store_export_csv,
    store_bulk_action, set_selected_store, view_store_dashboard,
    revenue_dashboard
)

app_name = 'accounts'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('settings/', account_settings, name='settings'),
    path('billing/', billing_info, name='billing'),
    path('billing/subscribe/', create_subscription, name='create_subscription'),
    path('billing/change-plan/', change_plan, name='change_plan'),
    path('billing/cancel/', cancel_subscription, name='cancel_subscription'),
    
    # マスターアカウント専用 - 店舗管理
    path('master/stores/', StoreListView.as_view(), name='master_store_list'),
    path('master/stores/create/', StoreCreateView.as_view(), name='master_store_create'),
    path('master/stores/<int:pk>/', StoreDetailView.as_view(), name='master_store_detail'),
    path('master/stores/<int:pk>/edit/', StoreUpdateView.as_view(), name='master_store_update'),
    path('master/stores/<int:pk>/delete/', StoreDeleteView.as_view(), name='master_store_delete'),
    path('master/stores/<int:pk>/dashboard/', view_store_dashboard, name='master_view_store_dashboard'),
    path('master/stores/export/', store_export_csv, name='master_store_export'),
    path('master/stores/bulk-action/', store_bulk_action, name='master_store_bulk_action'),
    path('master/set-selected-store/', set_selected_store, name='master_set_selected_store'),
    
    # マスターアカウント専用 - 売上管理
    path('master/revenue/', revenue_dashboard, name='master_revenue_dashboard'),
    
    # confirm_email はallauthのデフォルト処理に任せる
]