from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です')
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
        blank=True,
        null=True,
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
        if self.subscription_status == 'trial':
            return self.trial_end_date and self.trial_end_date > timezone.now()
        return self.subscription_status == 'active'