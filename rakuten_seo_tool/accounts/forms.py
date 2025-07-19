from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
from allauth.account.forms import SignupForm
from .models import User


class CustomSignupForm(SignupForm):
    """カスタム会員登録フォーム"""
    
    # バリデーター定義
    phone_validator = RegexValidator(
        regex=r'^[0-9\-]+$',
        message='電話番号は数字とハイフンのみ入力してください。'
    )
    
    company_name = forms.CharField(
        max_length=255,
        label='会社名',
        help_text='正式な会社名・屋号を入力してください',
        widget=forms.TextInput(attrs={
            'placeholder': '株式会社○○',
            'class': 'form-control',
            'required': True
        })
    )
    
    contact_name = forms.CharField(
        max_length=100,
        label='担当者名',
        help_text='ご担当者様のお名前を入力してください',
        widget=forms.TextInput(attrs={
            'placeholder': '山田太郎',
            'class': 'form-control',
            'required': True
        })
    )
    
    phone_number = forms.CharField(
        max_length=20,
        label='電話番号',
        validators=[phone_validator],
        help_text='連絡可能な電話番号を入力してください',
        widget=forms.TextInput(attrs={
            'placeholder': '03-1234-5678',
            'class': 'form-control',
            'required': True
        })
    )
    
    rakuten_shop_id = forms.CharField(
        max_length=100,
        label='楽天店舗ID（必須）',
        required=True,
        help_text='楽天市場の店舗IDを入力してください',
        widget=forms.TextInput(attrs={
            'placeholder': '例：rakuten-shop',
            'class': 'form-control',
            'required': True
        })
    )
    
    subscription_plan = forms.ChoiceField(
        choices=[
            ('standard', 'スタンダードプラン（¥2,980/月）'),
            ('master', 'マスタープラン（¥4,980/月）'),
        ],
        initial='standard',
        label='サブスクリプションプラン',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    terms_agreement = forms.BooleanField(
        label='利用規約とプライバシーポリシーに同意する',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    field_order = ['email', 'password1', 'password2', 'company_name', 'contact_name', 'phone_number', 'rakuten_shop_id', 'subscription_plan', 'terms_agreement']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # allauthのデフォルトフィールドを無効化
        if 'username' in self.fields:
            del self.fields['username']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('このメールアドレスは既に登録されています。')
        return email
    
    def clean_company_name(self):
        company_name = self.cleaned_data.get('company_name')
        if len(company_name.strip()) < 2:
            raise forms.ValidationError('会社名は2文字以上で入力してください。')
        return company_name.strip()
    
    def clean_contact_name(self):
        contact_name = self.cleaned_data.get('contact_name')
        if len(contact_name.strip()) < 2:
            raise forms.ValidationError('担当者名は2文字以上で入力してください。')
        return contact_name.strip()
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # ハイフンを除去して数字のみをチェック
        numbers_only = phone_number.replace('-', '')
        if len(numbers_only) < 10 or len(numbers_only) > 11:
            raise forms.ValidationError('電話番号は10〜11桁で入力してください。')
        return phone_number
    
    def clean_rakuten_shop_id(self):
        shop_id = self.cleaned_data.get('rakuten_shop_id')
        if not shop_id:
            raise forms.ValidationError('楽天店舗IDは必須です。')
        if len(shop_id.strip()) < 3:
            raise forms.ValidationError('楽天店舗IDは3文字以上で入力してください。')
        
        # 重複チェック（マスターアカウント以外）
        # 新規登録時は常にマスターアカウントではないので、重複チェックを行う
        if User.objects.filter(rakuten_shop_id=shop_id.strip(), is_master=False).exists():
            raise forms.ValidationError('この楽天店舗IDは既に登録されています。')
        
        return shop_id.strip()
    
    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.company_name = self.cleaned_data['company_name']
        user.contact_name = self.cleaned_data['contact_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.rakuten_shop_id = self.cleaned_data.get('rakuten_shop_id', '')
        
        # 選択されたプランを設定
        user.subscription_plan = self.cleaned_data.get('subscription_plan', 'standard')
        
        # 決済前なので一旦 inactive に設定
        user.subscription_status = 'inactive'
        
        user.save()
        
        # 選択されたプランをセッションに保存
        if hasattr(request, 'session'):
            request.session['user_selected_plan'] = user.subscription_plan
            request.session['user_id_for_checkout'] = user.id
        
        return user