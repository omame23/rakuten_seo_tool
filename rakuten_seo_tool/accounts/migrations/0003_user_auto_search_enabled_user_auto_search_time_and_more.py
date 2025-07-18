# Generated by Django 5.1.5 on 2025-07-11 06:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_is_master'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='auto_search_enabled',
            field=models.BooleanField(default=True, help_text='毎日自動でキーワード順位を確認する', verbose_name='自動検索有効'),
        ),
        migrations.AddField(
            model_name='user',
            name='auto_search_time',
            field=models.TimeField(default='10:00', help_text='毎日自動検索を実行する時間（24時間形式）', verbose_name='自動検索時間'),
        ),
        migrations.AddField(
            model_name='user',
            name='last_bulk_search_date',
            field=models.DateField(blank=True, help_text='最後に一括検索を実行した日付', null=True, verbose_name='最終一括検索日'),
        ),
        migrations.AlterField(
            model_name='user',
            name='rakuten_shop_id',
            field=models.CharField(max_length=100, null=True, verbose_name='楽天店舗ID'),
        ),
    ]
