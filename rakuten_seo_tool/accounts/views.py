from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """ダッシュボードビュー"""
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # サブスクリプション状態のチェック
        if not user.has_active_subscription() and not user.is_master:
            messages.warning(
                self.request,
                'サブスクリプションが無効です。全機能を利用するには有効なサブスクリプションが必要です。'
            )
        
        # マスターアカウントの場合は特別なメッセージ
        if user.is_master:
            messages.info(
                self.request,
                f'マスターアカウントでログイン中です。全機能・全店舗データにアクセス可能です。'
            )
        
        # キーワード数を取得
        from seo_ranking.models import Keyword
        
        # マスターアカウントの場合は選択店舗のデータを表示
        if user.is_master:
            # 全店舗リストを取得
            from .models import User
            all_stores = User.objects.filter(is_master=False).order_by('company_name')
            context['all_stores'] = all_stores
            
            # 選択店舗があればそのデータを表示
            selected_store_id = self.request.session.get('selected_store_id')
            if selected_store_id:
                try:
                    selected_user = User.objects.get(id=selected_store_id, is_master=False)
                    keyword_count = Keyword.objects.filter(user=selected_user).count()
                    context['selected_store'] = selected_user
                except User.DoesNotExist:
                    # 選択店舗が見つからない場合はセッションをクリア
                    self.request.session.pop('selected_store_id', None)
                    self.request.session.pop('selected_store_name', None)
                    keyword_count = Keyword.objects.filter(user__is_master=False).count()
            else:
                # 全店舗のキーワード数
                keyword_count = Keyword.objects.filter(user__is_master=False).count()
        else:
            keyword_count = Keyword.objects.filter(user=user).count()
        
        context['has_active_subscription'] = user.has_active_subscription()
        context['subscription_status'] = user.subscription_status
        context['is_master'] = user.is_master
        context['keyword_count'] = keyword_count
        
        return context


@login_required
def account_settings(request):
    """アカウント設定ページ"""
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        user = request.user
        
        if form_type == 'account_info':
            # アカウント情報更新
            # 楽天店舗IDの重複チェック（マスターアカウント以外）
            new_shop_id = request.POST.get('rakuten_shop_id', '').strip()
            
            # 重複チェックが必要かどうか
            need_duplicate_check = new_shop_id and not user.is_master and new_shop_id != user.rakuten_shop_id
            
            if need_duplicate_check:
                # 自分以外で同じ店舗IDを持つユーザーがいるかチェック
                from .models import User
                existing_user = User.objects.filter(
                    rakuten_shop_id=new_shop_id,
                    is_master=False
                ).exclude(id=user.id).exists()
                
                if existing_user:
                    messages.error(request, 'この楽天店舗IDは既に別のユーザーに登録されています。')
                    return redirect('accounts:settings')
            
            # 各フィールドを更新
            user.company_name = request.POST.get('company_name', user.company_name)
            user.contact_name = request.POST.get('contact_name', user.contact_name)
            user.phone_number = request.POST.get('phone_number', user.phone_number)
            
            # 楽天店舗IDを更新（空文字の場合は更新しない）
            if new_shop_id:
                user.rakuten_shop_id = new_shop_id
            
            user.save()
            messages.success(request, 'アカウント情報を更新しました。')
            
        elif form_type == 'password_change':
            # パスワード変更
            current_password = request.POST.get('current_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            # 現在のパスワード確認
            if not check_password(current_password, user.password):
                messages.error(request, '現在のパスワードが正しくありません。')
                return redirect('accounts:settings')
            
            # 新しいパスワードの確認
            if new_password1 != new_password2:
                messages.error(request, '新しいパスワードが一致しません。')
                return redirect('accounts:settings')
            
            # パスワードの長さチェック
            if len(new_password1) < 8:
                messages.error(request, 'パスワードは8文字以上で設定してください。')
                return redirect('accounts:settings')
            
            # パスワードを更新
            user.set_password(new_password1)
            user.save()
            
            # セッションを維持（ログアウトを防ぐ）
            update_session_auth_hash(request, user)
            
            messages.success(request, 'パスワードを変更しました。')
            
        elif form_type == 'auto_search_settings':
            # 自動検索設定
            auto_search_enabled = request.POST.get('auto_search_enabled') == 'on'
            auto_search_time = request.POST.get('auto_search_time')
            
            if auto_search_time:
                from datetime import datetime
                try:
                    # 時間形式の検証
                    time_obj = datetime.strptime(auto_search_time, '%H:%M').time()
                    user.auto_search_enabled = auto_search_enabled
                    user.auto_search_time = time_obj
                    user.save()
                    
                    messages.success(request, '自動検索設定を更新しました。')
                except ValueError:
                    messages.error(request, '時間の形式が正しくありません。')
            else:
                messages.error(request, '時間を入力してください。')
        
        return redirect('accounts:settings')
    
    # マスターアカウント用の統計情報
    context = {}
    if request.user.is_master:
        from .models import User
        context.update({
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'trial_users': User.objects.filter(subscription_status='trial').count(),
        })
    
    return render(request, 'accounts/settings.html', context)


@login_required
def billing_info(request):
    """請求情報ページ"""
    return render(request, 'accounts/billing.html', {
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    })


# confirm_email ビューは削除（allauthのデフォルト処理を使用）
