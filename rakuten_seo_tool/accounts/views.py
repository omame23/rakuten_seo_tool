from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
import logging

logger = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """ダッシュボードビュー"""
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 新規登録ユーザーはStripe決済済みなので警告表示は不要
        
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
            # 招待ユーザーのみのリストを取得
            from .models import User
            all_stores = User.objects.filter(is_invited_user=True).order_by('company_name')
            context['all_stores'] = all_stores
            
            # 選択店舗があればそのデータを表示
            selected_store_id = self.request.session.get('selected_store_id')
            if selected_store_id:
                try:
                    selected_user = User.objects.get(id=selected_store_id, is_invited_user=True)
                    keyword_count = Keyword.objects.filter(user=selected_user).count()
                    context['selected_store'] = selected_user
                except User.DoesNotExist:
                    # 選択店舗が見つからない場合はセッションをクリア
                    self.request.session.pop('selected_store_id', None)
                    self.request.session.pop('selected_store_name', None)
                    keyword_count = Keyword.objects.filter(user__is_invited_user=True).count()
            else:
                # 招待ユーザーのキーワード数
                keyword_count = Keyword.objects.filter(user__is_invited_user=True).count()
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
            
            # プラン変更処理（通常ユーザーのみ）
            if not user.is_master and not user.is_invited_user:
                new_plan = request.POST.get('subscription_plan', user.subscription_plan)
                if new_plan in ['standard', 'master'] and new_plan != user.subscription_plan:
                    user.subscription_plan = new_plan
                    messages.success(request, f'サブスクリプションプランを{user.get_plan_display_name()}に変更しました。次回請求から適用されます。')
            
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
            auto_seo_search_enabled = request.POST.get('auto_seo_search_enabled') == 'on'
            auto_rpp_search_enabled = request.POST.get('auto_rpp_search_enabled') == 'on'
            auto_search_time = request.POST.get('auto_search_time')
            
            # SEO・RPP自動検索設定を更新
            user.auto_seo_search_enabled = auto_seo_search_enabled
            user.auto_rpp_search_enabled = auto_rpp_search_enabled
            
            # マスターアカウントの場合のみ時間設定を処理
            if user.is_master and auto_search_time:
                from datetime import datetime
                try:
                    # 時間形式の検証
                    time_obj = datetime.strptime(auto_search_time, '%H:%M').time()
                    user.auto_search_time = time_obj
                except ValueError:
                    messages.error(request, '時間の形式が正しくありません。')
                    return redirect('accounts:settings')
            elif user.is_master and not auto_search_time:
                # マスターアカウントで時間が空の場合はNullに設定
                user.auto_search_time = None
            
            user.save()
            messages.success(request, '自動検索設定を更新しました。')
        
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
    user = request.user
    
    # サブスクリプション状態の詳細情報を取得
    subscription_info = {
        'status': user.subscription_status,
        'plan': user.subscription_plan,
        'is_trial': user.subscription_status == 'trial',
        'is_active': user.subscription_status == 'active',
        'trial_end_date': user.trial_end_date,
    }
    
    # Stripeサブスクリプション情報を取得
    stripe_subscription = None
    if user.stripe_customer_id:
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            subscriptions = stripe.Subscription.list(
                customer=user.stripe_customer_id,
                limit=1
            )
            if subscriptions.data:
                stripe_subscription = subscriptions.data[0]
                
        except Exception as e:
            logger.error(f'Failed to get Stripe subscription: {e}')
    
    return render(request, 'accounts/billing.html', {
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'subscription_info': subscription_info,
        'stripe_subscription': stripe_subscription,
    })


def create_checkout_session(request):
    """Stripeチェックアウトセッション作成"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POSTメソッドが必要です'})
    
    try:
        import stripe
        import json
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        data = json.loads(request.body)
        plan = data.get('plan', 'standard')
        
        # Price IDを決定
        if plan == 'standard':
            price_id = 'price_1RmXcoLifu2YUCmRzmEJLAYd'
            plan_name = 'スタンダードプラン'
        elif plan == 'master':
            price_id = 'price_1RmXdwLifu2YUCmRI3rZQUGH'
            plan_name = 'マスタープラン'
        else:
            return JsonResponse({'success': False, 'error': '無効なプランです'})
        
        # チェックアウトセッションを作成
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            subscription_data={
                'trial_period_days': 30,  # 30日間無料トライアル
            },
            success_url=request.build_absolute_uri('/accounts/checkout/success/') + '?session_id={CHECKOUT_SESSION_ID}&plan=' + plan,
            cancel_url=request.build_absolute_uri('/'),
            metadata={
                'plan': plan,
                'plan_name': plan_name,
            }
        )
        
        return JsonResponse({
            'success': True,
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id,
        })
        
    except Exception as e:
        logger.error(f'Checkout session creation error: {e}')
        return JsonResponse({'success': False, 'error': str(e)})


def checkout_success(request):
    """チェックアウト成功後の処理"""
    session_id = request.GET.get('session_id')
    plan = request.GET.get('plan', 'standard')
    
    if not session_id:
        messages.error(request, 'セッションIDが見つかりません。')
        return redirect('home')
    
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        # セッション情報を取得
        session = stripe.checkout.Session.retrieve(session_id)
        
        # セッション情報をsessionに保存
        request.session['stripe_session_id'] = session_id
        request.session['stripe_customer_id'] = session.customer
        request.session['stripe_subscription_id'] = session.subscription
        request.session['selected_plan'] = plan
        
        # 新規登録ページにリダイレクト
        return redirect('account_signup')
        
    except Exception as e:
        logger.error(f'Checkout success error: {e}')
        messages.error(request, 'チェックアウト処理でエラーが発生しました。')
        return redirect('home')


def create_subscription_signup(request):
    """新規登録時のサブスクリプション作成"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POSTメソッドが必要です'})
    
    try:
        import stripe
        import json
        from django.contrib.auth import login
        from .forms import CustomSignupForm
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        data = json.loads(request.body)
        
        # フォームデータを作成
        form_data = {
            'email': data.get('email'),
            'password1': data.get('password1'),
            'password2': data.get('password2'),
            'company_name': data.get('company_name'),
            'contact_name': data.get('contact_name'),
            'phone_number': data.get('phone_number'),
            'rakuten_shop_id': data.get('rakuten_shop_id'),
            'subscription_plan': data.get('plan', 'standard'),
            'terms_agreement': data.get('terms_agreement'),
        }
        
        # フォームバリデーション
        form = CustomSignupForm(form_data)
        if not form.is_valid():
            return JsonResponse({
                'success': False, 
                'error': '入力内容に不備があります: ' + str(form.errors)
            })
        
        # ユーザーを作成（仮のrequestオブジェクトを作成）
        class FakeRequest:
            def __init__(self):
                self.user = None
                self.session = {}
        
        fake_request = FakeRequest()
        user = form.save(fake_request)
        
        # Stripeカスタマーを作成
        customer = stripe.Customer.create(
            email=user.email,
            name=user.contact_name,
            metadata={
                'user_id': user.id,
                'company_name': user.company_name,
                'rakuten_shop_id': user.rakuten_shop_id,
            }
        )
        
        user.stripe_customer_id = customer.id
        user.save()
        
        # Price IDを決定
        plan = data.get('plan', 'standard')
        if plan == 'standard':
            price_id = 'price_1RmXcoLifu2YUCmRzmEJLAYd'
        elif plan == 'master':
            price_id = 'price_1RmXdwLifu2YUCmRI3rZQUGH'
        else:
            return JsonResponse({'success': False, 'error': '無効なプランです'})
        
        # トライアル付きサブスクリプションを作成
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': price_id}],
            trial_period_days=30,  # 30日間の無料トライアル
            payment_behavior='default_incomplete',
            payment_settings={'save_default_payment_method': 'on_subscription'},
            expand=['latest_invoice.payment_intent'],
        )
        
        # ユーザーをログイン
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret,
            'subscription_id': subscription.id,
        })
        
    except Exception as e:
        logger.error(f'Signup subscription creation error: {e}')
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def create_subscription(request):
    """サブスクリプション作成"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POSTメソッドが必要です'})
    
    try:
        import stripe
        import json
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        data = json.loads(request.body)
        plan = data.get('plan', request.user.subscription_plan)
        
        # Price IDを決定
        if plan == 'standard':
            price_id = 'price_1RmVueQ5K9ikjqbDDkLo7lXg'
        elif plan == 'master':
            price_id = 'price_1RmVvXQ5K9ikjqbDHsmutBvF'
        else:
            return JsonResponse({'success': False, 'error': '無効なプランです'})
        
        # Stripeカスタマーを作成または取得
        if request.user.stripe_customer_id:
            customer = stripe.Customer.retrieve(request.user.stripe_customer_id)
        else:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.contact_name,
                metadata={
                    'user_id': request.user.id,
                    'company_name': request.user.company_name,
                }
            )
            request.user.stripe_customer_id = customer.id
            request.user.save()
        
        # サブスクリプションを作成
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{
                'price': price_id,
            }],
            payment_behavior='default_incomplete',
            payment_settings={'save_default_payment_method': 'on_subscription'},
            expand=['latest_invoice.payment_intent'],
        )
        
        return JsonResponse({
            'success': True,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret,
            'subscription_id': subscription.id,
        })
        
    except Exception as e:
        logger.error(f'Subscription creation error: {e}')
        return JsonResponse({'success': False, 'error': str(e)})


@login_required  
def change_plan(request):
    """プラン変更"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POSTメソッドが必要です'})
    
    try:
        import stripe
        import json
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        data = json.loads(request.body)
        new_plan = data.get('plan')
        user = request.user
        
        if new_plan not in ['standard', 'master']:
            return JsonResponse({'success': False, 'error': '無効なプランです'})
        
        # Price IDを決定
        if new_plan == 'standard':
            new_price_id = 'price_1RmXcoLifu2YUCmRzmEJLAYd'
        else:  # master
            new_price_id = 'price_1RmXdwLifu2YUCmRI3rZQUGH'
        
        # Stripeカスタマーを取得（stripe_customer_idがない場合はメールアドレスで検索）
        stripe_customer_id = user.stripe_customer_id
        
        if not stripe_customer_id:
            # メールアドレスでStripeカスタマーを検索
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                stripe_customer_id = customers.data[0].id
                # 見つかったカスタマーIDをユーザーに保存
                user.stripe_customer_id = stripe_customer_id
                user.save()
                logger.info(f'Found Stripe customer {stripe_customer_id} for user {user.id} by email')
            else:
                logger.error(f'No Stripe customer found for user {user.id} ({user.email})')
                return JsonResponse({'success': False, 'error': 'Stripeカスタマーが見つかりません'})
        
        # サブスクリプション一覧を取得
        subscriptions = stripe.Subscription.list(
            customer=stripe_customer_id,
            status='active',
            limit=1
        )
        
        if not subscriptions.data:
            # トライアル中のサブスクリプションも確認
            subscriptions = stripe.Subscription.list(
                customer=stripe_customer_id,
                status='trialing',
                limit=1
            )
            
            if not subscriptions.data:
                logger.error(f'No active or trialing subscriptions found for customer {stripe_customer_id}')
                return JsonResponse({'success': False, 'error': 'アクティブなサブスクリプションが見つかりません'})
        
        subscription = subscriptions.data[0]
        
        # サブスクリプションアイテムを更新
        stripe.Subscription.modify(
            subscription.id,
            items=[{
                'id': subscription['items']['data'][0].id,
                'price': new_price_id,
            }],
            proration_behavior='always_invoice',
        )
        
        # ユーザーのプラン情報を更新
        user.subscription_plan = new_plan
        user.save()
        
        logger.info(f'Plan changed successfully for user {user.id} to {new_plan}')
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f'Plan change error for user {request.user.id}: {e}')
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def cancel_subscription(request):
    """サービス解約（Stripe解約 + アカウント削除）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POSTメソッドが必要です'})
    
    try:
        import stripe
        from django.contrib.auth import logout
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        user = request.user
        
        # Stripeサブスクリプションの解約
        try:
            # stripe_customer_idがある場合はそれを使用、ない場合はメールアドレスで検索
            customers_to_cancel = []
            
            if user.stripe_customer_id:
                customers_to_cancel.append(user.stripe_customer_id)
            else:
                # メールアドレスでStripeカスタマーを検索
                customers = stripe.Customer.list(email=user.email, limit=10)
                for customer in customers.data:
                    customers_to_cancel.append(customer.id)
                    logger.info(f'Found Stripe customer {customer.id} for email {user.email}')
            
            # 各カスタマーのサブスクリプションをキャンセル
            for customer_id in customers_to_cancel:
                subscriptions = stripe.Subscription.list(
                    customer=customer_id,
                    limit=10
                )
                
                for subscription in subscriptions.data:
                    if subscription.status in ['active', 'trialing', 'past_due']:
                        stripe.Subscription.cancel(subscription.id)
                        logger.info(f'Cancelled Stripe subscription {subscription.id} (status: {subscription.status}) for user {user.id}')
                    else:
                        logger.info(f'Skipped Stripe subscription {subscription.id} (status: {subscription.status}) for user {user.id}')
            
            if not customers_to_cancel:
                logger.warning(f'No Stripe customers found for user {user.id} ({user.email})')
                
        except Exception as e:
            logger.error(f'Failed to cancel Stripe subscription for user {user.id}: {e}')
            # Stripeエラーでも続行
        
        # ユーザーデータの削除前にログ出力
        logger.info(f'Deleting user account: {user.email} (ID: {user.id})')
        
        # セッションからユーザーをログアウト
        logout(request)
        
        # ユーザーアカウントを削除（関連データも自動削除される）
        user.delete()
        
        return JsonResponse({'success': True, 'message': '解約が完了しました。ご利用ありがとうございました。'})
        
    except Exception as e:
        logger.error(f'Account cancellation error: {e}')
        return JsonResponse({'success': False, 'error': '解約処理中にエラーが発生しました。サポートまでお問い合わせください。'})


# confirm_email ビューは削除（allauthのデフォルト処理を使用）


def resend_email_verification(request):
    """認証メール再送信"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            messages.error(request, 'メールアドレスを入力してください。')
            return render(request, 'account/email_resend.html')
        
        try:
            from .models import User
            user = User.objects.get(email=email)
            
            # メールアドレスを取得または作成
            email_address, created = EmailAddress.objects.get_or_create(
                user=user,
                email=user.email.lower(),
                defaults={'verified': False, 'primary': True}
            )
            
            # まだ認証されていない場合のみ送信
            if not email_address.verified:
                send_email_confirmation(request, user, signup=True)
                messages.success(request, f'{email} 宛に認証メールを再送信しました。')
                return render(request, 'account/verification_sent.html')
            else:
                messages.info(request, 'このメールアドレスは既に認証済みです。')
                return redirect('account_login')
                
        except User.DoesNotExist:
            messages.error(request, 'このメールアドレスのアカウントが見つかりません。')
            return render(request, 'account/email_resend.html')
        except Exception as e:
            logger.error(f'Email resend error: {e}')
            messages.error(request, '認証メール送信中にエラーが発生しました。')
            return render(request, 'account/email_resend.html')
    
    return render(request, 'account/email_resend.html')


def email_verification_sent(request):
    """認証メール送信完了ページ"""
    return render(request, 'account/verification_sent.html')
