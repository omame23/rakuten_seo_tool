# Generated by Django 5.1.5 on 2025-07-12 07:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seo_ranking', '0008_rakutengenre'),
    ]

    operations = [
        migrations.AddField(
            model_name='rankingtarget',
            name='check_all_genres',
            field=models.BooleanField(default=True, help_text='第5階層までの全ジャンルをチェックするか', verbose_name='全ジャンルチェック'),
        ),
        migrations.AlterField(
            model_name='rankingtarget',
            name='target_genre_ids',
            field=models.TextField(blank=True, help_text='調査するジャンルID（複数の場合は改行区切り）※空の場合は全ジャンル', null=True, verbose_name='調査対象ジャンルID'),
        ),
    ]
