#!/usr/bin/env python
"""
指定したアカウントをマスターアカウントに設定するスクリプト
"""
import os
import sys
import django

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inspice_seo_tool.settings')
django.setup()

from accounts.models import User

def set_master_account():
    """segishogo@gmail.comをマスターアカウントに設定"""
    try:
        user = User.objects.get(email='segishogo@gmail.com')
        user.is_master = True
        user.subscription_status = 'active'  # アクティブな状態に
        user.save()
        
        print(f"✅ マスターアカウント設定完了: {user.email}")
        print(f"   - 会社名: {user.company_name}")
        print(f"   - 担当者: {user.contact_name}")
        print(f"   - マスター権限: {user.is_master}")
        print(f"   - サブスクリプション: {user.subscription_status}")
        print(f"   - 全店舗アクセス: {user.can_access_all_stores()}")
        
    except User.DoesNotExist:
        print("❌ エラー: segishogo@gmail.com が見つかりません")
        print("利用可能なユーザー:")
        for user in User.objects.all():
            print(f"  - {user.email}")

if __name__ == '__main__':
    set_master_account()