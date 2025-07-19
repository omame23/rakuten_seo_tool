from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です')
        # マスターアカウント以外は楽天店舗IDが必須
        if not extra_fields.get('is_master', False) and not extra_fields.get('rakuten_shop_id'):
            raise ValueError('楽天店舗IDは必須です')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        verbose_name='メールアドレス',
        max_length=255,
        unique=True,
    )
    company_name = models.CharField(
        verbose_name='会社名',
        max_length=255,
    )
    contact_name = models.CharField(
        verbose_name='担当者名',
        max_length=100,
    )
    phone_number = models.CharField(
        verbose_name='電話番号',
        max_length=20,
    )
    rakuten_shop_id = models.CharField(
        verbose_name='楽天店舗ID',
        max_length=100,
        blank=False,
        null=True,  # 既存データの互換性のため一時的にnull=Trueを残す
    )
    is_active = models.BooleanField(
        verbose_name='有効',
        default=True,
    )
    is_staff = models.BooleanField(
        verbose_name='スタッフ権限',
        default=False,
    )
    date_joined = models.DateTimeField(
        verbose_name='登録日時',
        default=timezone.now,
    )
    
    # 支払い関連
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    subscription_status = models.CharField(
        verbose_name='サブスクリプション状態',
        max_length=20,
        choices=[
            ('trial', '無料トライアル'),
            ('active', '有効'),
            ('past_due', '支払い遅延'),
            ('canceled', 'キャンセル'),
            ('inactive', '無効'),
        ],
        default='inactive',
    )
    subscription_plan = models.CharField(
        verbose_name='サブスクリプションプラン',
        max_length=20,
        choices=[
            ('standard', 'スタンダードプラン'),
            ('master', 'マスタープラン'),
        ],
        default='standard',
        help_text='スタンダード: 2,980円/月 (SEO&RPP各30個), マスター: 4,980円/月 (SEO&RPP各100個)'
    )
    trial_end_date = models.DateTimeField(
        verbose_name='トライアル終了日',
        blank=True,
        null=True,
    )
    subscription_end_date = models.DateTimeField(
        verbose_name='サブスクリプション終了日',
        blank=True,
        null=True,
    )
    
    # マスターアカウント設定
    is_master = models.BooleanField(
        verbose_name='マスターアカウント',
        default=False,
        help_text='全機能・全店舗データにアクセス可能'
    )
    
    # 招待ユーザー設定
    is_invited_user = models.BooleanField(
        verbose_name='招待ユーザー',
        default=False,
        help_text='マスターアカウントから招待されたユーザー（ダッシュボードに表示）'
    )
    
    # 自動検索設定
    auto_seo_search_enabled = models.BooleanField(
        verbose_name='SEO自動検索有効',
        default=True,
        help_text='毎日深夜に自動でSEOキーワード順位を確認する'
    )
    auto_rpp_search_enabled = models.BooleanField(
        verbose_name='RPP自動検索有効',
        default=True,
        help_text='毎日深夜に自動でRPPキーワード順位を確認する'
    )
    auto_search_time = models.TimeField(
        verbose_name='自動検索時間',
        default='10:00',
        help_text='毎日自動検索を実行する時間（24時間形式・マスターアカウントのみ有効）',
        blank=True,
        null=True
    )
    last_bulk_search_date = models.DateField(
        verbose_name='最終一括検索日',
        blank=True,
        null=True,
        help_text='最後に一括検索を実行した日付'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['company_name', 'contact_name', 'phone_number']

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
        db_table = 'users'

    def __str__(self):
        return self.email

    def has_active_subscription(self):
        """有効なサブスクリプションを持っているかチェック"""
        # マスターアカウントは常に有効
        if self.is_master:
            return True
        
        if self.subscription_status == 'trial':
            # trial_end_dateが設定されている場合はそれを基準に判定
            if self.trial_end_date:
                return self.trial_end_date > timezone.now()
            # trial_end_dateが設定されていない場合は30日間の無料期間を使用
            else:
                return self.is_within_trial_period()
        return self.subscription_status == 'active'
    
    def can_access_all_stores(self):
        """全店舗データにアクセス可能かチェック"""
        return self.is_master
    
    def get_accessible_stores(self):
        """アクセス可能な店舗リストを取得"""
        if self.is_master:
            # マスターアカウントは全店舗にアクセス可能
            return None  # Noneは全店舗を意味する
        else:
            # 通常アカウントは自分の店舗のみ
            return [self.rakuten_shop_id] if self.rakuten_shop_id else []
    
    def is_within_trial_period(self):
        """1ヶ月無料期間内かチェック"""
        from django.utils import timezone
        from datetime import timedelta
        
        # アカウント作成から30日以内かチェック
        trial_end = self.date_joined + timedelta(days=30)
        return timezone.now() < trial_end
    
    def get_data_retention_days(self):
        """データ保持期間を取得（プランによって異なる）"""
        if self.is_master:
            return 365  # マスターアカウントは1年保持
        elif self.is_within_trial_period():
            return 30   # 無料期間は30日
        else:
            return 365  # 有料プランは1年保持
    
    def can_execute_auto_search_today(self):
        """今日自動検索を実行可能かチェック"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.last_bulk_search_date != today
    
    def should_execute_auto_search_now(self):
        """現在時刻で自動検索を実行すべきかチェック（マスターアカウントのみ時間指定）"""
        if self.is_master and self.auto_search_time:
            from django.utils import timezone
            current_time = timezone.localtime(timezone.now()).time()
            # ±5分の範囲で実行
            user_time = self.auto_search_time
            time_diff = abs(
                (current_time.hour * 60 + current_time.minute) - 
                (user_time.hour * 60 + user_time.minute)
            )
            return time_diff <= 5
        return False
    
    def update_last_auto_search_date(self):
        """最終一括検索日を今日に更新"""
        from django.utils import timezone
        self.last_bulk_search_date = timezone.now().date()
        self.save()
    
    def get_keyword_limit(self):
        """プランに応じたキーワード登録上限を取得"""
        # マスターアカウントは無制限
        if self.is_master:
            return None
            
        # 招待ユーザーは無制限
        if self.is_invited_user:
            return None
            
        # プラン別の上限
        if self.subscription_plan == 'master':
            return 100  # マスタープラン: 100個
        else:
            return 30   # スタンダードプラン: 30個
    
    def get_plan_display_name(self):
        """プランの表示名を取得"""
        if self.is_master:
            return 'マスターアカウント'
        elif self.is_invited_user:
            return '招待アカウント（無制限）'
        else:
            plan_dict = dict(self._meta.get_field('subscription_plan').choices)
            return plan_dict.get(self.subscription_plan, 'スタンダードプラン')
    
    def get_plan_price(self):
        """プランの月額料金を取得"""
        if self.is_master or self.is_invited_user:
            return 0  # 無料
        elif self.subscription_plan == 'master':
            return 4980  # マスタープラン
        else:
            return 2980  # スタンダードプラン
    
    def can_register_keyword(self, keyword_type='seo'):
        """キーワード登録可能かチェック"""
        keyword_limit = self.get_keyword_limit()
        if keyword_limit is None:
            return True  # 無制限
        
        # 現在の登録数を取得
        if keyword_type == 'seo':
            from seo_ranking.models import Keyword
            current_count = Keyword.objects.filter(user=self).count()
        else:  # rpp
            from seo_ranking.models import RPPKeyword
            current_count = RPPKeyword.objects.filter(user=self).count()
        
        return current_count < keyword_limit