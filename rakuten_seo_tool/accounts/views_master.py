from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from .models import User
from .decorators import master_account_required
from .forms_master import StoreCreateForm, StoreUpdateForm
from seo_ranking.models import Keyword, RankingResult
from seo_ranking.models_rpp import RPPKeyword, RPPResult


@method_decorator(master_account_required, name='dispatch')
class StoreListView(ListView):
    """店舗一覧ビュー"""
    model = User
    template_name = 'accounts/master/store_list.html'
    context_object_name = 'stores'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.filter(is_master=False).select_related()
        
        # 検索機能
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(rakuten_shop_id__icontains=search) |
                Q(company_name__icontains=search) |
                Q(contact_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        # ステータスフィルタ
        status = self.request.GET.get('status')
        if status:
            if status == 'active':
                queryset = queryset.filter(is_active=True, subscription_status='active')
            elif status == 'trial':
                queryset = queryset.filter(subscription_status='trial')
            elif status == 'inactive':
                queryset = queryset.filter(Q(is_active=False) | Q(subscription_status='inactive'))
        
        # キーワード数でアノテート
        queryset = queryset.annotate(
            keyword_count=Count('keywords', distinct=True),
            rpp_keyword_count=Count('rpp_keywords', distinct=True)
        )
        
        return queryset.order_by('-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        
        # 統計情報
        all_stores = User.objects.filter(is_master=False)
        context['total_stores'] = all_stores.count()
        context['active_stores'] = all_stores.filter(is_active=True, subscription_status='active').count()
        context['trial_stores'] = all_stores.filter(subscription_status='trial').count()
        context['inactive_stores'] = all_stores.filter(Q(is_active=False) | Q(subscription_status='inactive')).count()
        
        return context


@method_decorator(master_account_required, name='dispatch')
class StoreDetailView(DetailView):
    """店舗詳細ビュー"""
    model = User
    template_name = 'accounts/master/store_detail.html'
    context_object_name = 'store'
    
    def get_queryset(self):
        return User.objects.filter(is_master=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = self.object
        
        # SEOキーワード統計
        seo_keywords = Keyword.objects.filter(user=store)
        context['seo_keyword_count'] = seo_keywords.count()
        
        # 最新の順位結果
        latest_rankings = RankingResult.objects.filter(
            keyword__user=store
        ).order_by('-checked_at')[:5]
        context['latest_rankings'] = latest_rankings
        
        # RPPキーワード統計
        rpp_keywords = RPPKeyword.objects.filter(user=store)
        context['rpp_keyword_count'] = rpp_keywords.count()
        
        # 最新のRPP結果
        latest_rpp_results = RPPResult.objects.filter(
            keyword__user=store
        ).order_by('-checked_at')[:5]
        context['latest_rpp_results'] = latest_rpp_results
        
        return context


@method_decorator(master_account_required, name='dispatch')
class StoreCreateView(CreateView):
    """新規店舗追加ビュー（楽天店舗IDのみで登録）"""
    model = User
    form_class = StoreCreateForm
    template_name = 'accounts/master/store_form.html'
    success_url = reverse_lazy('accounts:master_store_list')

    def form_valid(self, form):
        user = form.save()
        messages.success(
            self.request, 
            f'店舗「{user.company_name}」を追加しました。\n'
            f'楽天店舗ID: {user.rakuten_shop_id}\n'
            f'一時メールアドレス: {user.email}\n'
            f'一時パスワード: temppass123\n'
            f'※店舗には正式な情報への更新をお願いしてください。'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '新規店舗追加'
        context['button_text'] = '店舗を追加'
        context['is_create'] = True
        return context


@method_decorator(master_account_required, name='dispatch')
class StoreUpdateView(UpdateView):
    """店舗情報編集ビュー"""
    model = User
    form_class = StoreUpdateForm
    template_name = 'accounts/master/store_form.html'
    
    def get_queryset(self):
        return User.objects.filter(is_master=False)
    
    def get_success_url(self):
        return reverse_lazy('accounts:master_store_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'店舗「{form.instance.company_name}」の情報を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '店舗情報編集'
        context['button_text'] = '更新'
        context['is_create'] = False
        return context


@method_decorator(master_account_required, name='dispatch')
class StoreDeleteView(DeleteView):
    """店舗削除ビュー"""
    model = User
    template_name = 'accounts/master/store_confirm_delete.html'
    success_url = reverse_lazy('accounts:master_store_list')
    context_object_name = 'store'
    
    def get_queryset(self):
        return User.objects.filter(is_master=False)

    def delete(self, request, *args, **kwargs):
        store = self.get_object()
        company_name = store.company_name
        result = super().delete(request, *args, **kwargs)
        messages.success(request, f'店舗「{company_name}」を削除しました。')
        return result


@master_account_required
def store_export_csv(request):
    """店舗データCSVエクスポート"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stores.csv"'
    response.write('\ufeff')  # BOM for Excel

    writer = csv.writer(response)
    writer.writerow([
        '楽天店舗ID', '会社名', '担当者名', 'メールアドレス', '電話番号',
        'サブスクリプション状態', '有効', '登録日時', 'SEOキーワード数', 'RPPキーワード数'
    ])

    stores = User.objects.filter(is_master=False).annotate(
        keyword_count=Count('keywords', distinct=True),
        rpp_keyword_count=Count('rpp_keywords', distinct=True)
    )

    for store in stores:
        writer.writerow([
            store.rakuten_shop_id or '',
            store.company_name,
            store.contact_name,
            store.email,
            store.phone_number,
            store.get_subscription_status_display(),
            '有効' if store.is_active else '無効',
            store.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            store.keyword_count,
            store.rpp_keyword_count,
        ])

    return response


@master_account_required
def store_bulk_action(request):
    """店舗一括操作"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '無効なリクエストです'})

    action = request.POST.get('action')
    store_ids = request.POST.getlist('store_ids')

    if not store_ids:
        return JsonResponse({'success': False, 'error': '店舗が選択されていません'})

    stores = User.objects.filter(id__in=store_ids, is_master=False)
    
    if action == 'activate':
        stores.update(is_active=True)
        messages.success(request, f'{len(store_ids)}件の店舗を有効にしました。')
    elif action == 'deactivate':
        stores.update(is_active=False)
        messages.success(request, f'{len(store_ids)}件の店舗を無効にしました。')
    else:
        return JsonResponse({'success': False, 'error': '無効な操作です'})

    return JsonResponse({'success': True})


@master_account_required
def set_selected_store(request):
    """選択店舗をセッションに保存"""
    if request.method == 'POST':
        store_id = request.POST.get('store_id')
        if store_id:
            if store_id == 'all':
                request.session['selected_store_id'] = None
                request.session['selected_store_name'] = '全店舗'
            else:
                try:
                    store = User.objects.get(id=store_id, is_invited_user=True)
                    request.session['selected_store_id'] = store_id
                    request.session['selected_store_name'] = store.company_name
                except User.DoesNotExist:
                    return JsonResponse({'success': False, 'error': '店舗が見つかりません'})
            
            return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': '無効なリクエストです'})


@master_account_required
def view_store_dashboard(request, pk):
    """指定店舗のダッシュボードに移動（店舗を選択状態にしてダッシュボードにリダイレクト）"""
    try:
        store = User.objects.get(id=pk, is_master=False)
        # セッションに選択店舗を設定
        request.session['selected_store_id'] = str(pk)
        request.session['selected_store_name'] = store.company_name
        
        messages.info(
            request,
            f'店舗「{store.company_name}」のダッシュボードを表示しています。'
        )
        
        # ダッシュボードにリダイレクト
        return redirect('accounts:dashboard')
        
    except User.DoesNotExist:
        messages.error(request, '指定された店舗が見つかりません。')
        return redirect('accounts:master_store_list')


@master_account_required
def revenue_dashboard(request):
    """売上管理ダッシュボード"""
    # 現在の日付
    today = timezone.now().date()
    
    # 今月の開始日
    month_start = today.replace(day=1)
    
    # 先月の開始日
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    
    # 全ユーザー（マスター以外）
    all_users = User.objects.filter(is_master=False)
    
    # 無料体験中のユーザー数
    trial_users = all_users.filter(subscription_status='trial').count()
    
    # 課金中のユーザー数
    active_users = all_users.filter(subscription_status='active').count()
    
    # 今月新規登録ユーザー数
    new_users_this_month = all_users.filter(
        date_joined__gte=month_start
    ).count()
    
    # 先月新規登録ユーザー数
    new_users_last_month = all_users.filter(
        date_joined__gte=last_month_start,
        date_joined__lt=month_start
    ).count()
    
    # 月額料金（¥3,980）
    monthly_fee = 3980
    
    # 今月の推定売上（課金ユーザー数 × 月額料金）
    estimated_revenue = active_users * monthly_fee
    
    # 先月の課金ユーザー数（概算）
    # 実際のデータがない場合は現在の数値を使用
    last_month_active_users = active_users  # 実際には履歴データが必要
    last_month_revenue = last_month_active_users * monthly_fee
    
    # ユーザー状況の詳細
    user_stats = {
        'total_users': all_users.count(),
        'trial_users': trial_users,
        'active_users': active_users,
        'inactive_users': all_users.filter(subscription_status='inactive').count(),
        'new_users_this_month': new_users_this_month,
        'new_users_last_month': new_users_last_month,
    }
    
    # 売上情報
    revenue_stats = {
        'estimated_monthly_revenue': estimated_revenue,
        'last_month_revenue': last_month_revenue,
        'monthly_fee': monthly_fee,
        'revenue_growth': estimated_revenue - last_month_revenue,
    }
    
    # 最近の新規登録ユーザー（直近10件）
    recent_users = all_users.order_by('-date_joined')[:10]
    
    # 月別の登録ユーザー数推移（直近12ヶ月）
    monthly_registrations = []
    for i in range(12):
        month_date = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        next_month = (month_date + timedelta(days=32)).replace(day=1)
        
        count = all_users.filter(
            date_joined__gte=month_date,
            date_joined__lt=next_month
        ).count()
        
        monthly_registrations.append({
            'month': month_date.strftime('%Y-%m'),
            'count': count
        })
    
    monthly_registrations.reverse()
    
    context = {
        'user_stats': user_stats,
        'revenue_stats': revenue_stats,
        'recent_users': recent_users,
        'monthly_registrations': monthly_registrations,
        'today': today,
    }
    
    return render(request, 'accounts/master/revenue_dashboard.html', context)