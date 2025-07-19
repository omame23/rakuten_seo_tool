import stripe
import json
import logging
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.utils import timezone
from .models import User

logger = logging.getLogger(__name__)

# Stripe Webhook シークレット
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Stripe Webhookエンドポイント"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        # Webhookの署名を検証
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        logger.error("Invalid payload in Stripe webhook")
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        logger.error("Invalid signature in Stripe webhook")
        return HttpResponseBadRequest("Invalid signature")
    
    # イベントタイプに応じて処理
    if event['type'] == 'customer.subscription.created':
        handle_subscription_created(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    elif event['type'] == 'invoice.payment_succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])
    else:
        logger.info(f"Unhandled event type: {event['type']}")
    
    return HttpResponse(status=200)


def handle_subscription_created(subscription):
    """サブスクリプション作成時の処理"""
    try:
        customer_id = subscription['customer']
        status = subscription['status']
        
        # カスタマーIDからユーザーを特定
        user = User.objects.get(stripe_customer_id=customer_id)
        
        # ユーザーのサブスクリプション状態を更新
        if status == 'active':
            user.subscription_status = 'active'
        elif status == 'trialing':
            user.subscription_status = 'trial'
        elif status == 'past_due':
            user.subscription_status = 'past_due'
        else:
            user.subscription_status = 'inactive'
        
        user.save()
        
        logger.info(f"Subscription created for user {user.id}: {status}")
        
    except User.DoesNotExist:
        logger.error(f"User not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling subscription created: {e}")


def handle_subscription_updated(subscription):
    """サブスクリプション更新時の処理"""
    try:
        customer_id = subscription['customer']
        status = subscription['status']
        
        # カスタマーIDからユーザーを特定
        user = User.objects.get(stripe_customer_id=customer_id)
        
        # ユーザーのサブスクリプション状態を更新
        if status == 'active':
            user.subscription_status = 'active'
        elif status == 'trialing':
            user.subscription_status = 'trial'
        elif status == 'past_due':
            user.subscription_status = 'past_due'
        elif status == 'canceled':
            user.subscription_status = 'canceled'
        else:
            user.subscription_status = 'inactive'
        
        # プラン情報も更新
        if subscription.get('items') and subscription['items']['data']:
            price_id = subscription['items']['data'][0]['price']['id']
            
            if price_id == 'price_1RmXcoLifu2YUCmRzmEJLAYd':  # スタンダードプラン
                user.subscription_plan = 'standard'
            elif price_id == 'price_1RmXdwLifu2YUCmRI3rZQUGH':  # マスタープラン
                user.subscription_plan = 'master'
        
        user.save()
        
        logger.info(f"Subscription updated for user {user.id}: {status}")
        
    except User.DoesNotExist:
        logger.error(f"User not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling subscription updated: {e}")


def handle_subscription_deleted(subscription):
    """サブスクリプション削除時の処理"""
    try:
        customer_id = subscription['customer']
        
        # カスタマーIDからユーザーを特定
        user = User.objects.get(stripe_customer_id=customer_id)
        
        # ユーザーのサブスクリプション状態を更新
        user.subscription_status = 'canceled'
        user.save()
        
        logger.info(f"Subscription deleted for user {user.id}")
        
    except User.DoesNotExist:
        logger.error(f"User not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling subscription deleted: {e}")


def handle_payment_succeeded(invoice):
    """支払い成功時の処理"""
    try:
        customer_id = invoice['customer']
        
        # カスタマーIDからユーザーを特定
        user = User.objects.get(stripe_customer_id=customer_id)
        
        # サブスクリプションが有効の場合、ステータスを確認
        if invoice.get('subscription'):
            user.subscription_status = 'active'
            user.save()
        
        logger.info(f"Payment succeeded for user {user.id}")
        
    except User.DoesNotExist:
        logger.error(f"User not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling payment succeeded: {e}")


def handle_payment_failed(invoice):
    """支払い失敗時の処理"""
    try:
        customer_id = invoice['customer']
        
        # カスタマーIDからユーザーを特定
        user = User.objects.get(stripe_customer_id=customer_id)
        
        # サブスクリプションの状態を支払い遅延に変更
        user.subscription_status = 'past_due'
        user.save()
        
        logger.warning(f"Payment failed for user {user.id}")
        
    except User.DoesNotExist:
        logger.error(f"User not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling payment failed: {e}")