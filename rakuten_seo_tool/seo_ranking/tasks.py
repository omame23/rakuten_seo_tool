from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
import logging
import time

from .models import Keyword, RankingResult, TopProduct, SearchLog
from .rakuten_api import RakutenSearchManager
from accounts.models import User

logger = logging.getLogger(__name__)


@shared_task
def auto_keyword_search():
    """
    自動キーワード検索タスク
    毎日指定時間に実行される
    """
    logger.info("Starting auto keyword search task")
    
    # タイムゾーンを考慮して現在時刻を取得
    from django.utils import timezone as tz
    current_datetime = tz.localtime(tz.now())
    current_time = current_datetime.time()
    current_date = current_datetime.date()
    
    logger.info(f"Current local time: {current_time}, Current date: {current_date}")
    
    # 自動検索が有効で、設定時間に近いユーザーを取得（±5分の範囲）
    users_to_search = []
    
    for user in User.objects.filter(auto_search_enabled=True, is_active=True):
        # 既に今日実行済みかチェック
        if user.last_bulk_search_date == current_date:
            logger.info(f"User {user.email} already searched today")
            continue
            
        # 時間チェック（±5分の範囲）
        user_time = user.auto_search_time
        time_diff = abs(
            (current_time.hour * 60 + current_time.minute) - 
            (user_time.hour * 60 + user_time.minute)
        )
        
        logger.info(f"User {user.email}: auto_search_time={user_time}, time_diff={time_diff}")
        
        if time_diff <= 5:  # 5分以内
            users_to_search.append(user)
    
    logger.info(f"Found {len(users_to_search)} users for auto search")
    
    # 各ユーザーの自動検索を実行
    for user in users_to_search:
        try:
            execute_user_auto_search(user.id)
        except Exception as e:
            logger.error(f"Failed auto search for user {user.id}: {e}")
    
    logger.info("Auto keyword search task completed")


@shared_task
def execute_user_auto_search(user_id):
    """
    特定ユーザーの自動検索を実行
    """
    try:
        user = User.objects.get(id=user_id)
        
        # サブスクリプションチェック
        if not user.has_active_subscription():
            logger.warning(f"User {user_id} does not have active subscription")
            return
        
        # アクティブなキーワードを取得
        active_keywords = Keyword.objects.filter(user=user, is_active=True)
        
        if not active_keywords.exists():
            logger.info(f"No active keywords for user {user_id}")
            return
        
        # 検索マネージャーを初期化
        search_manager = RakutenSearchManager(user)
        
        success_count = 0
        error_count = 0
        total_count = active_keywords.count()
        
        logger.info(f"Starting auto search for user {user_id}, {total_count} keywords")
        
        for i, keyword in enumerate(active_keywords):
            try:
                # 楽天API制限を考慮して間隔を空ける
                if i > 0:
                    time.sleep(1)  # 1秒間隔
                
                # 検索実行
                ranking_result = search_manager.execute_keyword_search(keyword)
                success_count += 1
                
                logger.info(f"Auto search progress for user {user_id}: {i+1}/{total_count}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error in auto search for keyword {keyword.keyword}: {e}")
                continue
        
        # 最終一括検索日を更新
        user.update_last_bulk_search_date()
        
        logger.info(f"Auto search completed for user {user_id}. Success: {success_count}, Error: {error_count}")
        
        return {
            'success': True,
            'user_id': user_id,
            'success_count': success_count,
            'error_count': error_count,
            'total_count': total_count
        }
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Auto search failed for user {user_id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_old_data_task():
    """
    古いデータを定期的にクリーンアップするタスク
    ユーザーのプランに応じて保持期間を調整
    """
    logger.info("Starting scheduled data cleanup task")
    
    total_ranking_deleted = 0
    total_log_deleted = 0
    
    # ユーザーごとに異なる保持期間でクリーンアップ
    for user in User.objects.all():
        retention_days = user.get_data_retention_days()
        
        # そのユーザーの古い順位データを削除
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        user_ranking_results = RankingResult.objects.filter(
            keyword__user=user,
            checked_at__lt=cutoff_date
        )
        
        user_ranking_count = user_ranking_results.count()
        if user_ranking_count > 0:
            user_ranking_results.delete()
            total_ranking_deleted += user_ranking_count
            logger.info(f"Deleted {user_ranking_count} ranking results for user {user.email} (retention: {retention_days} days)")
    
    # 検索ログは全ユーザー共通で30日保持
    log_deleted = SearchLog.cleanup_old_logs(30)
    total_log_deleted += log_deleted
    
    logger.info(f"Data cleanup completed - Rankings: {total_ranking_deleted}, Logs: {total_log_deleted}")
    
    return {
        'ranking_deleted': total_ranking_deleted,
        'log_deleted': total_log_deleted,
        'cleanup_date': timezone.now().isoformat()
    }


@shared_task
def weekly_data_summary():
    """
    週次でデータ使用量のサマリーを生成
    """
    from django.db.models import Count
    
    # 各ユーザーのデータ使用量を集計
    users_summary = []
    
    for user in User.objects.all():
        ranking_count = RankingResult.objects.filter(keyword__user=user).count()
        log_count = SearchLog.objects.filter(user=user).count()
        keyword_count = user.keywords.count()
        
        users_summary.append({
            'user_email': user.email,
            'user_type': 'master' if user.is_master else 'regular',
            'keywords': keyword_count,
            'ranking_results': ranking_count,
            'search_logs': log_count,
            'retention_days': user.get_data_retention_days()
        })
    
    logger.info(f"Weekly data summary generated for {len(users_summary)} users")
    
    return {
        'summary_date': timezone.now().isoformat(),
        'users_summary': users_summary
    }