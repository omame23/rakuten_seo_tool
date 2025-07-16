from django import forms
from .models import Keyword


class KeywordForm(forms.ModelForm):
    """キーワード登録・編集フォーム（単体用）"""
    
    class Meta:
        model = Keyword
        fields = ['keyword', 'rakuten_shop_id', 'target_product_url', 'is_active']
        widgets = {
            'keyword': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '検索キーワードを入力してください',
                'required': True
            }),
            'rakuten_shop_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '楽天店舗IDを入力してください',
                'required': True
            }),
            'target_product_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://item.rakuten.co.jp/...',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.selected_store = kwargs.pop('selected_store', None)
        super().__init__(*args, **kwargs)
        
        # マスターアカウントが選択店舗でキーワードを登録する場合
        if self.user and self.user.is_master and self.selected_store:
            # 楽天店舗IDを自動設定して読み取り専用にする
            self.fields['rakuten_shop_id'].initial = self.selected_store.rakuten_shop_id
            self.fields['rakuten_shop_id'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control bg-light',
                'title': f'選択店舗: {self.selected_store.company_name}'
            })
        elif self.user and not self.user.is_master:
            # 通常ユーザーは自分の店舗IDを自動設定
            self.fields['rakuten_shop_id'].initial = self.user.rakuten_shop_id
            self.fields['rakuten_shop_id'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control bg-light'
            })
        self.fields['keyword'].help_text = '楽天市場で検索するキーワードを入力してください'
        self.fields['rakuten_shop_id'].help_text = '順位を確認したい楽天店舗のIDを入力してください'
        self.fields['target_product_url'].help_text = '特定の商品URLを指定する場合は入力してください（オプション）'
        self.fields['is_active'].help_text = '有効にすると自動検索の対象になります'
        
        # マスターアカウント以外は店舗IDを固定
        if self.user and not self.user.is_master:
            self.fields['rakuten_shop_id'].widget = forms.HiddenInput()
            self.fields['rakuten_shop_id'].initial = self.user.rakuten_shop_id
            self.fields['rakuten_shop_id'].help_text = ''
    
    def clean_keyword(self):
        keyword = self.cleaned_data.get('keyword')
        if not keyword:
            raise forms.ValidationError('キーワードは必須です。')
        if len(keyword) < 2:
            raise forms.ValidationError('キーワードは2文字以上で入力してください。')
        return keyword.strip()
    
    def clean_rakuten_shop_id(self):
        shop_id = self.cleaned_data.get('rakuten_shop_id')
        if not shop_id:
            raise forms.ValidationError('楽天店舗IDは必須です。')
        
        # マスターアカウント以外は自分の店舗IDのみ許可
        if self.user and not self.user.is_master:
            if shop_id.strip() != self.user.rakuten_shop_id:
                raise forms.ValidationError('契約されている店舗ID以外は使用できません。')
        
        return shop_id.strip()
    
    def clean_target_product_url(self):
        url = self.cleaned_data.get('target_product_url')
        if url:
            if not url.startswith('https://item.rakuten.co.jp/'):
                raise forms.ValidationError('楽天商品URLは https://item.rakuten.co.jp/ で始まる必要があります。')
            
            # マスターアカウント以外は自分の店舗URLのみ許可
            if self.user and not self.user.is_master:
                # URLから店舗IDを抽出 (https://item.rakuten.co.jp/店舗ID/商品ID/)
                import re
                match = re.match(r'https://item\.rakuten\.co\.jp/([^/]+)/', url)
                if match:
                    url_shop_id = match.group(1)
                    if url_shop_id != self.user.rakuten_shop_id:
                        raise forms.ValidationError('契約されている店舗の商品URL以外は使用できません。')
        
        return url


class BulkKeywordForm(forms.Form):
    """キーワード一括登録フォーム"""
    
    keywords = forms.CharField(
        label='キーワード一覧',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'キーワードを改行で区切って入力してください\n例：\n楽天 商品名\nショップ名 商品\nブランド名 アイテム',
            'required': True
        })
    )
    
    rakuten_shop_id = forms.CharField(
        label='楽天店舗ID',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '楽天店舗IDを入力してください',
            'required': True
        }),
        help_text='全てのキーワードに適用される楽天店舗ID'
    )
    
    target_product_url = forms.URLField(
        label='対象商品URL（オプション）',
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://item.rakuten.co.jp/...',
        }),
        help_text='特定の商品URLを指定する場合は入力してください（全てのキーワードに適用されます）'
    )
    
    is_active = forms.BooleanField(
        label='有効',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        help_text='有効にすると自動検索の対象になります'
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.selected_store = kwargs.pop('selected_store', None)
        super().__init__(*args, **kwargs)
        
        # マスターアカウントが選択店舗でキーワードを登録する場合
        if self.user and self.user.is_master and self.selected_store:
            # 楽天店舗IDを自動設定して読み取り専用にする
            self.fields['rakuten_shop_id'].initial = self.selected_store.rakuten_shop_id
            self.fields['rakuten_shop_id'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control bg-light',
                'title': f'選択店舗: {self.selected_store.company_name}'
            })
            self.fields['keywords'].help_text = '改行で区切って複数のキーワードを入力できます（最大10個まで）'
        elif self.user and not self.user.is_master:
            # 通常ユーザーは自分の店舗IDを自動設定
            self.fields['rakuten_shop_id'].initial = self.user.rakuten_shop_id
            self.fields['rakuten_shop_id'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control bg-light'
            })
            self.fields['keywords'].help_text = '改行で区切って複数のキーワードを入力できます（最大10個まで）'
        else:
            # マスターアカウントで店舗未選択の場合
            self.fields['keywords'].help_text = '改行で区切って複数のキーワードを入力できます（最大50個まで）'
    
    def clean_keywords(self):
        keywords_text = self.cleaned_data.get('keywords')
        if not keywords_text:
            raise forms.ValidationError('キーワードは必須です。')
        
        # 改行で分割してキーワードリストを作成
        keywords_list = [kw.strip() for kw in keywords_text.split('\n') if kw.strip()]
        
        if not keywords_list:
            raise forms.ValidationError('有効なキーワードが入力されていません。')
        
        # ユーザーに応じた最大数チェック
        if self.user and not self.user.is_master:
            # 現在の登録数を取得
            from .models import Keyword
            current_count = Keyword.objects.filter(user=self.user).count()
            remaining = 10 - current_count
            
            if remaining <= 0:
                raise forms.ValidationError('キーワード登録数の上限（10個）に達しています。')
            
            if len(keywords_list) > remaining:
                raise forms.ValidationError(f'登録可能なキーワード数は残り{remaining}個です。')
        else:
            if len(keywords_list) > 50:
                raise forms.ValidationError('キーワードは最大50個まで登録できます。')
        
        # 各キーワードの長さチェック
        for keyword in keywords_list:
            if len(keyword) < 2:
                raise forms.ValidationError(f'キーワード「{keyword}」は2文字以上で入力してください。')
            if len(keyword) > 100:
                raise forms.ValidationError(f'キーワード「{keyword}」は100文字以内で入力してください。')
        
        return keywords_list
    
    def clean_rakuten_shop_id(self):
        shop_id = self.cleaned_data.get('rakuten_shop_id')
        if not shop_id:
            raise forms.ValidationError('楽天店舗IDは必須です。')
        
        # マスターアカウント以外は自分の店舗IDのみ許可
        if self.user and not self.user.is_master:
            if shop_id.strip() != self.user.rakuten_shop_id:
                raise forms.ValidationError('契約されている店舗ID以外は使用できません。')
        
        return shop_id.strip()
    
    def clean_target_product_url(self):
        url = self.cleaned_data.get('target_product_url')
        if url:
            if not url.startswith('https://item.rakuten.co.jp/'):
                raise forms.ValidationError('楽天商品URLは https://item.rakuten.co.jp/ で始まる必要があります。')
            
            # マスターアカウント以外は自分の店舗URLのみ許可
            if self.user and not self.user.is_master:
                import re
                match = re.match(r'https://item\.rakuten\.co\.jp/([^/]+)/', url)
                if match:
                    url_shop_id = match.group(1)
                    if url_shop_id != self.user.rakuten_shop_id:
                        raise forms.ValidationError('契約されている店舗の商品URL以外は使用できません。')
        
        return url