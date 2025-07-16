from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'company_name', 'contact_name', 'subscription_status', 'is_master', 'date_joined', 'is_active')
    list_filter = ('subscription_status', 'is_active', 'is_staff', 'is_master', 'date_joined')
    search_fields = ('email', 'company_name', 'contact_name', 'rakuten_shop_id')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('会社情報', {'fields': ('company_name', 'contact_name', 'phone_number', 'rakuten_shop_id')}),
        ('サブスクリプション', {'fields': ('subscription_status', 'stripe_customer_id', 'trial_end_date', 'subscription_end_date')}),
        ('権限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_master', 'groups', 'user_permissions')}),
        ('重要な日付', {'fields': ('date_joined', 'last_login')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'company_name', 'contact_name', 'phone_number'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')