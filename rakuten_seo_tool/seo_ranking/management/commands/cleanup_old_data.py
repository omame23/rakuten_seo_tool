from django.core.management.base import BaseCommand
from django.utils import timezone
from seo_ranking.models import RankingResult, SearchLog
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '古いデータを削除してデータベースサイズを管理'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ranking-days',
            type=int,
            default=90,
            help='順位データの保持日数（デフォルト: 90日）'
        )
        parser.add_argument(
            '--log-days',
            type=int,
            default=30,
            help='検索ログの保持日数（デフォルト: 30日）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際に削除せず、削除対象のみ表示'
        )

    def handle(self, *args, **options):
        ranking_days = options['ranking_days']
        log_days = options['log_days']
        dry_run = options['dry_run']

        self.stdout.write(f"データクリーンアップ開始: {timezone.now()}")
        self.stdout.write(f"順位データ保持期間: {ranking_days}日")
        self.stdout.write(f"ログ保持期間: {log_days}日")
        
        if dry_run:
            self.stdout.write("--- DRY RUN モード ---")

        # 順位データのクリーンアップ
        if dry_run:
            from datetime import timedelta
            cutoff_date = timezone.now() - timedelta(days=ranking_days)
            ranking_count = RankingResult.objects.filter(checked_at__lt=cutoff_date).count()
            self.stdout.write(f"削除対象の順位データ: {ranking_count}件")
        else:
            ranking_deleted = RankingResult.cleanup_old_data(ranking_days)
            self.stdout.write(
                self.style.SUCCESS(f"順位データを削除: {ranking_deleted}件")
            )

        # ログデータのクリーンアップ
        if dry_run:
            from datetime import timedelta
            cutoff_date = timezone.now() - timedelta(days=log_days)
            log_count = SearchLog.objects.filter(created_at__lt=cutoff_date).count()
            self.stdout.write(f"削除対象のログデータ: {log_count}件")
        else:
            log_deleted = SearchLog.cleanup_old_logs(log_days)
            self.stdout.write(
                self.style.SUCCESS(f"ログデータを削除: {log_deleted}件")
            )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS("データクリーンアップ完了")
            )
            logger.info(f"Data cleanup completed - Rankings: {ranking_deleted}, Logs: {log_deleted}")