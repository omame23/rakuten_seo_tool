from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from allauth.account.views import SignupView
from allauth.account import app_settings
from allauth.account.utils import complete_signup
from .forms import CustomSignupForm
from .models import User
import stripe
import json
import logging

logger = logging.getLogger(__name__)

# Stripe APIキー設定
stripe.api_key = settings.STRIPE_SECRET_KEY


class CustomSignupView(SignupView):
    """カスタム新規登録ビュー（Stripe決済統合）"""
    form_class = CustomSignupForm
    template_name = 'account/signup.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stripe_public_key'] = settings.STRIPE_PUBLIC_KEY
        return context
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        try:
            # Payment Method IDを取得
            payment_method_id = self.request.POST.get('payment_method_id')
            if not payment_method_id:
                messages.error(self.request, 'クレジットカード情報が正しく取得できませんでした。')
                return self.form_invalid(form)
            
            # ユーザーを作成（まだデータベースに保存しない）
            user = form.save(self.request)
            
            # Stripeカスタマーを作成
            try:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.contact_name,
                    payment_method=payment_method_id,
                    invoice_settings={'default_payment_method': payment_method_id},
                    metadata={
                        'user_id': user.id,
                        'company_name': user.company_name,
                        'rakuten_shop_id': user.rakuten_shop_id,
                    }
                )
                
                # ユーザーにStripeカスタマーIDを設定
                user.stripe_customer_id = customer.id
                user.save()
                
                # 選択されたプランに応じてPrice IDを決定
                plan = form.cleaned_data.get('subscription_plan', 'standard')
                if plan == 'standard':
                    price_id = 'price_1RmXcoLifu2YUCmRzmEJLAYd'
                else:  # master
                    price_id = 'price_1RmXdwLifu2YUCmRI3rZQUGH'
                
                # トライアル付きサブスクリプションを作成
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': price_id}],
                    trial_period_days=30,  # 30日間の無料トライアル
                    payment_settings={'save_default_payment_method': 'on_subscription'},
                    expand=['latest_invoice.payment_intent'],
                )
                
                logger.info(f"User {user.id} registered with Stripe subscription {subscription.id}")
                
                # allauthの完了処理
                ret = complete_signup(
                    self.request, user,
                    app_settings.EMAIL_VERIFICATION,
                    self.get_success_url()
                )
                
                messages.success(
                    self.request,
                    f'登録が完了しました！{plan.title()}プランで30日間の無料トライアルが開始されました。'
                )
                
                return ret
                
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error during signup: {e}")
                # Stripeエラーの場合、ユーザーは作成されているので削除
                user.delete()
                messages.error(self.request, f'決済処理でエラーが発生しました: {str(e)}')
                return self.form_invalid(form)
                
        except Exception as e:
            logger.error(f"Signup error: {e}")
            messages.error(self.request, '登録処理中にエラーが発生しました。しばらく時間をおいて再度お試しください。')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """フォームが無効な場合の処理"""
        logger.warning(f"Signup form invalid: {form.errors}")
        return super().form_invalid(form)


def custom_signup_view(request):
    """カスタム新規登録ビュー関数版（必要に応じて使用）"""
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            try:
                # Payment Method IDを取得
                payment_method_id = request.POST.get('payment_method_id')
                if not payment_method_id:
                    messages.error(request, 'クレジットカード情報が正しく取得できませんでした。')
                    return render(request, 'account/signup.html', {
                        'form': form,
                        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
                    })
                
                # ユーザーを作成
                user = form.save(request)
                
                # Stripeカスタマーとサブスクリプションを作成
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.contact_name,
                    payment_method=payment_method_id,
                    invoice_settings={'default_payment_method': payment_method_id},
                    metadata={
                        'user_id': user.id,
                        'company_name': user.company_name,
                        'rakuten_shop_id': user.rakuten_shop_id,
                    }
                )
                
                user.stripe_customer_id = customer.id
                user.save()
                
                # プランに応じてサブスクリプション作成
                plan = form.cleaned_data.get('subscription_plan', 'standard')
                price_id = 'price_1RmXcoLifu2YUCmRzmEJLAYd' if plan == 'standard' else 'price_1RmXdwLifu2YUCmRI3rZQUGH'
                
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': price_id}],
                    trial_period_days=30,
                    payment_settings={'save_default_payment_method': 'on_subscription'},
                )
                
                # ログイン処理
                login(request, user)
                
                messages.success(request, f'登録が完了しました！{plan.title()}プランで30日間の無料トライアルが開始されました。')
                return redirect('accounts:dashboard')
                
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error: {e}")
                if 'user' in locals():
                    user.delete()
                messages.error(request, f'決済処理でエラーが発生しました: {str(e)}')
            except Exception as e:
                logger.error(f"Signup error: {e}")
                messages.error(request, '登録処理中にエラーが発生しました。')
        else:
            messages.error(request, '入力内容に不備があります。')
    else:
        form = CustomSignupForm()
    
    return render(request, 'account/signup.html', {
        'form': form,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    })