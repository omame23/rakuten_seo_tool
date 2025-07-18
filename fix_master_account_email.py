#!/usr/bin/env python
"""
マスターアカウントのメール認証済み状態を設定するスクリプト
"""
import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inspice_seo_tool.settings')
django.setup()

from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()

def fix_master_account_email():
    """マスターアカウントのメール認証済み状態を設定"""
    
    try:
        # マスターアカウントを取得
        master_user = User.objects.get(is_master=True)
        print(f"マスターアカウントを確認: {master_user.email}")
        
        # EmailAddressレコードを確認・作成
        email_address, created = EmailAddress.objects.get_or_create(
            user=master_user,
            email=master_user.email,
            defaults={
                'verified': True,
                'primary': True
            }
        )
        
        if created:
            print(f"EmailAddressレコードを作成: {email_address.email}")
        else:
            # 既存のレコードを認証済みに更新
            email_address.verified = True
            email_address.primary = True
            email_address.save()
            print(f"EmailAddressレコードを更新: {email_address.email}")
        
        print("✅ マスターアカウントのメール認証設定完了")
        
    except User.DoesNotExist:
        print("❌ マスターアカウントが見つかりません")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    fix_master_account_email()