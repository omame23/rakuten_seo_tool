"""
RPP広告順位関連のモデル
"""

from django.db import models
from django.utils import timezone
from accounts.models import User


class RPPKeyword(models.Model):
    """RPP広告キーワード管理"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='ユーザー',
        related_name='rpp_keywords'
    )
    keyword = models.CharField(
        verbose_name='検索キーワード',
        max_length=255
    )
    rakuten_shop_id = models.CharField(
        verbose_name='楽天店舗ID',
        max_length=100
    )
    target_product_url = models.URLField(
        verbose_name='対象商品URL',
        blank=True,
        null=True,
        help_text='追跡したい自社商品のURL'
    )
    target_product_id = models.CharField(
        verbose_name='対象商品ID',
        max_length=100,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        verbose_name='有効',
        default=True,
        help_text='自動実行の対象にするか'
    )
    created_at = models.DateTimeField(
        verbose_name='作成日時',
        default=timezone.now
    )
    updated_at = models.DateTimeField(
        verbose_name='更新日時',
        auto_now=True
    )

    class Meta:
        verbose_name = 'RPPキーワード'
        verbose_name_plural = 'RPPキーワード'
        unique_together = ['user', 'keyword', 'rakuten_shop_id']

    def __str__(self):
        return f"RPP: {self.keyword} ({self.user.email})"


class RPPResult(models.Model):
    """RPP広告検索結果"""
    keyword = models.ForeignKey(
        RPPKeyword,
        on_delete=models.CASCADE,
        verbose_name='キーワード',
        related_name='rpp_results'
    )
    rank = models.IntegerField(
        verbose_name='広告順位',
        null=True,
        blank=True,
        help_text='見つからない場合はNULL'
    )
    total_ads = models.IntegerField(
        verbose_name='総広告数',
        default=0,
        help_text='検索結果で見つかった広告の総数'
    )
    pages_checked = models.IntegerField(
        verbose_name='チェックページ数',
        default=1,
        help_text='何ページまでチェックしたか'
    )
    checked_at = models.DateTimeField(
        verbose_name='チェック日時',
        default=timezone.now
    )
    is_found = models.BooleanField(
        verbose_name='発見',
        default=False
    )
    error_message = models.TextField(
        verbose_name='エラーメッセージ',
        blank=True,
        null=True
    )
    memo = models.TextField(
        verbose_name='メモ',
        blank=True,
        null=True,
        help_text='CPC変更履歴、改善履歴などを記録'
    )
    
    @classmethod
    def cleanup_old_data(cls, days_to_keep=90):
        """古いデータを削除（デフォルト90日保持）"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # 関連するRPPAdも自動削除される（CASCADE）
        deleted_count = cls.objects.filter(checked_at__lt=cutoff_date).count()
        cls.objects.filter(checked_at__lt=cutoff_date).delete()
        
        return deleted_count

    class Meta:
        verbose_name = 'RPP結果'
        verbose_name_plural = 'RPP結果'
        ordering = ['-checked_at']

    def __str__(self):
        if self.is_found:
            return f"RPP {self.keyword.keyword}: {self.rank}位"
        return f"RPP {self.keyword.keyword}: 圏外"


class RPPAd(models.Model):
    """RPP広告商品情報"""
    rpp_result = models.ForeignKey(
        RPPResult,
        on_delete=models.CASCADE,
        verbose_name='RPP結果',
        related_name='rpp_ads'
    )
    rank = models.IntegerField(
        verbose_name='広告順位',
        help_text='1位, 2位, 3位...'
    )
    product_name = models.CharField(
        verbose_name='商品名',
        max_length=255
    )
    catchcopy = models.TextField(
        verbose_name='キャッチコピー',
        blank=True,
        null=True
    )
    product_url = models.URLField(
        verbose_name='商品URL'
    )
    product_id = models.CharField(
        verbose_name='商品ID',
        max_length=100,
        blank=True,
        null=True
    )
    shop_name = models.CharField(
        verbose_name='店舗名',
        max_length=255
    )
    shop_id = models.CharField(
        verbose_name='店舗ID',
        max_length=100,
        blank=True,
        null=True
    )
    price = models.IntegerField(
        verbose_name='価格',
        null=True,
        blank=True
    )
    image_url = models.URLField(
        verbose_name='商品画像URL',
        blank=True,
        null=True
    )
    bid_amount = models.IntegerField(
        verbose_name='推定入札単価',
        null=True,
        blank=True,
        help_text='円単位（推定値）'
    )
    position_on_page = models.IntegerField(
        verbose_name='ページ内位置',
        default=1,
        help_text='そのページの何番目の広告か'
    )
    page_number = models.IntegerField(
        verbose_name='ページ番号',
        default=1,
        help_text='何ページ目に表示されているか'
    )
    is_own_product = models.BooleanField(
        verbose_name='自社商品',
        default=False
    )
    collected_at = models.DateTimeField(
        verbose_name='収集日時',
        default=timezone.now
    )

    class Meta:
        verbose_name = 'RPP広告'
        verbose_name_plural = 'RPP広告'
        unique_together = ['rpp_result', 'rank']
        ordering = ['rank']

    def __str__(self):
        return f"RPP広告 {self.rank}位: {self.product_name}"


class RPPSearchLog(models.Model):
    """RPP検索ログ"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='ユーザー',
        related_name='rpp_search_logs'
    )
    keyword = models.CharField(
        verbose_name='検索キーワード',
        max_length=255
    )
    execution_time = models.FloatField(
        verbose_name='実行時間（秒）',
        default=0
    )
    pages_checked = models.IntegerField(
        verbose_name='チェックページ数',
        default=0
    )
    ads_found = models.IntegerField(
        verbose_name='発見広告数',
        default=0
    )
    success = models.BooleanField(
        verbose_name='成功',
        default=True
    )
    error_details = models.TextField(
        verbose_name='エラー詳細',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(
        verbose_name='作成日時',
        default=timezone.now
    )
    
    @classmethod
    def cleanup_old_logs(cls, days_to_keep=30):
        """古いログを削除（デフォルト30日保持）"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        deleted_count = cls.objects.filter(created_at__lt=cutoff_date).count()
        cls.objects.filter(created_at__lt=cutoff_date).delete()
        
        return deleted_count

    class Meta:
        verbose_name = 'RPP検索ログ'
        verbose_name_plural = 'RPP検索ログ'
        ordering = ['-created_at']

    def __str__(self):
        return f"RPP検索: {self.keyword} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class RPPBulkSearchLog(models.Model):
    """RPP一括検索実行ログ"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='ユーザー',
        related_name='rpp_bulk_search_logs'
    )
    executed_at = models.DateTimeField(
        verbose_name='実行日時',
        default=timezone.now
    )
    keywords_count = models.IntegerField(
        verbose_name='実行キーワード数',
        default=0
    )
    success_count = models.IntegerField(
        verbose_name='成功件数',
        default=0
    )
    error_count = models.IntegerField(
        verbose_name='エラー件数',
        default=0
    )
    total_execution_time = models.FloatField(
        verbose_name='総実行時間（秒）',
        default=0
    )
    is_completed = models.BooleanField(
        verbose_name='完了',
        default=False
    )
    
    @classmethod
    def can_execute_today(cls, user):
        """今日実行可能かチェック（マスターアカウントは制限なし）"""
        # マスターアカウントかチェック（スーパーユーザーまたはis_masterプロパティ）
        if user.is_superuser or (hasattr(user, 'is_master') and user.is_master):
            return True
        
        # 今日の実行履歴をチェック
        today = timezone.now().date()
        today_executions = cls.objects.filter(
            user=user,
            executed_at__date=today,
            is_completed=True
        ).count()
        
        return today_executions == 0
    
    @classmethod
    def get_today_execution(cls, user):
        """今日の実行履歴を取得"""
        today = timezone.now().date()
        return cls.objects.filter(
            user=user,
            executed_at__date=today
        ).first()

    class Meta:
        verbose_name = 'RPP一括検索ログ'
        verbose_name_plural = 'RPP一括検索ログ'
        ordering = ['-executed_at']

    def __str__(self):
        return f"RPP一括検索: {self.user.email} - {self.executed_at.strftime('%Y-%m-%d %H:%M')}"