from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
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