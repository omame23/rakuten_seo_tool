#!/usr/bin/env python
"""
手動でメール認証を完了させるスクリプト
"""
import os
import sys
import django

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inspice_seo_tool.settings')
django.setup()

from accounts.models import User
from allauth.account.models import EmailAddress

def verify_all_users():
    """すべてのユーザーのメールアドレスを認証済みにする"""
    users = User.objects.all()
    
    for user in users:
        email_address, created = EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={
                'verified': True,
                'primary': True,
            }
        )
        
        if not created:
            email_address.verified = True
            email_address.primary = True
            email_address.save()
        
        print(f"認証完了: {user.email}")

if __name__ == '__main__':
    verify_all_users()
    print("すべてのユーザーのメール認証が完了しました。")