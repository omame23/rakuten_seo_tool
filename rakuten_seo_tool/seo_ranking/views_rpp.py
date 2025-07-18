"""
RPP広告順位関連のビュー
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import math
from .models import RPPKeyword, RPPResult, RPPAd, RPPSearchLog, RPPBulkSearchLog
from .forms_rpp import RPPKeywordForm, BulkRPPKeywordForm
from .rpp_scraper import scrape_rpp_ranking
import logging
import time
import csv
import io

logger = logging.getLogger(__name__)


@login_required
def rpp_keyword_list(request):
    """RPPキーワード一覧"""
    # マスターアカウントの場合は選択店舗のキーワードを表示
    if request.user.is_master:
        selected_store_id = request.session.get('selected_store_id')
        if selected_store_id:
            try:
                from accounts.models import User
                selected_user = User.objects.get(id=selected_store_id, is_invited_user=True)
                keywords = RPPKeyword.objects.filter(user=selected_user).order_by('-created_at')
                target_user = selected_user
            except User.DoesNotExist:
                # 選択店舗が見つからない場合は招待ユーザーのキーワードのみ
                from accounts.models import User
                invited_users = User.objects.filter(is_invited_user=True)
                keywords = RPPKeyword.objects.filter(user__in=invited_users).order_by('-created_at')
                target_user = None
        else:
            # 招待ユーザーのキーワードのみ
            from accounts.models import User
            invited_users = User.objects.filter(is_invited_user=True)
            keywords = RPPKeyword.objects.filter(user__in=invited_users).order_by('-created_at')
            target_user = None
    else:
        keywords = RPPKeyword.objects.filter(user=request.user).order_by('-created_at')
        target_user = request.user
    
    # 検索フィルタ
    search_query = request.GET.get('search', '')
    if search_query:
        keywords = keywords.filter(
            Q(keyword__icontains=search_query) |
            Q(rakuten_shop_id__icontains=search_query)
        )
    
    # アクティブフィルタ
    active_filter = request.GET.get('active', '')
    if active_filter == 'true':
        keywords = keywords.filter(is_active=True)
    elif active_filter == 'false':
        keywords = keywords.filter(is_active=False)
    
    # ページネーション
    paginator = Paginator(keywords, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 登録数情報を追加
    if request.user.is_master:
        if target_user:
            total_keywords = RPPKeyword.objects.filter(user=target_user).count()
        else:
            # 招待ユーザーのキーワード数のみ
            from accounts.models import User
            invited_users = User.objects.filter(is_invited_user=True)
            total_keywords = RPPKeyword.objects.filter(user__in=invited_users).count()
        keyword_limit = None  # マスターアカウントは制限なし
    else:
        total_keywords = RPPKeyword.objects.filter(user=request.user).count()
        keyword_limit = request.user.get_keyword_limit()
    
    # 一括検索実行制限チェック
    can_execute_bulk_search = RPPBulkSearchLog.can_execute_today(request.user)
    last_execution = RPPBulkSearchLog.get_today_execution(request.user)
    
    return render(request, 'seo_ranking/rpp_keyword_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'active_filter': active_filter,
        'total_keywords': total_keywords,
        'keyword_limit': keyword_limit,
        'can_execute_bulk_search': can_execute_bulk_search,
        'last_execution': last_execution,
        'target_user': target_user,
    })


@login_required
def rpp_keyword_create(request):
    """RPPキーワード作成"""
    # マスターアカウントの場合は選択店舗を取得
    selected_store = None
    target_user = request.user
    
    if request.user.is_master:
        selected_store_id = request.session.get('selected_store_id')
        if selected_store_id:
            try:
                from accounts.models import User
                selected_store = User.objects.get(id=selected_store_id, is_master=False)
                target_user = selected_store
            except User.DoesNotExist:
                messages.error(request, '店舗が選択されていません。店舗を選択してからキーワードを登録してください。')
                return redirect('seo_ranking:rpp_keyword_list')
        else:
            messages.error(request, '店舗が選択されていません。店舗を選択してからキーワードを登録してください。')
            return redirect('seo_ranking:rpp_keyword_list')
    
    # キーワード登録数チェック
    if not target_user.can_register_keyword('rpp'):
        keyword_limit = target_user.get_keyword_limit()
        store_name = selected_store.company_name if selected_store else "あなた"
        messages.error(request, f'{store_name}のRPPキーワード登録数の上限（{keyword_limit}個）に達しています。既存のキーワードを削除してから登録してください。')
        return redirect('seo_ranking:rpp_keyword_list')
    
    if request.method == 'POST':
        form = RPPKeywordForm(request.POST, user=request.user, selected_store=selected_store)
        if form.is_valid():
            # 再度チェック（並行アクセス対策）
            if not target_user.can_register_keyword('rpp'):
                keyword_limit = target_user.get_keyword_limit()
                store_name = selected_store.company_name if selected_store else "あなた"
                messages.error(request, f'{store_name}のRPPキーワード登録数の上限（{keyword_limit}個）に達しています。')
                return redirect('seo_ranking:rpp_keyword_list')
            
            keyword = form.save(commit=False)
            keyword.user = target_user
            keyword.save()
            
            store_name = selected_store.company_name if selected_store else "あなた"
            messages.success(request, f'{store_name}のRPPキーワード "{keyword.keyword}" を登録しました。')
            return redirect('seo_ranking:rpp_keyword_list')
    else:
        form = RPPKeywordForm(user=request.user, selected_store=selected_store)
    
    return render(request, 'seo_ranking/rpp_keyword_form.html', {
        'form': form,
        'selected_store': selected_store,
        'title': 'RPPキーワード登録',
        'bulk_mode': False,
    })


@login_required
def rpp_keyword_bulk_create(request):
    """RPPキーワード一括作成"""
    # マスターアカウントの場合は選択店舗を取得
    selected_store = None
    target_user = request.user
    
    if request.user.is_master:
        selected_store_id = request.session.get('selected_store_id')
        if selected_store_id:
            try:
                from accounts.models import User
                selected_store = User.objects.get(id=selected_store_id, is_master=False)
                target_user = selected_store
            except User.DoesNotExist:
                messages.error(request, '店舗が選択されていません。店舗を選択してからキーワードを登録してください。')
                return redirect('seo_ranking:rpp_keyword_list')
        else:
            messages.error(request, '店舗が選択されていません。店舗を選択してからキーワードを登録してください。')
            return redirect('seo_ranking:rpp_keyword_list')
    
    # キーワード登録数チェック（招待ユーザー以外）
    if not target_user.is_invited_user:
        current_count = RPPKeyword.objects.filter(user=target_user).count()
        if current_count >= 10:
            store_name = selected_store.company_name if selected_store else "あなた"
            messages.error(request, f'{store_name}のRPPキーワード登録数の上限（10個）に達しています。既存のキーワードを削除してから登録してください。')
            return redirect('seo_ranking:rpp_keyword_list')
    
    if request.method == 'POST':
        form = BulkRPPKeywordForm(request.POST, user=request.user, selected_store=selected_store)
        if form.is_valid():
            keywords_list = form.cleaned_data['keywords']
            rakuten_shop_id = form.cleaned_data['rakuten_shop_id']
            target_product_url = form.cleaned_data.get('target_product_url', '')
            is_active = form.cleaned_data.get('is_active', True)
            
            # 商品IDを商品URLから抽出
            target_product_id = ''
            if target_product_url:
                import re
                match = re.search(r'/([^/]+)/?$', target_product_url.rstrip('/'))
                if match:
                    target_product_id = match.group(1)
            
            # 重複チェック用に既存キーワードを取得
            existing_keywords = set(
                RPPKeyword.objects.filter(user=target_user, rakuten_shop_id=rakuten_shop_id)
                .values_list('keyword', flat=True)
            )
            
            # 一括登録処理
            created_count = 0
            skipped_count = 0
            
            # 現在の登録数を取得
            current_count = RPPKeyword.objects.filter(user=target_user).count()
            
            for keyword_text in keywords_list:
                if keyword_text in existing_keywords:
                    skipped_count += 1
                    continue
                
                # 登録数制限チェック（各店舗10個まで）- 招待ユーザー除く
                if not target_user.is_invited_user and current_count >= 10:
                    store_name = selected_store.company_name if selected_store else "あなた"
                    messages.error(request, f'{store_name}のRPPキーワード登録数の上限（10個）に達したため、"{keyword_text}" 以降の登録を中断しました。')
                    break
                
                try:
                    RPPKeyword.objects.create(
                        user=target_user,
                        keyword=keyword_text,
                        rakuten_shop_id=rakuten_shop_id,
                        target_product_url=target_product_url,
                        target_product_id=target_product_id,
                        is_active=is_active
                    )
                    created_count += 1
                    current_count += 1
                except Exception as e:
                    logger.error(f'Error creating RPP keyword "{keyword_text}": {e}')
                    skipped_count += 1
            
            # 結果メッセージ
            store_name = selected_store.company_name if selected_store else "あなた"
            if created_count > 0:
                messages.success(request, f'{store_name}に{created_count}個のRPPキーワードを登録しました。')
            if skipped_count > 0:
                messages.warning(request, f'{skipped_count}個のキーワードはスキップされました（重複または処理エラー）。')
            
            return redirect('seo_ranking:rpp_keyword_list')
    else:
        form = BulkRPPKeywordForm(user=request.user, selected_store=selected_store)
    
    return render(request, 'seo_ranking/rpp_keyword_form.html', {
        'form': form,
        'title': 'RPPキーワード一括登録',
        'bulk_mode': True,
        'selected_store': selected_store,
    })


@login_required
def rpp_keyword_edit(request, keyword_id):
    """RPPキーワード編集"""
    # マスターアカウントの場合は全店舗のキーワードにアクセス可能
    if request.user.is_master:
        keyword = get_object_or_404(RPPKeyword, id=keyword_id)
        # マスターアカウントの場合、キーワードの所有者を選択店舗として設定
        selected_store = keyword.user if not keyword.user.is_master else None
    else:
        keyword = get_object_or_404(RPPKeyword, id=keyword_id, user=request.user)
        selected_store = None
    
    if request.method == 'POST':
        form = RPPKeywordForm(request.POST, instance=keyword, user=request.user, selected_store=selected_store)
        if form.is_valid():
            form.save()
            messages.success(request, f'RPPキーワード "{keyword.keyword}" を更新しました。')
            return redirect('seo_ranking:rpp_keyword_list')
    else:
        form = RPPKeywordForm(instance=keyword, user=request.user, selected_store=selected_store)
    
    return render(request, 'seo_ranking/rpp_keyword_form.html', {
        'form': form,
        'title': 'RPPキーワード編集',
        'keyword': keyword,
        'is_edit': True,
        'selected_store': selected_store,
    })


@login_required
def rpp_keyword_delete(request, keyword_id):
    """RPPキーワード削除"""
    # マスターアカウントの場合は全店舗のキーワードにアクセス可能
    if request.user.is_master:
        keyword = get_object_or_404(RPPKeyword, id=keyword_id)
    else:
        keyword = get_object_or_404(RPPKeyword, id=keyword_id, user=request.user)
    
    if request.method == 'POST':
        keyword_name = keyword.keyword
        keyword.delete()
        messages.success(request, f'RPPキーワード "{keyword_name}" を削除しました。')
        return redirect('seo_ranking:rpp_keyword_list')
    
    return render(request, 'seo_ranking/rpp_keyword_confirm_delete.html', {
        'keyword': keyword,
    })


@login_required
@require_http_methods(["POST"])
def rpp_keyword_search(request, keyword_id):
    """RPPキーワード検索実行"""
    # マスターアカウントの場合は全店舗のキーワードにアクセス可能
    if request.user.is_master:
        keyword = get_object_or_404(RPPKeyword, id=keyword_id)
    else:
        keyword = get_object_or_404(RPPKeyword, id=keyword_id, user=request.user)
    
    # サブスクリプションチェック
    if not request.user.has_active_subscription():
        try:
            messages.error(request, '有効なサブスクリプションが必要です。')
        except Exception as msg_error:
            logger.error(f'Messages framework error: {msg_error}')
        return JsonResponse({'success': False, 'message': '有効なサブスクリプションが必要です。'})
    
    try:
        start_time = time.time()
        
        logger.info(f"RPP個別検索開始: keyword={keyword.keyword}, shop_id={keyword.rakuten_shop_id}")
        
        # RPP広告順位を検索
        result = scrape_rpp_ranking(
            keyword=keyword.keyword,
            target_shop_id=keyword.rakuten_shop_id,
            target_product_url=keyword.target_product_url,
            max_pages=3  # 3ページまで検索
        )
        
        execution_time = time.time() - start_time
        logger.info(f"RPP個別検索完了: execution_time={execution_time:.2f}s, success={result.get('success')}, total_ads={result.get('total_ads')}, is_found={result.get('is_found')}, rank={result.get('rank')}")
        
        # 【高速化】検索結果を即座に返し、DB保存は非同期で実行
        from .tasks import save_rpp_search_data_async
        
        # 非同期でデータベース保存タスクを実行
        try:
            save_rpp_search_data_async.delay(keyword.id, result, execution_time)
            logger.info(f"RPP非同期データ保存タスクを開始: keyword_id={keyword.id}")
        except Exception as async_error:
            logger.error(f"非同期タスク開始エラー: {async_error}")
            # フォールバック：同期処理（安全性確保）
            logger.warning("非同期処理に失敗、同期処理にフォールバック")
            
            # 元の同期処理を実行
            try:
                rpp_result = RPPResult.objects.create(
                    keyword=keyword,
                    rank=result.get('rank'),
                    total_ads=result.get('total_ads', 0),
                    pages_checked=3,
                    is_found=result.get('is_found', False),
                    error_message=result.get('error')
                )
                logger.info(f"フォールバック同期処理でRPPResult保存完了: {rpp_result.id}")
            except Exception as sync_error:
                logger.error(f"フォールバック同期処理もエラー: {sync_error}")
        
        if result.get('success') and result.get('is_found'):
            try:
                messages.success(request, f'RPPキーワード "{keyword.keyword}" の検索が完了しました。順位: {result["rank"]}位')
            except Exception as msg_error:
                logger.error(f'Messages framework error: {msg_error}')
            return JsonResponse({
                'success': True,
                'rank': result['rank'],
                'message': f'順位: {result["rank"]}位'
            })
        elif result.get('success'):
            try:
                messages.info(request, f'RPPキーワード "{keyword.keyword}" で広告が見つかりませんでした（圏外）。')
            except Exception as msg_error:
                logger.error(f'Messages framework error: {msg_error}')
            return JsonResponse({
                'success': True,
                'rank': None,
                'message': '圏外'
            })
        else:
            try:
                messages.error(request, f'RPP検索中にエラーが発生しました: {result.get("error", "不明なエラー")}')
            except Exception as msg_error:
                logger.error(f'Messages framework error: {msg_error}')
            return JsonResponse({'success': False, 'message': result.get('error', '検索に失敗しました')})
    
    except Exception as e:
        logger.error(f'RPP search error for keyword {keyword_id}: {e}')
        try:
            messages.error(request, 'RPP検索中にエラーが発生しました。しばらくしてから再度お試しください。')
        except Exception as msg_error:
            logger.error(f'Messages framework error: {msg_error}')
        return JsonResponse({'success': False, 'message': '検索処理でエラーが発生しました'})


@login_required
def rpp_results(request, keyword_id):
    """RPP順位結果履歴"""
    # マスターアカウントの場合は全店舗のキーワードにアクセス可能
    if request.user.is_master:
        keyword = get_object_or_404(RPPKeyword, id=keyword_id)
    else:
        keyword = get_object_or_404(RPPKeyword, id=keyword_id, user=request.user)
    
    # 順位結果を取得
    results = RPPResult.objects.filter(keyword=keyword).order_by('-checked_at')
    
    # 期間フィルタ
    period = request.GET.get('period', '365')
    if period == '7':
        start_date = timezone.now() - timedelta(days=7)
    elif period == '30':
        start_date = timezone.now() - timedelta(days=30)
    elif period == '90':
        start_date = timezone.now() - timedelta(days=90)
    elif period == '365':
        start_date = timezone.now() - timedelta(days=365)
    else:  # period == 'all'
        start_date = None
    
    if start_date:
        results = results.filter(checked_at__gte=start_date)
    
    # ページネーション
    paginator = Paginator(results, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'seo_ranking/rpp_results.html', {
        'keyword': keyword,
        'page_obj': page_obj,
        'period': period,
    })


@login_required
def rpp_detail(request, result_id):
    """RPP結果詳細"""
    # マスターアカウントの場合は全店舗の結果にアクセス可能
    if request.user.is_master:
        result = get_object_or_404(RPPResult, id=result_id)
    else:
        result = get_object_or_404(RPPResult, id=result_id, keyword__user=request.user)
    
    # 上位10広告を取得（表示速度向上のため）
    top_ads = RPPAd.objects.filter(rpp_result=result).order_by('rank')[:10]
    
    return render(request, 'seo_ranking/rpp_detail.html', {
        'result': result,
        'top_ads': top_ads,
    })


@login_required
def export_rpp_csv(request, result_id):
    """RPP結果詳細をCSVでエクスポート"""
    # マスターアカウントの場合は全店舗の結果にアクセス可能
    if request.user.is_master:
        result = get_object_or_404(RPPResult, id=result_id)
    else:
        result = get_object_or_404(RPPResult, id=result_id, keyword__user=request.user)
    
    # 上位10広告を取得（CSV出力速度向上のため）
    top_ads = RPPAd.objects.filter(rpp_result=result).order_by('rank')[:10]
    
    # CSVレスポンスを作成
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    
    # ファイル名を作成
    shop_id = result.keyword.rakuten_shop_id
    keyword = result.keyword.keyword
    from django.utils import timezone as tz
    jst_time = tz.localtime(result.checked_at)
    timestamp = jst_time.strftime("%Y%m%d_%H%M")
    filename = f'RPP_{shop_id}_{keyword}_{timestamp}.csv'
    
    # ブラウザ対応のためURLエンコード
    import urllib.parse
    encoded_filename = urllib.parse.quote(filename.encode('utf-8'))
    response['Content-Disposition'] = f'attachment; filename="RPP_{shop_id}_{timestamp}.csv"; filename*=UTF-8\'\'{encoded_filename}'
    
    # BOMを追加（Excel用）
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # ヘッダー行
    writer.writerow([
        '順位',
        '画像URL',
        '商品名',
        'キャッチコピー',
        '店舗名',
        '価格',
        'ページ番号',
        'ページ内位置',
        '商品URL',
        '自社商品'
    ])
    
    # データ行
    for ad in top_ads:
        writer.writerow([
            ad.rank,
            ad.image_url,
            ad.product_name,
            ad.catchcopy,
            ad.shop_name,
            ad.price,
            ad.page_number,
            ad.position_on_page,
            ad.product_url,
            '自社' if ad.is_own_product else '他社'
        ])
    
    return response


@login_required
def rpp_search_logs(request):
    """RPP検索ログ一覧"""
    # マスターアカウントの場合は全店舗のログを表示（マスター含む）
    if request.user.is_master:
        logs = RPPSearchLog.objects.all().order_by('-created_at')
    else:
        logs = RPPSearchLog.objects.filter(user=request.user).order_by('-created_at')
    
    # フィルタ
    success_filter = request.GET.get('success', '')
    if success_filter == 'true':
        logs = logs.filter(success=True)
    elif success_filter == 'false':
        logs = logs.filter(success=False)
    
    # 期間フィルタ
    period = request.GET.get('period', '7')
    if period == '7':
        start_date = timezone.now() - timedelta(days=7)
    elif period == '30':
        start_date = timezone.now() - timedelta(days=30)
    else:
        start_date = None
    
    if start_date:
        logs = logs.filter(created_at__gte=start_date)
    
    # ページネーション
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'seo_ranking/rpp_search_logs.html', {
        'page_obj': page_obj,
        'success_filter': success_filter,
        'period': period,
    })


@login_required
def rpp_all_data(request):
    """RPP全店舗データ（マスターアカウント限定）"""
    if not request.user.is_master:
        messages.error(request, 'この機能はマスターアカウント限定です。')
        return redirect('seo_ranking:dashboard')
    
    # 全店舗のRPPキーワードを取得
    keywords = RPPKeyword.objects.all().order_by('-created_at')
    
    # 検索フィルタ
    search_query = request.GET.get('search', '')
    if search_query:
        keywords = keywords.filter(
            Q(keyword__icontains=search_query) |
            Q(rakuten_shop_id__icontains=search_query) |
            Q(user__company_name__icontains=search_query)
        )
    
    # 店舗IDフィルタ
    shop_filter = request.GET.get('shop', '')
    if shop_filter:
        keywords = keywords.filter(rakuten_shop_id__icontains=shop_filter)
    
    # アクティブフィルタ
    active_filter = request.GET.get('active', '')
    if active_filter == 'true':
        keywords = keywords.filter(is_active=True)
    elif active_filter == 'false':
        keywords = keywords.filter(is_active=False)
    
    # 期間フィルタ
    period = request.GET.get('period', '30')
    if period == '7':
        start_date = timezone.now() - timedelta(days=7)
    elif period == '30':
        start_date = timezone.now() - timedelta(days=30)
    elif period == '90':
        start_date = timezone.now() - timedelta(days=90)
    else:  # period == 'all'
        start_date = None
    
    if start_date:
        keywords = keywords.filter(created_at__gte=start_date)
    
    # ページネーション
    paginator = Paginator(keywords, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 統計情報
    total_keywords = keywords.count()
    active_keywords = keywords.filter(is_active=True).count()
    total_shops = keywords.values('rakuten_shop_id').distinct().count()
    
    # 店舗一覧（フィルタ用）
    shop_list = RPPKeyword.objects.values_list('rakuten_shop_id', flat=True).distinct().order_by('rakuten_shop_id')
    
    return render(request, 'seo_ranking/rpp_all_data.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'shop_filter': shop_filter,
        'active_filter': active_filter,
        'period': period,
        'total_keywords': total_keywords,
        'active_keywords': active_keywords,
        'total_shops': total_shops,
        'shop_list': shop_list,
    })


@login_required
@require_http_methods(["POST"])
def update_rpp_memo(request, result_id):
    """RPP結果のメモを更新"""
    try:
        # RPP結果を取得（マスターアカウントの場合は全店舗アクセス可能）
        if request.user.is_master:
            rpp_result = get_object_or_404(RPPResult, id=result_id)
        else:
            rpp_result = get_object_or_404(
                RPPResult,
                id=result_id,
                keyword__user=request.user
            )
        
        # POSTデータからメモを取得
        memo_text = request.POST.get('memo', '').strip()
        
        # メモを更新
        rpp_result.memo = memo_text
        rpp_result.save(update_fields=['memo'])
        
        logger.info(f"RPP結果 {result_id} のメモを更新: {request.user.email}")
        
        messages.success(request, 'メモを更新しました')
        
        # リファラーチェック - 履歴ページから来た場合は履歴ページに戻る
        referer = request.META.get('HTTP_REFERER', '')
        if 'rpp/results' in referer and 'rpp/detail' not in referer:
            return redirect('seo_ranking:rpp_results', keyword_id=rpp_result.keyword.id)
        else:
            return redirect('seo_ranking:rpp_detail', result_id=result_id)
        
    except Exception as e:
        logger.error(f"RPPメモ更新エラー: {e}")
        messages.error(request, 'メモの更新に失敗しました')
        
        # エラー時もリファラーチェック
        referer = request.META.get('HTTP_REFERER', '')
        if 'rpp/results' in referer and 'rpp/detail' not in referer:
            try:
                # マスターアカウントの場合は全店舗の結果にアクセス可能
                if request.user.is_master:
                    rpp_result = RPPResult.objects.get(id=result_id)
                else:
                    rpp_result = RPPResult.objects.get(id=result_id, keyword__user=request.user)
                return redirect('seo_ranking:rpp_results', keyword_id=rpp_result.keyword.id)
            except (RPPResult.DoesNotExist, ValueError):
                pass
        return redirect('seo_ranking:rpp_detail', result_id=result_id)


@login_required
@require_http_methods(["POST"])
def rpp_bulk_search(request):
    """RPP一括検索実行"""
    import json
    
    try:
        user = request.user
        logger.info(f"RPP一括検索開始: user_id={user.id}, is_master={user.is_master}")
        
        # リクエストデータの確認
        if request.content_type == 'application/json':
            try:
                request_data = json.loads(request.body)
                logger.info(f"リクエストデータ: {request_data}")
            except json.JSONDecodeError as e:
                logger.error(f"JSONパースエラー: {e}")
                return JsonResponse({
                    'success': False,
                    'message': 'リクエストデータの形式が正しくありません'
                }, status=400)
        
        # マスターアカウントの場合は選択店舗のキーワードを取得
        target_user = user
        if user.is_master:
            selected_store_id = request.session.get('selected_store_id')
            if selected_store_id:
                try:
                    from accounts.models import User
                    target_user = User.objects.get(id=selected_store_id, is_master=False)
                except User.DoesNotExist:
                    return JsonResponse({'success': False, 'error': '店舗が選択されていません。'})
            else:
                return JsonResponse({'success': False, 'error': '店舗が選択されていません。店舗を選択してから実行してください。'})
        
        # 実行制限チェック（マスターアカウント以外）
        if not user.is_master and not RPPBulkSearchLog.can_execute_today(target_user):
            return JsonResponse({
                'success': False,
                'message': '本日は既に一括検索を実行済みです。1日1回のみ実行可能です。'
            }, status=403)
        
        # 実行対象キーワードを取得
        keywords = RPPKeyword.objects.filter(
            user=target_user,
            is_active=True
        ).order_by('keyword')
        
        if not keywords.exists():
            return JsonResponse({
                'success': False,
                'message': '実行対象のアクティブなキーワードがありません'
            })
        
        # タイムアウト対策：多量のキーワードの場合は制限
        if keywords.count() > 50:
            return JsonResponse({
                'success': False,
                'message': f'キーワード数が多いため（{keywords.count()}件）、タイムアウトを防ぐために50件以下に減らしてから実行してください。'
            })
        
        # 実行ログを作成
        bulk_log = RPPBulkSearchLog.objects.create(
            user=target_user,
            keywords_count=keywords.count()
        )
        
        store_name = target_user.company_name if user.is_master else target_user.email
        estimated_time = math.ceil((keywords.count() * 2 + 5) / 60)  # 並行処理の推定時間（分）
        logger.info(f"RPP並行一括検索開始: user {target_user.id} ({store_name}) - {keywords.count()}件 - 推定時間: {estimated_time}分")
        
        # キーワードIDのリストを作成
        keyword_ids = list(keywords.values_list('id', flat=True))
        
        # 並行処理タスクをバックグラウンドで実行
        from .tasks import execute_parallel_rpp_bulk_search
        
        # 非同期タスクを開始
        task = execute_parallel_rpp_bulk_search.delay(
            user_id=target_user.id,
            keyword_ids=keyword_ids,
            bulk_log_id=bulk_log.id
        )
        
        # 最終一括検索日を更新
        target_user.update_last_bulk_search_date()
        
        logger.info(f"RPP並行一括検索タスク開始: user {target_user.id} - タスクID: {task.id}")
        
        return JsonResponse({
            'success': True,
            'message': f'RPP一括検索をバックグラウンドで開始しました（{keywords.count()}件のキーワードを並行処理中）',
            'task_id': task.id,
            'keywords_count': keywords.count(),
            'estimated_time_minutes': estimated_time
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"RPP一括検索エラー: {e}")
        logger.error(f"エラー詳細: {error_details}")
        from django.conf import settings
        return JsonResponse({
            'success': False,
            'message': f'一括検索でエラーが発生しました: {str(e)}',
            'error_details': error_details if settings.DEBUG else None
        }, status=500)