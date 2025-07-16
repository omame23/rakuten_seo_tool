from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def master_account_required(view_func):
    """マスターアカウント専用デコレーター"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_master:
            messages.error(request, 'この機能はマスターアカウントのみ利用可能です。')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view