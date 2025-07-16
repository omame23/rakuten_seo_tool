from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest
import logging

logger = logging.getLogger(__name__)


def custom_404(request, exception=None):
    """Custom 404 error handler"""
    logger.warning(f'404 error: {request.path}')
    return render(request, '404.html', status=404)


def custom_500(request):
    """Custom 500 error handler"""
    logger.error(f'500 error: {request.path}')
    return render(request, '500.html', status=500)


def custom_403(request, exception=None):
    """Custom 403 error handler"""
    logger.warning(f'403 error: {request.path}')
    return render(request, '403.html', status=403)


def custom_400(request, exception=None):
    """Custom 400 error handler"""
    logger.warning(f'400 error: {request.path}')
    return render(request, '400.html', status=400)