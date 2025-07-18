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
    auto_search_enabled = models.BooleanField(
        verbose_name='自動検索有効',
        default=True,
        help_text='毎日自動でキーワード順位を確認する'
    )
    auto_search_time = models.TimeField(
        verbose_name='自動検索時間',
        default='10:00',
        help_text='毎日自動検索を実行する時間（24時間形式）'
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
            return self.trial_end_date and self.trial_end_date > timezone.now()
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
    
    def can_execute_bulk_search_today(self):
        """今日一括検索を実行可能かチェック"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.last_bulk_search_date != today
    
    def update_last_bulk_search_date(self):
        """最終一括検索日を今日に更新"""
        from django.utils import timezone
        self.last_bulk_search_date = timezone.now().date()
        self.save()