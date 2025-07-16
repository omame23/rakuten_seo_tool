from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.contrib import messages
from .models import User
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """新規ユーザー作成時の処理"""
    if created:
        # ログに記録
        logger.info(f"新規ユーザーが作成されました: {instance.email}")
        
        # 必要に応じて追加の初期化処理
        # - ユーザープロファイルの作成
        # - 初期データの設定
        # - 通知の送信など


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """ユーザーログイン時の処理"""
    # サブスクリプション状態をチェック
    if not user.has_active_subscription():
        if user.subscription_status == 'trial':
            messages.info(
                request,
                f'無料トライアル期間中です。{user.trial_end_date.strftime("%Y年%m月%d日")}まで全機能をご利用いただけます。'
            )
        else:
            messages.warning(
                request,
                'サブスクリプションが無効です。全機能を利用するには有効なサブスクリプションが必要です。'
            )
    else:
        messages.success(request, f'おかえりなさい、{user.contact_name}様！')