"""
RPP広告順位関連のフォーム
"""

from django import forms
from django.core.exceptions import ValidationError
from .models_rpp import RPPKeyword


class RPPKeywordForm(forms.ModelForm):
    """RPPキーワード登録フォーム"""
    
    class Meta:
        model = RPPKeyword
        fields = ['keyword', 'rakuten_shop_id', 'target_product_url', 'is_active']
        widgets = {
            'keyword': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'スニーカー メンズ',
                'maxlength': 255
            }),
            'rakuten_shop_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'your-shop-id'
            }),
            'target_product_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://item.rakuten.co.jp/your-shop/item-id/'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        help_texts = {
            'keyword': 'RPP広告を追跡したいキーワードを入力してください（例：スニーカー メンズ）',
            'rakuten_shop_id': 'あなたの楽天店舗IDを入力してください',
            'target_product_url': '特定の商品URLを指定すると、より正確な順位判定が可能です（任意）',
            'is_active': 'チェックすると自動検索の対象になります'
        }
    
    def __init__(self, *args, user=None, selected_store=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.selected_store = selected_store
        # 実際の対象ユーザーを設定（マスターアカウントの場合は選択店舗、通常は自分）
        self.target_user = selected_store if (user and user.is_master and selected_store) else user
        
        # マスターアカウントが選択店舗でキーワードを登録する場合
        if user and user.is_master and selected_store:
            # 楽天店舗IDを自動設定して読み取り専用にする
            self.fields['rakuten_shop_id'].initial = selected_store.rakuten_shop_id
            self.fields['rakuten_shop_id'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control bg-light',
                'title': f'選択店舗: {selected_store.company_name}'
            })
        elif user and not user.is_master:
            # 通常ユーザーは自分の店舗IDを自動設定
            self.fields['rakuten_shop_id'].widget = forms.HiddenInput()
            self.fields['rakuten_shop_id'].initial = user.rakuten_shop_id
    
    def clean_keyword(self):
        keyword = self.cleaned_data.get('keyword')
        if not keyword:
            raise ValidationError('キーワードは必須です。')
        
        # キーワードの長さチェック
        if len(keyword) > 100:
            raise ValidationError('キーワードは100文字以内で入力してください。')
        
        # 禁止文字チェック
        invalid_chars = ['<', '>', '"', "'", '&']
        for char in invalid_chars:
            if char in keyword:
                raise ValidationError(f'キーワードに使用できない文字が含まれています: {char}')
        
        return keyword.strip()
    
    def clean_rakuten_shop_id(self):
        shop_id = self.cleaned_data.get('rakuten_shop_id')
        if not shop_id:
            raise ValidationError('楽天店舗IDは必須です。')
        
        # 店舗IDの形式チェック
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', shop_id):
            raise ValidationError('楽天店舗IDは英数字、ハイフン、アンダースコアのみ使用可能です。')
        
        return shop_id.strip()
    
    def clean(self):
        cleaned_data = super().clean()
        keyword = cleaned_data.get('keyword')
        shop_id = cleaned_data.get('rakuten_shop_id')
        
        # 重複チェック
        if keyword and shop_id and self.target_user:
            existing = RPPKeyword.objects.filter(
                user=self.target_user,
                keyword=keyword,
                rakuten_shop_id=shop_id
            )
            
            # 編集時は自分自身を除外
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(
                    f'キーワード「{keyword}」は既に店舗ID「{shop_id}」で登録されています。'
                )
        
        # キーワード登録数制限チェック（マスターアカウント以外）
        if self.target_user and not self.user.is_master:
            current_count = RPPKeyword.objects.filter(user=self.target_user).count()
            
            # 新規登録の場合のみチェック
            if not (self.instance and self.instance.pk):
                if current_count >= 10:
                    raise ValidationError(
                        'RPPキーワード登録数の上限（10個）に達しています。'
                        '既存のキーワードを削除してから登録してください。'
                    )
        
        return cleaned_data


class BulkRPPKeywordForm(forms.Form):
    """RPPキーワード一括登録フォーム"""
    
    keywords = forms.CharField(
        label='RPPキーワード（複数）',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': '''例：
スニーカー メンズ
ランニングシューズ
バスケットシューズ 白
サッカーシューズ ジュニア''',
        }),
        help_text='改行で区切って複数のキーワードを入力してください（最大10個）'
    )
    
    rakuten_shop_id = forms.CharField(
        label='楽天店舗ID',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'your-shop-id'
        }),
        help_text='あなたの楽天店舗IDを入力してください'
    )
    
    target_product_url = forms.URLField(
        label='対象商品URL',
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://item.rakuten.co.jp/your-shop/item-id/'
        }),
        help_text='特定の商品URLを指定すると、より正確な順位判定が可能です（任意）'
    )
    
    is_active = forms.BooleanField(
        label='有効にする',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='チェックすると自動検索の対象になります'
    )
    
    def __init__(self, *args, user=None, selected_store=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.selected_store = selected_store
        # 実際の対象ユーザーを設定（マスターアカウントの場合は選択店舗、通常は自分）
        self.target_user = selected_store if (user and user.is_master and selected_store) else user
        
        # マスターアカウントが選択店舗でキーワードを登録する場合
        if user and user.is_master and selected_store:
            # 楽天店舗IDを自動設定して読み取り専用にする
            self.fields['rakuten_shop_id'].initial = selected_store.rakuten_shop_id
            self.fields['rakuten_shop_id'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control bg-light',
                'title': f'選択店舗: {selected_store.company_name}'
            })
        elif user and not user.is_master:
            # 通常ユーザーは自分の店舗IDを自動設定
            self.fields['rakuten_shop_id'].widget = forms.HiddenInput()
            self.fields['rakuten_shop_id'].initial = user.rakuten_shop_id
    
    def clean_keywords(self):
        keywords_text = self.cleaned_data.get('keywords', '')
        if not keywords_text.strip():
            raise ValidationError('キーワードは必須です。')
        
        # 改行で分割してキーワードリストを作成
        keywords = []
        for line in keywords_text.strip().split('\n'):
            keyword = line.strip()
            if keyword:  # 空行は無視
                keywords.append(keyword)
        
        if not keywords:
            raise ValidationError('有効なキーワードを入力してください。')
        
        if len(keywords) > 10:
            raise ValidationError('一括登録できるキーワードは最大10個です。')
        
        # 各キーワードの妥当性をチェック
        validated_keywords = []
        for keyword in keywords:
            if len(keyword) > 100:
                raise ValidationError(f'キーワード「{keyword}」は100文字以内で入力してください。')
            
            # 禁止文字チェック
            invalid_chars = ['<', '>', '"', "'", '&']
            for char in invalid_chars:
                if char in keyword:
                    raise ValidationError(f'キーワード「{keyword}」に使用できない文字が含まれています: {char}')
            
            validated_keywords.append(keyword.strip())
        
        # 重複チェック
        unique_keywords = list(set(validated_keywords))
        if len(unique_keywords) != len(validated_keywords):
            raise ValidationError('重複するキーワードがあります。')
        
        return unique_keywords
    
    def clean_rakuten_shop_id(self):
        shop_id = self.cleaned_data.get('rakuten_shop_id')
        if not shop_id:
            raise ValidationError('楽天店舗IDは必須です。')
        
        # 店舗IDの形式チェック
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', shop_id):
            raise ValidationError('楽天店舗IDは英数字、ハイフン、アンダースコアのみ使用可能です。')
        
        return shop_id.strip()
    
    def clean(self):
        cleaned_data = super().clean()
        keywords = cleaned_data.get('keywords', [])
        shop_id = cleaned_data.get('rakuten_shop_id')
        
        # 登録数制限チェック（マスターアカウント以外）
        if self.target_user and not self.user.is_master and keywords:
            current_count = RPPKeyword.objects.filter(user=self.target_user).count()
            new_count = len(keywords)
            
            if current_count + new_count > 10:
                available_slots = 10 - current_count
                raise ValidationError(
                    f'登録可能なキーワードは残り{available_slots}個です。'
                    f'{new_count}個のキーワードを登録しようとしていますが、上限を超えています。'
                )
        
        return cleaned_data