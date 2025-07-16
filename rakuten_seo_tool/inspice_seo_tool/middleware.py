import logging
from django.conf import settings
from django.http import HttpResponseServerError
from django.shortcuts import render

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware:
    """
    カスタムエラーハンドリングミドルウェア
    本番環境で詳細なエラー情報が漏洩しないようにする
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Exception as e:
            # エラーをログに記録
            logger.error(f'Unhandled exception: {e}', exc_info=True)
            
            # 本番環境では一般的なエラーページを表示
            if not settings.DEBUG:
                return render(request, '500.html', status=500)
            else:
                # 開発環境では通常のデバッグページを表示
                raise
        
        return response
    
    def process_exception(self, request, exception):
        """
        例外処理
        """
        logger.error(f'Exception in {request.path}: {exception}', exc_info=True)
        
        # 本番環境では詳細な情報を隠す
        if not settings.DEBUG:
            return render(request, '500.html', status=500)
        
        # 開発環境ではNoneを返してデフォルトの処理を続行
        return None