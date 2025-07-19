from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
import logging
import time

from .models import Keyword, RankingResult, TopProduct, SearchLog, RPPKeyword, RPPResult, RPPAd, RPPBulkSearchLog
from .rakuten_api import RakutenSearchManager
from .rpp_scraper import scrape_rpp_ranking
from accounts.models import User

logger = logging.getLogger(__name__)


@shared_task
def auto_keyword_search():
    """
    自動キーワード検索タスク（従来のマスターアカウント用）
    毎分実行され、マスターアカウントの時間指定検索をチェック
    """
    logger.info("Starting auto keyword search task (for master accounts)")
    
    # タイムゾーンを考慮して現在時刻を取得
    from django.utils import timezone as tz
    current_datetime = tz.localtime(tz.now())
    current_time = current_datetime.time()
    current_date = current_datetime.date()
    
    logger.info(f"Current local time: {current_time}, Current date: {current_date}")
    
    # マスターアカウントで時間指定の自動検索をチェック
    users_to_search = []
    
    for user in User.objects.filter(is_master=True, is_active=True):
        # 既に今日実行済みかチェック
        if user.last_bulk_search_date == current_date:
            logger.info(f"Master user {user.email} already searched today")
            continue
            
        # マスターアカウントの時間指定チェック
        if user.should_execute_auto_search_now():
            users_to_search.append(user)
    
    logger.info(f"Found {len(users_to_search)} master users for auto search")
    
    # 各マスターユーザーの自動検索を実行
    for user in users_to_search:
        try:
            execute_user_auto_search(user.id)
        except Exception as e:
            logger.error(f"Failed auto search for master user {user.id}: {e}")
    
    logger.info("Auto keyword search task completed")


@shared_task
def nighttime_auto_search():
    """
    深夜自動検索タスク（一般ユーザー向け）
    深夜0時-7時の間に全ユーザーの自動検索を順次実行
    """
    logger.info("Starting nighttime auto search task")
    
    from django.utils import timezone as tz
    current_datetime = tz.localtime(tz.now())
    current_time = current_datetime.time()
    current_date = current_datetime.date()
    
    logger.info(f"Current local time: {current_time}, Current date: {current_date}")
    
    # 深夜0時-7時の間のみ実行
    if not (0 <= current_time.hour < 7):
        logger.info(f"Not nighttime hours (current: {current_time.hour:02d}:XX), skipping auto search")
        return
    
    # 自動検索が有効なユーザーを取得（マスターアカウント除く）
    eligible_users = []
    
    for user in User.objects.filter(is_active=True, is_master=False):
        # 既に今日実行済みかチェック
        if user.last_bulk_search_date == current_date:
            continue
            
        # SEOかRPPのどちらかが有効な場合のみ実行
        if user.auto_seo_search_enabled or user.auto_rpp_search_enabled:
            eligible_users.append(user)
    
    if not eligible_users:
        logger.info("No eligible users for nighttime auto search")
        return
    
    logger.info(f"Found {len(eligible_users)} users for nighttime auto search")
    
    # ユーザーを順次実行（負荷分散のため）
    import random
    random.shuffle(eligible_users)  # ランダム順序で実行
    
    for i, user in enumerate(eligible_users):
        try:
            logger.info(f"Executing nighttime auto search for user {user.email} ({i+1}/{len(eligible_users)})")
            
            # SEOとRPPの両方を実行
            seo_success = False
            rpp_success = False
            
            # SEO自動検索
            if user.auto_seo_search_enabled:
                try:
                    result = execute_user_auto_search(user.id)
                    seo_success = result.get('success', False) if result else False
                    logger.info(f"SEO auto search for user {user.id}: {'success' if seo_success else 'failed'}")
                except Exception as e:
                    logger.error(f"SEO auto search failed for user {user.id}: {e}")
            
            # 負荷軽減のため間隔を空ける
            time.sleep(5)
            
            # RPP自動検索
            if user.auto_rpp_search_enabled:
                try:
                    result = execute_user_auto_rpp_search(user.id)
                    rpp_success = result.get('success', False) if result else False
                    logger.info(f"RPP auto search for user {user.id}: {'success' if rpp_success else 'failed'}")
                except Exception as e:
                    logger.error(f"RPP auto search failed for user {user.id}: {e}")
            
            # どちらか一つでも成功した場合は日付を更新
            if seo_success or rpp_success:
                user.update_last_auto_search_date()
            
            # ユーザー間の間隔を空ける（負荷分散）
            if i < len(eligible_users) - 1:  # 最後のユーザーでない場合
                time.sleep(10)  # 10秒間隔
                
        except Exception as e:
            logger.error(f"Nighttime auto search failed for user {user.id}: {e}")
    
    logger.info("Nighttime auto search task completed")


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
        user.update_last_auto_search_date()
        
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
def execute_user_auto_rpp_search(user_id):
    """
    特定ユーザーのRPP自動検索を実行
    """
    try:
        user = User.objects.get(id=user_id)
        
        # サブスクリプションチェック
        if not user.has_active_subscription():
            logger.warning(f"User {user_id} does not have active subscription for RPP auto search")
            return
        
        # アクティブなRPPキーワードを取得
        from .models import RPPKeyword
        active_rpp_keywords = RPPKeyword.objects.filter(user=user, is_active=True)
        
        if not active_rpp_keywords.exists():
            logger.info(f"No active RPP keywords for user {user_id}")
            return
        
        success_count = 0
        error_count = 0
        total_count = active_rpp_keywords.count()
        
        logger.info(f"Starting RPP auto search for user {user_id}, {total_count} keywords")
        
        for i, keyword in enumerate(active_rpp_keywords):
            try:
                # 楽天API制限を考慮して間隔を空ける
                if i > 0:
                    time.sleep(2)  # RPPは2秒間隔
                
                # RPP検索実行
                result = scrape_rpp_ranking(
                    keyword=keyword.keyword,
                    target_shop_id=keyword.rakuten_shop_id,
                    target_product_url=keyword.target_product_url
                )
                
                if result['success']:
                    # 結果を保存
                    from .models import RPPResult, RPPAd
                    rpp_result = RPPResult.objects.create(
                        keyword=keyword,
                        rank=result['rank'],
                        total_ads=result['total_ads'],
                        pages_checked=3,
                        is_found=result['is_found'],
                        error_message=result['error']
                    )
                    
                    # 広告データを保存（bulk_create使用で高速化）
                    rpp_ads_to_create = []
                    for ad_data in result['ads']:
                        # 自社商品かどうかを判定
                        is_own = False
                        if keyword.rakuten_shop_id.lower() in ad_data.get('shop_name', '').lower():
                            is_own = True
                        elif keyword.target_product_url and ad_data.get('product_url'):
                            if keyword.target_product_url in ad_data['product_url']:
                                is_own = True
                        
                        rpp_ad = RPPAd(
                            rpp_result=rpp_result,
                            rank=ad_data.get('rank', 0),
                            product_name=ad_data.get('product_name', ''),
                            product_url=ad_data.get('product_url', ''),
                            product_id=ad_data.get('product_id', ''),
                            price=ad_data.get('price'),
                            shop_name=ad_data.get('shop_name', ''),
                            image_url=ad_data.get('image_url', ''),
                            catchcopy=ad_data.get('catchcopy', ''),
                            page_number=ad_data.get('page_number', 1),
                            position_on_page=ad_data.get('position_on_page', 0),
                            is_own_product=is_own
                        )
                        rpp_ads_to_create.append(rpp_ad)
                    
                    # 一括作成で高速化
                    if rpp_ads_to_create:
                        try:
                            RPPAd.objects.bulk_create(rpp_ads_to_create)
                        except Exception as bulk_error:
                            logger.error(f"RPP広告データ一括保存エラー: {bulk_error}")
                            # フォールバック：個別作成
                            for rpp_ad in rpp_ads_to_create:
                                try:
                                    rpp_ad.save()
                                except Exception:
                                    pass
                    
                    success_count += 1
                    logger.info(f"RPP auto search progress for user {user_id}: {i+1}/{total_count}")
                else:
                    # エラーの場合も結果を保存
                    from .models import RPPResult
                    RPPResult.objects.create(
                        keyword=keyword,
                        rank=None,
                        total_ads=0,
                        pages_checked=0,
                        is_found=False,
                        error_message=result['error']
                    )
                    error_count += 1
                    logger.error(f"Error in RPP auto search for keyword {keyword.keyword}: {result['error']}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error in RPP auto search for keyword {keyword.keyword}: {e}")
                continue
        
        logger.info(f"RPP auto search completed for user {user_id}. Success: {success_count}, Error: {error_count}")
        
        return {
            'success': True,
            'user_id': user_id,
            'success_count': success_count,
            'error_count': error_count,
            'total_count': total_count
        }
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for RPP auto search")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"RPP auto search failed for user {user_id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def execute_rpp_bulk_search(user_id, bulk_log_id):
    """
    RPP一括検索をバックグラウンドで実行するタスク
    """
    try:
        from accounts.models import User
        user = User.objects.get(id=user_id)
        bulk_log = RPPBulkSearchLog.objects.get(id=bulk_log_id)
        
        logger.info(f"RPP一括検索バックグラウンド開始: user {user.id} - {bulk_log.keywords_count}件")
        
        # 実行対象キーワードを取得
        keywords = RPPKeyword.objects.filter(
            user=user,
            is_active=True
        ).order_by('keyword')
        
        if not keywords.exists():
            bulk_log.is_completed = False
            bulk_log.save()
            return
        
        start_time = time.time()
        success_count = 0
        error_count = 0
        
        # 各キーワードを順次実行
        total_keywords = keywords.count()
        for i, keyword in enumerate(keywords, 1):
            try:
                logger.info(f"RPP検索実行中: {keyword.keyword} ({keyword.rakuten_shop_id}) - {i}/{total_keywords}")
                
                # 長時間実行の場合は間隔を空ける
                if i > 1 and total_keywords > 20:
                    time.sleep(3)  # 3秒間隔
                elif i > 1 and total_keywords > 10:
                    time.sleep(2)  # 2秒間隔
                elif i > 1:
                    time.sleep(1)  # 1秒間隔
                
                # RPP順位検索を実行
                result = scrape_rpp_ranking(
                    keyword=keyword.keyword,
                    target_shop_id=keyword.rakuten_shop_id,
                    target_product_url=keyword.target_product_url
                )
                
                if result['success']:
                    # 結果を保存
                    rpp_result = RPPResult.objects.create(
                        keyword=keyword,
                        rank=result['rank'],
                        total_ads=result['total_ads'],
                        pages_checked=3,
                        is_found=result['is_found'],
                        error_message=result['error']
                    )
                    
                    # 広告データを保存（bulk_create使用で高速化）
                    rpp_ads_to_create = []
                    for ad_data in result['ads']:
                        rpp_ad = RPPAd(
                            rpp_result=rpp_result,
                            rank=ad_data.get('rank', 0),
                            product_name=ad_data.get('product_name', ''),
                            product_url=ad_data.get('product_url', ''),
                            product_id=ad_data.get('product_id', ''),
                            price=ad_data.get('price'),
                            shop_name=ad_data.get('shop_name', ''),
                            image_url=ad_data.get('image_url', ''),
                            catchcopy=ad_data.get('catchcopy', ''),
                            page_number=ad_data.get('page_number', 1),
                            position_on_page=ad_data.get('position_on_page', 0)
                        )
                        rpp_ads_to_create.append(rpp_ad)
                    
                    # 一括作成で高速化
                    if rpp_ads_to_create:
                        try:
                            RPPAd.objects.bulk_create(rpp_ads_to_create)
                        except Exception as bulk_error:
                            logger.error(f"RPP広告データ一括保存エラー: {bulk_error}")
                            # フォールバック：個別作成
                            for rpp_ad in rpp_ads_to_create:
                                try:
                                    rpp_ad.save()
                                except Exception:
                                    pass
                    
                    success_count += 1
                    logger.info(f"RPP検索成功: {keyword.keyword} - 順位: {result['rank']}")
                else:
                    # エラーの場合も結果を保存
                    RPPResult.objects.create(
                        keyword=keyword,
                        rank=None,
                        total_ads=0,
                        pages_checked=0,
                        is_found=False,
                        error_message=result['error']
                    )
                    error_count += 1
                    logger.error(f"RPP検索失敗: {keyword.keyword} - エラー: {result['error']}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"RPP検索エラー: {keyword.keyword} - {str(e)}")
                
                # エラーの場合も結果を保存
                try:
                    RPPResult.objects.create(
                        keyword=keyword,
                        rank=None,
                        total_ads=0,
                        pages_checked=0,
                        is_found=False,
                        error_message=str(e)
                    )
                except Exception as save_error:
                    logger.error(f"結果保存エラー: {save_error}")
        
        # 実行ログを更新
        execution_time = time.time() - start_time
        bulk_log.is_completed = True
        bulk_log.success_count = success_count
        bulk_log.error_count = error_count
        bulk_log.total_execution_time = execution_time
        bulk_log.save()
        
        logger.info(f"RPP一括検索完了: user {user.id} - 成功: {success_count}, エラー: {error_count}, 実行時間: {execution_time:.2f}秒")
        
    except Exception as e:
        logger.error(f"RPP一括検索タスクエラー: {str(e)}")
        try:
            bulk_log = RPPBulkSearchLog.objects.get(id=bulk_log_id)
            bulk_log.is_completed = False
            bulk_log.save()
        except:
            pass


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


@shared_task
def save_rpp_search_data_async(keyword_id, search_result, execution_time):
    """
    RPP個別検索のデータベース保存を非同期で実行
    ユーザーには即座に検索結果を返し、DB保存は背景で実行
    """
    try:
        from .models import RPPKeyword, RPPResult, RPPAd, RPPSearchLog
        
        # キーワード取得
        try:
            keyword = RPPKeyword.objects.get(id=keyword_id)
        except RPPKeyword.DoesNotExist:
            logger.error(f"RPPキーワードが見つかりません: ID {keyword_id}")
            return {'success': False, 'error': 'Keyword not found'}
        
        logger.info(f"RPP非同期データ保存開始: keyword={keyword.keyword}, execution_time={execution_time:.2f}s")
        
        # 結果を保存
        rpp_result = RPPResult.objects.create(
            keyword=keyword,
            rank=search_result.get('rank'),
            total_ads=search_result.get('total_ads', 0),
            pages_checked=3,
            is_found=search_result.get('is_found', False),
            error_message=search_result.get('error')
        )
        
        # 広告情報を保存（bulk_create使用で高速化）
        ads = search_result.get('ads', [])
        logger.info(f"RPP広告データ非同期保存: {len(ads)}件")
        
        # RPPAdオブジェクトをリストで準備
        rpp_ads_to_create = []
        for i, ad in enumerate(ads[:20], 1):  # 上位20広告まで保存
            try:
                # 自社商品かどうかを判定
                is_own = False
                if keyword.rakuten_shop_id.lower() in ad.get('shop_name', '').lower():
                    is_own = True
                elif keyword.target_product_url and ad.get('product_url'):
                    if keyword.target_product_url in ad['product_url']:
                        is_own = True
                
                rpp_ad = RPPAd(
                    rpp_result=rpp_result,
                    rank=ad.get('rank', i),
                    product_name=ad.get('product_name', ''),
                    catchcopy=ad.get('catchcopy', ''),
                    product_url=ad.get('product_url', ''),
                    product_id=ad.get('product_id', ''),
                    shop_name=ad.get('shop_name', ''),
                    price=ad.get('price'),
                    image_url=ad.get('image_url', ''),
                    position_on_page=ad.get('position_on_page', 1),
                    page_number=ad.get('page_number', 1),
                    is_own_product=is_own
                )
                rpp_ads_to_create.append(rpp_ad)
            except Exception as ad_error:
                logger.error(f"広告データ準備エラー: {ad_error}, ad_data: {ad}")
        
        # 一括作成で高速化
        if rpp_ads_to_create:
            try:
                RPPAd.objects.bulk_create(rpp_ads_to_create)
                logger.info(f"RPP広告データ非同期保存完了: {len(rpp_ads_to_create)}件")
            except Exception as bulk_error:
                logger.error(f"RPP広告データ一括保存エラー: {bulk_error}")
                # フォールバック：個別作成
                for rpp_ad in rpp_ads_to_create:
                    try:
                        rpp_ad.save()
                    except Exception as individual_error:
                        logger.error(f"RPP広告データ個別保存エラー: {individual_error}")
        
        # 検索ログを保存
        try:
            RPPSearchLog.objects.create(
                user=keyword.user,
                keyword=keyword.keyword,
                execution_time=execution_time,
                pages_checked=3,
                ads_found=len(ads),
                success=search_result.get('success', False),
                error_details=search_result.get('error')
            )
        except Exception as log_error:
            logger.error(f"検索ログ保存エラー: {log_error}")
        
        logger.info(f"RPP非同期データ保存完了: keyword={keyword.keyword}, rpp_result_id={rpp_result.id}")
        
        return {
            'success': True,
            'rpp_result_id': rpp_result.id,
            'ads_saved': len(rpp_ads_to_create)
        }
        
    except Exception as e:
        logger.error(f"RPP非同期データ保存エラー: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def execute_single_rpp_search(keyword_id):
    """
    単一キーワードのRPP検索を実行する並行処理用タスク
    """
    try:
        from .models import RPPKeyword, RPPResult, RPPAd
        
        # キーワード取得
        try:
            keyword = RPPKeyword.objects.get(id=keyword_id)
        except RPPKeyword.DoesNotExist:
            logger.error(f"RPPキーワードが見つかりません: ID {keyword_id}")
            return {'success': False, 'error': 'Keyword not found', 'keyword_id': keyword_id}
        
        logger.info(f"RPP並行検索開始: {keyword.keyword} ({keyword.rakuten_shop_id})")
        
        start_time = time.time()
        
        # RPP順位検索を実行
        result = scrape_rpp_ranking(
            keyword=keyword.keyword,
            target_shop_id=keyword.rakuten_shop_id,
            target_product_url=keyword.target_product_url
        )
        
        execution_time = time.time() - start_time
        
        if result['success']:
            # 結果を保存
            rpp_result = RPPResult.objects.create(
                keyword=keyword,
                rank=result['rank'],
                total_ads=result['total_ads'],
                pages_checked=3,
                is_found=result['is_found'],
                error_message=result['error']
            )
            
            # 広告データを保存（bulk_create使用で高速化）
            rpp_ads_to_create = []
            for ad_data in result['ads']:
                # 自社商品かどうかを判定
                is_own = False
                if keyword.rakuten_shop_id.lower() in ad_data.get('shop_name', '').lower():
                    is_own = True
                elif keyword.target_product_url and ad_data.get('product_url'):
                    if keyword.target_product_url in ad_data['product_url']:
                        is_own = True
                
                rpp_ad = RPPAd(
                    rpp_result=rpp_result,
                    rank=ad_data.get('rank', 0),
                    product_name=ad_data.get('product_name', ''),
                    product_url=ad_data.get('product_url', ''),
                    product_id=ad_data.get('product_id', ''),
                    price=ad_data.get('price'),
                    shop_name=ad_data.get('shop_name', ''),
                    image_url=ad_data.get('image_url', ''),
                    catchcopy=ad_data.get('catchcopy', ''),
                    page_number=ad_data.get('page_number', 1),
                    position_on_page=ad_data.get('position_on_page', 0),
                    is_own_product=is_own
                )
                rpp_ads_to_create.append(rpp_ad)
            
            # 一括作成で高速化
            if rpp_ads_to_create:
                try:
                    RPPAd.objects.bulk_create(rpp_ads_to_create)
                except Exception as bulk_error:
                    logger.error(f"RPP広告データ一括保存エラー: {bulk_error}")
                    # フォールバック：個別作成
                    for rpp_ad in rpp_ads_to_create:
                        try:
                            rpp_ad.save()
                        except Exception:
                            pass
            
            logger.info(f"RPP並行検索成功: {keyword.keyword} - 順位: {result['rank']} - 実行時間: {execution_time:.2f}秒")
            
            return {
                'success': True,
                'keyword_id': keyword_id,
                'keyword': keyword.keyword,
                'rank': result['rank'],
                'is_found': result['is_found'],
                'total_ads': result['total_ads'],
                'execution_time': execution_time,
                'rpp_result_id': rpp_result.id
            }
        else:
            # エラーの場合も結果を保存
            RPPResult.objects.create(
                keyword=keyword,
                rank=None,
                total_ads=0,
                pages_checked=0,
                is_found=False,
                error_message=result['error']
            )
            
            logger.error(f"RPP並行検索失敗: {keyword.keyword} - エラー: {result['error']}")
            
            return {
                'success': False,
                'keyword_id': keyword_id,
                'keyword': keyword.keyword,
                'error': result['error'],
                'execution_time': execution_time
            }
        
    except Exception as e:
        logger.error(f"RPP並行検索タスクエラー: {str(e)}")
        return {
            'success': False,
            'keyword_id': keyword_id,
            'error': str(e),
            'execution_time': 0
        }


@shared_task
def execute_parallel_rpp_bulk_search(user_id, keyword_ids, bulk_log_id):
    """
    複数キーワードを並行処理でRPP検索する管理タスク
    """
    try:
        from celery import group
        from accounts.models import User
        from .models import RPPBulkSearchLog
        
        user = User.objects.get(id=user_id)
        bulk_log = RPPBulkSearchLog.objects.get(id=bulk_log_id)
        
        logger.info(f"RPP並行一括検索開始: user {user.id} - {len(keyword_ids)}件")
        
        start_time = time.time()
        
        # グループタスクで並行実行
        job = group(execute_single_rpp_search.s(keyword_id) for keyword_id in keyword_ids)
        result = job.apply_async()
        
        # 全タスクの完了を待機
        results = result.get()
        
        # 結果を集計
        success_count = sum(1 for r in results if r['success'])
        error_count = len(results) - success_count
        total_execution_time = time.time() - start_time
        
        # 実行ログを更新
        bulk_log.is_completed = True
        bulk_log.success_count = success_count
        bulk_log.error_count = error_count
        bulk_log.total_execution_time = total_execution_time
        bulk_log.save()
        
        logger.info(f"RPP並行一括検索完了: user {user.id} - 成功: {success_count}, エラー: {error_count}, 実行時間: {total_execution_time:.2f}秒")
        
        return {
            'success': True,
            'success_count': success_count,
            'error_count': error_count,
            'total_execution_time': total_execution_time,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"RPP並行一括検索エラー: {str(e)}")
        try:
            bulk_log = RPPBulkSearchLog.objects.get(id=bulk_log_id)
            bulk_log.is_completed = False
            bulk_log.save()
        except:
            pass
        return {'success': False, 'error': str(e)}