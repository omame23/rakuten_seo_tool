import os
from celery import Celery

# Django settingsモジュールをCeleryに設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inspice_seo_tool.settings')

app = Celery('inspice_seo_tool')

# Django設定ファイルからCelery設定を読み込み
app.config_from_object('django.conf:settings', namespace='CELERY')

# タスクの自動検出
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')