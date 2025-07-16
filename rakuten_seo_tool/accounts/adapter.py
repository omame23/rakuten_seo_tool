from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_field
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib import messages

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    
    def save_user(self, request, user, form, commit=True):
        """
        カスタムユーザーモデル用のユーザー保存処理
        """
        data = form.cleaned_data
        
        # 基本情報の設定
        user_field(user, 'email', data.get('email'))
        
        # パスワードの設定
        if 'password1' in data:
            user.set_password(data['password1'])
        
        # カスタムフィールドの設定
        if hasattr(form, 'cleaned_data'):
            user_field(user, 'company_name', data.get('company_name'))
            user_field(user, 'contact_name', data.get('contact_name'))
            user_field(user, 'phone_number', data.get('phone_number'))
            user_field(user, 'rakuten_shop_id', data.get('rakuten_shop_id', ''))
        
        if commit:
            user.save()
        
        return user
    
    def clean_username(self, username, shallow=False):
        """
        ユーザーネームのクリーニング（メールベース認証では不要）
        """
        return username
    
    def populate_username(self, request, user):
        """
        ユーザーネームの自動生成（メールベース認証では不要）
        """
        # メールアドレスをベースにした一意のユーザーネームを生成
        # ただし、実際には使用されない
        return user.email
    
    def get_login_redirect_url(self, request):
        """
        ログイン後のリダイレクト先をカスタマイズ
        """
        # メール認証完了後のログインも含めて、ダッシュボードにリダイレクト
        return reverse('accounts:dashboard')