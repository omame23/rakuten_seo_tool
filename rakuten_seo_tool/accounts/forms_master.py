from django import forms
from .models import User


class StoreCreateForm(forms.ModelForm):
    """新規店舗追加用フォーム（楽天店舗IDのみ必須）"""
    
    class Meta:
        model = User
        fields = ['rakuten_shop_id']
        widgets = {
            'rakuten_shop_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例: my-shop-123',
                'required': True
            }),
        }
        labels = {
            'rakuten_shop_id': '楽天店舗ID',
        }
        help_texts = {
            'rakuten_shop_id': '楽天市場の店舗IDを入力してください',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 楽天店舗IDを必須に設定
        self.fields['rakuten_shop_id'].required = True

    def clean_rakuten_shop_id(self):
        """楽天店舗IDの重複チェック"""
        rakuten_shop_id = self.cleaned_data.get('rakuten_shop_id')
        
        if not rakuten_shop_id:
            raise forms.ValidationError('楽天店舗IDは必須です。')
        
        # 重複チェック（マスターアカウント以外）
        existing_user = User.objects.filter(
            rakuten_shop_id=rakuten_shop_id,
            is_master=False
        ).exclude(pk=self.instance.pk if self.instance.pk else None)
        
        if existing_user.exists():
            raise forms.ValidationError('この楽天店舗IDは既に登録されています。')
        
        return rakuten_shop_id

    def save(self, commit=True):
        """店舗の保存処理"""
        user = super().save(commit=False)
        
        # デフォルト値を設定
        if not user.email:
            # 楽天店舗IDからメールアドレスを生成
            user.email = f"{user.rakuten_shop_id}@temp.example.com"
        
        if not user.company_name:
            user.company_name = f"店舗_{user.rakuten_shop_id}"
        
        if not user.contact_name:
            user.contact_name = "未設定"
        
        if not user.phone_number:
            user.phone_number = "000-0000-0000"
        
        # マスターアカウントではない
        user.is_master = False
        user.is_active = True
        user.subscription_status = 'trial'  # デフォルトでトライアル
        
        # 一時パスワードを設定
        user.set_password('temppass123')
        
        if commit:
            user.save()
        
        return user


class StoreUpdateForm(forms.ModelForm):
    """店舗編集用フォーム（全項目編集可能）"""
    
    class Meta:
        model = User
        fields = [
            'email', 'rakuten_shop_id', 'company_name', 
            'contact_name', 'phone_number', 'subscription_status', 'is_active'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rakuten_shop_id': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'subscription_status': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_rakuten_shop_id(self):
        """楽天店舗IDの重複チェック"""
        rakuten_shop_id = self.cleaned_data.get('rakuten_shop_id')
        
        if not rakuten_shop_id:
            raise forms.ValidationError('楽天店舗IDは必須です。')
        
        # 重複チェック（自分以外のマスターアカウント以外）
        existing_user = User.objects.filter(
            rakuten_shop_id=rakuten_shop_id,
            is_master=False
        ).exclude(pk=self.instance.pk if self.instance.pk else None)
        
        if existing_user.exists():
            raise forms.ValidationError('この楽天店舗IDは既に登録されています。')
        
        return rakuten_shop_id