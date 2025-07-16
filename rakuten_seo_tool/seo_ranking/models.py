from django.db import models
from django.utils import timezone
from accounts.models import User


class Keyword(models.Model):
    """SEO検索キーワード管理"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='ユーザー',
        related_name='keywords'
    )
    keyword = models.CharField(
        verbose_name='キーワード',
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
        help_text='順位を追跡したい自社商品のURL'
    )
    target_product_id = models.CharField(
        verbose_name='対象商品ID',
        max_length=100,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        verbose_name='有効',
        default=True
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
        verbose_name = 'キーワード'
        verbose_name_plural = 'キーワード'
        unique_together = ['user', 'keyword', 'rakuten_shop_id']

    def __str__(self):
        return f"{self.keyword} ({self.user.email})"


class RankingResult(models.Model):
    """検索順位結果"""
    keyword = models.ForeignKey(
        Keyword,
        on_delete=models.CASCADE,
        verbose_name='キーワード',
        related_name='ranking_results'
    )
    rank = models.IntegerField(
        verbose_name='順位',
        null=True,
        blank=True,
        help_text='見つからない場合はNULL'
    )
    total_results = models.IntegerField(
        verbose_name='総検索結果数',
        default=0
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
        help_text='分析結果や気づいたことを記録'
    )
    total_products = models.IntegerField(
        verbose_name='総商品数',
        null=True,
        blank=True,
        help_text='検索結果の総商品数'
    )
    found_product_url = models.URLField(
        verbose_name='発見商品URL',
        blank=True,
        null=True,
        help_text='見つかった商品のURL'
    )
    ai_analysis = models.TextField(
        verbose_name='AI分析結果',
        blank=True,
        null=True,
        help_text='AIによる競合分析結果'
    )
    
    @classmethod
    def cleanup_old_data(cls, days_to_keep=90):
        """古いデータを削除（デフォルト90日保持）"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # 関連するTopProductも自動削除される（CASCADE）
        deleted_count = cls.objects.filter(checked_at__lt=cutoff_date).count()
        cls.objects.filter(checked_at__lt=cutoff_date).delete()
        
        return deleted_count

    class Meta:
        verbose_name = '順位結果'
        verbose_name_plural = '順位結果'
        ordering = ['-checked_at']

    def __str__(self):
        if self.is_found:
            return f"{self.keyword.keyword}: {self.rank}位"
        return f"{self.keyword.keyword}: 圏外"


class TopProduct(models.Model):
    """上位商品情報"""
    ranking_result = models.ForeignKey(
        RankingResult,
        on_delete=models.CASCADE,
        verbose_name='順位結果',
        related_name='top_products'
    )
    rank = models.IntegerField(
        verbose_name='順位'
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
    review_count = models.IntegerField(
        verbose_name='レビュー数',
        default=0
    )
    review_average = models.DecimalField(
        verbose_name='レビュー平均',
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True
    )
    image_url = models.URLField(
        verbose_name='商品画像URL',
        blank=True,
        null=True
    )
    point_rate = models.IntegerField(
        verbose_name='ポイント倍率',
        default=1,
        null=True,
        blank=True
    )
    genre_id = models.CharField(
        verbose_name='ジャンルID',
        max_length=50,
        blank=True,
        null=True
    )
    genre_name = models.CharField(
        verbose_name='ジャンル名',
        max_length=255,
        blank=True,
        null=True
    )
    tag_ids = models.TextField(
        verbose_name='タグID（JSON形式）',
        blank=True,
        null=True,
        help_text='複数のタグIDをJSON配列で保存'
    )
    tag_names = models.TextField(
        verbose_name='タグ名（JSON形式）',
        blank=True,
        null=True,
        help_text='複数のタグ名をJSON配列で保存'
    )
    product_spec = models.TextField(
        verbose_name='製品情報・商品仕様',
        blank=True,
        null=True
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
        verbose_name = '上位商品'
        verbose_name_plural = '上位商品'
        unique_together = ['ranking_result', 'rank']
        ordering = ['rank']

    def __str__(self):
        return f"{self.rank}位: {self.product_name}"
    
    def get_large_image_url(self, size="original"):
        """画像URLのサイズパラメータを調整して大きな画像を取得"""
        if not self.image_url:
            return self.image_url
        
        import re
        
        # ?_ex=128x128のようなサイズパラメータを削除
        processed_url = re.sub(r'\?_ex=\d+x\d+', '', self.image_url)
        
        # &_ex=128x128のようなサイズパラメータも削除
        processed_url = re.sub(r'&_ex=\d+x\d+', '', processed_url)
        
        # 新しいサイズパラメータを追加（オプション）
        if size and size != "original":
            if '?' in processed_url:
                processed_url += f'&_ex={size}'
            else:
                processed_url += f'?_ex={size}'
        
        return processed_url
    
    def get_keyword_frequency(self, keyword: str) -> dict:
        """検索キーワードの露出頻度を計算（個別キーワード別）"""
        import re
        
        # キーワードを単語に分割（空白区切りを基本とし、さらに文字種で分割）
        # まず空白で分割
        space_split_words = keyword.split()
        keyword_words = []
        
        for word in space_split_words:
            word_lower = word.lower()
            # 各単語をさらに文字種で分割（ひらがな、カタカナ、漢字、英数字）
            sub_words = re.findall(r'[ぁ-ん]+|[ァ-ヶー]+|[一-龠々]+|[a-zA-Z0-9]+', word_lower)
            keyword_words.extend(sub_words)
        
        # デバッグ用：キーワード分割結果をログ出力
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Keyword split result: '{keyword}' -> {keyword_words}")
        
        # 対象テキストを準備
        product_name_text = (self.product_name or '').lower()
        catchcopy_text = (self.catchcopy or '').lower()
        product_spec_text = (self.product_spec or '').lower()
        
        # 各キーワードの詳細カウント
        keyword_details = {}
        total_name_count = 0
        total_catchcopy_count = 0
        total_spec_count = 0
        
        for word in keyword_words:
            # 漢字・ひらがな・カタカナは1文字でも有効、英数字は2文字以上
            is_japanese = bool(re.match(r'^[ぁ-んァ-ヶ一-龠々]+$', word))
            is_english = bool(re.match(r'^[a-zA-Z0-9]+$', word))
            
            if (is_japanese and len(word) >= 1) or (is_english and len(word) >= 2):
                name_count = len(re.findall(re.escape(word), product_name_text))
                catchcopy_count = len(re.findall(re.escape(word), catchcopy_text))
                spec_count = len(re.findall(re.escape(word), product_spec_text))
                
                word_total = name_count + catchcopy_count + spec_count
                
                if word_total > 0:  # 1回以上出現したキーワードのみ記録
                    keyword_details[word] = {
                        'name_count': name_count,
                        'catchcopy_count': catchcopy_count,
                        'spec_count': spec_count,
                        'total': word_total
                    }
                
                total_name_count += name_count
                total_catchcopy_count += catchcopy_count
                total_spec_count += spec_count
        
        total_count = total_name_count + total_catchcopy_count + total_spec_count
        
        return {
            'name_count': total_name_count,
            'catchcopy_count': total_catchcopy_count,
            'spec_count': total_spec_count,
            'total_count': total_count,
            'keywords_used': keyword_words,
            'keyword_details': keyword_details  # 個別キーワード詳細を追加
        }


class SearchLog(models.Model):
    """検索ログ"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='ユーザー',
        related_name='search_logs'
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
    products_found = models.IntegerField(
        verbose_name='発見商品数',
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
        verbose_name = '検索ログ'
        verbose_name_plural = '検索ログ'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.keyword} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


# RPP関連モデルをインポート
from .models_rpp import RPPKeyword, RPPResult, RPPAd, RPPSearchLog, RPPBulkSearchLog
