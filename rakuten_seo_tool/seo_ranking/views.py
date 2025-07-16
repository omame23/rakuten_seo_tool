from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Keyword, RankingResult, TopProduct, SearchLog
from .rakuten_api import RakutenSearchManager
from .forms import KeywordForm, BulkKeywordForm
from .ai_analysis import get_ai_analysis
import logging
import time
import csv
import io

logger = logging.getLogger(__name__)


@login_required
def keyword_list(request):
    """キーワード一覧"""
    # マスターアカウントの場合は選択店舗のキーワードを表示
    if request.user.is_master:
        selected_store_id = request.session.get('selected_store_id')
        if selected_store_id:
            try:
                from accounts.models import User
                selected_user = User.objects.get(id=selected_store_id, is_master=False)
                keywords = Keyword.objects.filter(user=selected_user).order_by('-created_at')
                target_user = selected_user
            except User.DoesNotExist:
                # 選択店舗が見つからない場合は全店舗のキーワード（マスター含む）
                keywords = Keyword.objects.all().order_by('-created_at')
                target_user = None
        else:
            # 全店舗のキーワード（マスター含む）
            keywords = Keyword.objects.all().order_by('-created_at')
            target_user = None
    else:
        keywords = Keyword.objects.filter(user=request.user).order_by('-created_at')
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
            total_keywords = Keyword.objects.filter(user=target_user).count()
        else:
            total_keywords = Keyword.objects.all().count()
        keyword_limit = None  # マスターアカウントは制限なし
    else:
        total_keywords = Keyword.objects.filter(user=request.user).count()
        keyword_limit = 10
    
    return render(request, 'seo_ranking/keyword_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'active_filter': active_filter,
        'total_keywords': total_keywords,
        'keyword_limit': keyword_limit,
        'target_user': target_user,
    })


@login_required
def keyword_create(request):
    """キーワード作成"""
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
                return redirect('seo_ranking:keyword_list')
        else:
            messages.error(request, '店舗が選択されていません。店舗を選択してからキーワードを登録してください。')
            return redirect('seo_ranking:keyword_list')
    
    # キーワード登録数チェック
    if not request.user.is_master:
        current_count = Keyword.objects.filter(user=target_user).count()
        if current_count >= 10:
            messages.error(request, 'キーワード登録数の上限（10個）に達しています。既存のキーワードを削除してから登録してください。')
            return redirect('seo_ranking:keyword_list')
    elif request.user.is_master and selected_store:
        # マスターアカウントが選択店舗にキーワードを登録する場合も制限チェック
        current_count = Keyword.objects.filter(user=selected_store).count()
        if current_count >= 10:
            messages.error(request, f'店舗「{selected_store.company_name}」のキーワード登録数の上限（10個）に達しています。')
            return redirect('seo_ranking:keyword_list')
    
    if request.method == 'POST':
        form = KeywordForm(request.POST, user=request.user, selected_store=selected_store)
        if form.is_valid():
            # 再度チェック（並行アクセス対策）
            current_count = Keyword.objects.filter(user=target_user).count()
            if current_count >= 10:
                store_name = selected_store.company_name if selected_store else "あなた"
                messages.error(request, f'{store_name}のキーワード登録数の上限（10個）に達しています。')
                return redirect('seo_ranking:keyword_list')
            
            keyword = form.save(commit=False)
            keyword.user = target_user
            keyword.save()
            
            store_name = selected_store.company_name if selected_store else "あなた"
            messages.success(request, f'{store_name}のキーワード "{keyword.keyword}" を登録しました。')
            return redirect('seo_ranking:keyword_list')
    else:
        form = KeywordForm(user=request.user, selected_store=selected_store)
    
    return render(request, 'seo_ranking/keyword_form.html', {
        'form': form,
        'selected_store': selected_store,
        'title': 'キーワード登録',
        'bulk_mode': False,
    })


@login_required
def keyword_bulk_create(request):
    """キーワード一括作成"""
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
                return redirect('seo_ranking:keyword_list')
        else:
            messages.error(request, '店舗が選択されていません。店舗を選択してからキーワードを登録してください。')
            return redirect('seo_ranking:keyword_list')
    
    # キーワード登録数チェック
    current_count = Keyword.objects.filter(user=target_user).count()
    if current_count >= 10:
        store_name = selected_store.company_name if selected_store else "あなた"
        messages.error(request, f'{store_name}のキーワード登録数の上限（10個）に達しています。既存のキーワードを削除してから登録してください。')
        return redirect('seo_ranking:keyword_list')
    
    if request.method == 'POST':
        form = BulkKeywordForm(request.POST, user=request.user, selected_store=selected_store)
        if form.is_valid():
            keywords_list = form.cleaned_data['keywords']
            rakuten_shop_id = form.cleaned_data['rakuten_shop_id']
            target_product_url = form.cleaned_data.get('target_product_url', '')
            is_active = form.cleaned_data.get('is_active', True)
            
            # 商品IDを商品URLから抽出（target_product_idの代替）
            target_product_id = ''
            if target_product_url:
                import re
                # URLから商品IDを抽出: https://item.rakuten.co.jp/shop-id/item-id/
                match = re.search(r'/([^/]+)/?$', target_product_url.rstrip('/'))
                if match:
                    target_product_id = match.group(1)
            
            # 重複チェック用に既存キーワードを取得
            existing_keywords = set(
                Keyword.objects.filter(user=target_user, rakuten_shop_id=rakuten_shop_id)
                .values_list('keyword', flat=True)
            )
            
            # 一括登録処理
            created_count = 0
            skipped_count = 0
            
            # 現在の登録数を取得
            current_count = Keyword.objects.filter(user=target_user).count()
            
            for keyword_text in keywords_list:
                if keyword_text in existing_keywords:
                    skipped_count += 1
                    continue
                
                # 登録数制限チェック（各店舗10個まで）
                if current_count >= 10:
                    store_name = selected_store.company_name if selected_store else "あなた"
                    messages.error(request, f'{store_name}のキーワード登録数の上限（10個）に達したため、"{keyword_text}" 以降の登録を中断しました。')
                    break
                
                try:
                    Keyword.objects.create(
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
                    logger.error(f'Error creating keyword "{keyword_text}": {e}')
                    skipped_count += 1
            
            # 結果メッセージ
            store_name = selected_store.company_name if selected_store else "あなた"
            if created_count > 0:
                messages.success(request, f'{store_name}に{created_count}個のキーワードを登録しました。')
            if skipped_count > 0:
                messages.warning(request, f'{skipped_count}個のキーワードはスキップされました（重複または処理エラー）。')
            
            return redirect('seo_ranking:keyword_list')
    else:
        form = BulkKeywordForm(user=request.user, selected_store=selected_store)
    
    return render(request, 'seo_ranking/keyword_form.html', {
        'form': form,
        'title': 'キーワード一括登録',
        'bulk_mode': True,
        'selected_store': selected_store,
    })


@login_required
def keyword_edit(request, keyword_id):
    """キーワード編集"""
    # マスターアカウントの場合は全店舗のキーワードにアクセス可能
    if request.user.is_master:
        keyword = get_object_or_404(Keyword, id=keyword_id)
    else:
        keyword = get_object_or_404(Keyword, id=keyword_id, user=request.user)
    
    if request.method == 'POST':
        form = KeywordForm(request.POST, instance=keyword, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'キーワード "{keyword.keyword}" を更新しました。')
            return redirect('seo_ranking:keyword_list')
    else:
        form = KeywordForm(instance=keyword, user=request.user)
    
    return render(request, 'seo_ranking/keyword_form.html', {
        'form': form,
        'title': 'キーワード編集',
        'keyword': keyword,
        'is_edit': True,  # 編集モードフラグを追加
    })


@login_required
def keyword_delete(request, keyword_id):
    """キーワード削除"""
    # マスターアカウントの場合は全店舗のキーワードにアクセス可能
    if request.user.is_master:
        keyword = get_object_or_404(Keyword, id=keyword_id)
    else:
        keyword = get_object_or_404(Keyword, id=keyword_id, user=request.user)
    
    if request.method == 'POST':
        keyword_name = keyword.keyword
        keyword.delete()
        messages.success(request, f'キーワード "{keyword_name}" を削除しました。')
        return redirect('seo_ranking:keyword_list')
    
    return render(request, 'seo_ranking/keyword_confirm_delete.html', {
        'keyword': keyword,
    })


@login_required
@require_http_methods(["POST"])
def keyword_search(request, keyword_id):
    """キーワード検索実行"""
    # マスターアカウントの場合は全店舗のキーワードにアクセス可能
    if request.user.is_master:
        keyword = get_object_or_404(Keyword, id=keyword_id)
    else:
        keyword = get_object_or_404(Keyword, id=keyword_id, user=request.user)
    
    # サブスクリプションチェック
    if not request.user.has_active_subscription():
        messages.error(request, '有効なサブスクリプションが必要です。')
        return JsonResponse({'success': False, 'message': '有効なサブスクリプションが必要です。'})
    
    try:
        # 検索マネージャーを初期化
        search_manager = RakutenSearchManager(request.user)
        
        # 検索実行
        ranking_result = search_manager.execute_keyword_search(keyword)
        
        if ranking_result.is_found:
            messages.success(request, f'キーワード "{keyword.keyword}" の検索が完了しました。順位: {ranking_result.rank}位')
            return JsonResponse({
                'success': True,
                'rank': ranking_result.rank,
                'message': f'順位: {ranking_result.rank}位'
            })
        else:
            messages.info(request, f'キーワード "{keyword.keyword}" で商品が見つかりませんでした（圏外）。')
            return JsonResponse({
                'success': True,
                'rank': None,
                'message': '圏外'
            })
    
    except Exception as e:
        logger.error(f'Search error for keyword {keyword_id}: {e}')
        messages.error(request, '検索中にエラーが発生しました。しばらくしてから再度お試しください。')
        return JsonResponse({'success': False, 'message': '検索処理でエラーが発生しました'})


@login_required
def ranking_results(request, keyword_id):
    """順位結果履歴"""
    # マスターアカウントの場合は全店舗のキーワードにアクセス可能
    if request.user.is_master:
        keyword = get_object_or_404(Keyword, id=keyword_id)
    else:
        keyword = get_object_or_404(Keyword, id=keyword_id, user=request.user)
    
    # 順位結果を取得
    results = RankingResult.objects.filter(keyword=keyword).order_by('-checked_at')
    
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
    
    # ページネーション（365日分のデータを表示するため大きめに設定）
    paginator = Paginator(results, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 一括検索実行可能かチェック
    can_bulk_search = request.user.can_execute_bulk_search_today()
    
    return render(request, 'seo_ranking/ranking_results.html', {
        'keyword': keyword,
        'page_obj': page_obj,
        'period': period,
        'can_bulk_search': can_bulk_search,
    })


@login_required
def ranking_detail(request, result_id):
    """順位結果詳細"""
    # マスターアカウントの場合は全店舗のランキング結果にアクセス可能
    if request.user.is_master:
        result = get_object_or_404(RankingResult, id=result_id)
    else:
        result = get_object_or_404(RankingResult, id=result_id, keyword__user=request.user)
    
    # 上位10商品を取得
    top_products = TopProduct.objects.filter(ranking_result=result).order_by('rank')
    
    # 各商品のキーワード露出頻度を計算
    search_keyword = result.keyword.keyword
    products_with_frequency = []
    
    for product in top_products:
        frequency_data = product.get_keyword_frequency(search_keyword)
        
        # 商品データに頻度情報を追加
        product_data = {
            'product': product,
            'keyword_frequency': frequency_data,
        }
        products_with_frequency.append(product_data)
    
    # 統計情報を計算
    statistics = {}
    if top_products.exists():
        prices = [p.price for p in top_products if p.price is not None]
        review_counts = [p.review_count for p in top_products if p.review_count is not None]
        review_averages = [float(p.review_average) for p in top_products if p.review_average is not None]
        keyword_frequencies = [data['keyword_frequency']['total_count'] for data in products_with_frequency]
        
        if prices:
            statistics['price'] = {
                'min': min(prices),
                'max': max(prices),
                'avg': sum(prices) // len(prices)
            }
        
        if review_counts:
            statistics['review_count'] = {
                'min': min(review_counts),
                'max': max(review_counts),
                'avg': sum(review_counts) // len(review_counts)
            }
        
        if review_averages:
            statistics['review_average'] = {
                'min': min(review_averages),
                'max': max(review_averages),
                'avg': sum(review_averages) / len(review_averages)
            }
        
        if keyword_frequencies:
            statistics['keyword_frequency'] = {
                'min': min(keyword_frequencies),
                'max': max(keyword_frequencies),
                'avg': sum(keyword_frequencies) // len(keyword_frequencies)
            }
    
    # AI分析を実行（マスターアカウントのみ）
    ai_analysis_result = None
    if request.user.is_master:
        ai_analysis_result = get_ai_analysis(result.keyword, result, top_products)
    
    context = {
        'result': result,
        'top_products': top_products,
        'products_with_frequency': products_with_frequency,
        'search_keyword': search_keyword,
        'statistics': statistics,
    }
    
    # マスターアカウントの場合のみAI分析結果を追加
    if ai_analysis_result:
        context['ai_analysis'] = ai_analysis_result
    
    return render(request, 'seo_ranking/ranking_detail.html', context)


@login_required
def export_ranking_csv(request, result_id):
    """順位結果詳細をCSVでエクスポート"""
    # マスターアカウントの場合は全店舗のランキング結果にアクセス可能
    if request.user.is_master:
        result = get_object_or_404(RankingResult, id=result_id)
    else:
        result = get_object_or_404(RankingResult, id=result_id, keyword__user=request.user)
    
    # 上位10商品を取得
    top_products = TopProduct.objects.filter(ranking_result=result).order_by('rank')
    
    # CSVレスポンスを作成
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    
    # ファイル名を作成（日本語文字対応）
    shop_id = result.keyword.rakuten_shop_id
    keyword = result.keyword.keyword
    # UTC時刻を日本時間（JST）に変換
    from django.utils import timezone as tz
    jst_time = tz.localtime(result.checked_at)
    timestamp = jst_time.strftime("%Y%m%d_%H%M")
    filename = f'{shop_id}_{keyword}_{timestamp}.csv'
    
    # ブラウザ対応のためURLエンコードとRFC5987形式を両方指定
    import urllib.parse
    encoded_filename = urllib.parse.quote(filename.encode('utf-8'))
    response['Content-Disposition'] = f'attachment; filename="{shop_id}_{timestamp}.csv"; filename*=UTF-8\'\'{encoded_filename}'
    
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
        'レビュー件数',
        'レビュー評価',
        'ポイント倍率',
        'ジャンル',
        'キーワード露出頻度(総数)',
        'キーワード露出頻度(商品名)',
        'キーワード露出頻度(キャッチコピー)',
        'キーワード露出頻度(商品説明)',
        '個別キーワード詳細',
        '商品説明文',
        '商品URL',
        '自社商品'
    ])
    
    # データ行
    search_keyword = result.keyword.keyword
    for product in top_products:
        # キーワード露出頻度を計算
        frequency_data = product.get_keyword_frequency(search_keyword)
        
        # 個別キーワード詳細をテキスト形式で作成
        keyword_details_text = ""
        if frequency_data.get('keyword_details'):
            details_list = []
            for keyword, details in frequency_data['keyword_details'].items():
                detail_parts = []
                if details['name_count'] > 0:
                    detail_parts.append(f"商品名:{details['name_count']}回")
                if details['catchcopy_count'] > 0:
                    detail_parts.append(f"キャッチコピー:{details['catchcopy_count']}回")
                if details['spec_count'] > 0:
                    detail_parts.append(f"商品説明:{details['spec_count']}回")
                
                details_list.append(f"{keyword}(計{details['total']}回: {' | '.join(detail_parts)})")
            keyword_details_text = " / ".join(details_list)
        
        writer.writerow([
            product.rank,
            product.image_url,
            product.product_name,
            product.catchcopy,
            product.shop_name,
            product.price,
            product.review_count,
            product.review_average,
            product.point_rate,
            product.genre_name,
            frequency_data.get('total_count', 0),
            frequency_data.get('name_count', 0),
            frequency_data.get('catchcopy_count', 0),
            frequency_data.get('spec_count', 0),
            keyword_details_text,
            product.product_spec,
            product.product_url,
            '自社' if product.is_own_product else '他社'
        ])
    
    return response


@login_required
def search_logs(request):
    """検索ログ一覧"""
    # マスターアカウントの場合は全店舗のログを表示（マスター含む）
    if request.user.is_master:
        logs = SearchLog.objects.all().order_by('-created_at')
    else:
        logs = SearchLog.objects.filter(user=request.user).order_by('-created_at')
    
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
    
    return render(request, 'seo_ranking/search_logs.html', {
        'page_obj': page_obj,
        'success_filter': success_filter,
        'period': period,
    })


@login_required
def dashboard(request):
    """SEOダッシュボード"""
    # 統計データを取得
    total_keywords = Keyword.objects.filter(user=request.user).count()
    active_keywords = Keyword.objects.filter(user=request.user, is_active=True).count()
    
    # 最新の検索結果
    recent_results = RankingResult.objects.filter(
        keyword__user=request.user
    ).order_by('-checked_at')[:10]
    
    # 今日の検索ログ
    today = timezone.now().date()
    today_logs = SearchLog.objects.filter(
        user=request.user,
        created_at__date=today
    ).count()
    
    # 成功率計算
    recent_logs = SearchLog.objects.filter(
        user=request.user,
        created_at__gte=timezone.now() - timedelta(days=30)
    )
    success_rate = 0
    if recent_logs.exists():
        success_rate = (recent_logs.filter(success=True).count() / recent_logs.count()) * 100
    
    # 一括検索実行可能かチェック
    can_bulk_search = request.user.can_execute_bulk_search_today()
    
    return render(request, 'seo_ranking/dashboard.html', {
        'total_keywords': total_keywords,
        'active_keywords': active_keywords,
        'recent_results': recent_results,
        'today_logs': today_logs,
        'success_rate': success_rate,
        'can_bulk_search': can_bulk_search,
    })


@login_required
@require_http_methods(["POST"])
def bulk_keyword_search(request):
    """一括キーワード検索実行"""
    user = request.user
    
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
    
    # 1ヶ月無料期間チェック（マスターアカウントは除外）
    if not user.is_master and not target_user.is_within_trial_period():
        return JsonResponse({'success': False, 'error': '無料期間が終了しています。有料プランへのアップグレードが必要です。'})
    
    # 1日1回制限チェック（マスターアカウント以外）
    if not user.is_master and not target_user.can_execute_bulk_search_today():
        messages.error(request, '一括検索は1日1回のみ実行可能です。明日再度お試しください。')
        return JsonResponse({'success': False, 'error': '一括検索は1日1回のみ実行可能です。明日再度お試しください。'})
    
    try:
        # 対象ユーザーのアクティブなキーワードを取得
        active_keywords = Keyword.objects.filter(user=target_user, is_active=True)
        
        if not active_keywords.exists():
            messages.warning(request, 'アクティブなキーワードが見つかりません。')
            return JsonResponse({'success': False, 'error': 'アクティブなキーワードが見つかりません。'})
        
        # 検索マネージャーを初期化（対象ユーザーで初期化）
        search_manager = RakutenSearchManager(target_user)
        
        success_count = 0
        error_count = 0
        total_count = active_keywords.count()
        
        store_name = target_user.company_name if user.is_master else target_user.email
        logger.info(f"Starting bulk search for user {target_user.id} ({store_name}), {total_count} keywords")
        
        for i, keyword in enumerate(active_keywords):
            try:
                # 楽天API制限を考慮して間隔を空ける
                if i > 0:
                    time.sleep(1)  # 1秒間隔
                
                # 検索実行
                ranking_result = search_manager.execute_keyword_search(keyword)
                success_count += 1
                
                logger.info(f"Bulk search progress: {i+1}/{total_count} - Keyword: {keyword.keyword}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error in bulk search for keyword {keyword.keyword}: {e}")
                continue
        
        # 最終一括検索日を更新（マスターアカウント以外）
        if not user.is_master:
            target_user.update_last_bulk_search_date()
        
        # 結果メッセージ
        store_info = f"店舗「{target_user.company_name}」の" if user.is_master else ""
        message = f'{store_info}一括検索が完了しました。成功: {success_count}件'
        if error_count > 0:
            message += f', エラー: {error_count}件'
        
        messages.success(request, message)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'success_count': success_count,
            'error_count': error_count,
            'total_count': total_count
        })
        
    except Exception as e:
        logger.error(f'Bulk search error for user {user.id}: {e}')
        messages.error(request, '一括検索中にエラーが発生しました。しばらくしてから再度お試しください。')
        return JsonResponse({'success': False, 'error': '検索処理でエラーが発生しました'})


@login_required
@require_http_methods(["POST"])
def update_ranking_memo(request, result_id):
    """SEOランキング結果のメモを更新"""
    try:
        # ランキング結果を取得（マスターアカウントの場合は全店舗アクセス可能）
        if request.user.is_master:
            ranking_result = get_object_or_404(RankingResult, id=result_id)
        else:
            ranking_result = get_object_or_404(
                RankingResult,
                id=result_id,
                keyword__user=request.user
            )
        
        # POSTデータからメモを取得
        memo_text = request.POST.get('memo', '').strip()
        
        # メモを更新
        ranking_result.memo = memo_text
        ranking_result.save(update_fields=['memo'])
        
        logger.info(f"ランキング結果 {result_id} のメモを更新: {request.user.email}")
        
        messages.success(request, 'メモを更新しました')
        
        # リファラーチェック - 履歴ページから来た場合は履歴ページに戻る
        referer = request.META.get('HTTP_REFERER', '')
        if 'results' in referer and 'ranking_detail' not in referer:
            return redirect('seo_ranking:ranking_results', keyword_id=ranking_result.keyword.id)
        else:
            return redirect('seo_ranking:ranking_detail', result_id=result_id)
        
    except Exception as e:
        logger.error(f"メモ更新エラー: {e}")
        messages.error(request, 'メモの更新に失敗しました')
        
        # エラー時もリファラーチェック
        referer = request.META.get('HTTP_REFERER', '')
        if 'results' in referer and 'ranking_detail' not in referer:
            try:
                # マスターアカウントの場合は全店舗のランキング結果にアクセス可能
                if request.user.is_master:
                    ranking_result = RankingResult.objects.get(id=result_id)
                else:
                    ranking_result = RankingResult.objects.get(id=result_id, keyword__user=request.user)
                return redirect('seo_ranking:ranking_results', keyword_id=ranking_result.keyword.id)
            except (RankingResult.DoesNotExist, ValueError):
                pass
        return redirect('seo_ranking:ranking_detail', result_id=result_id)
