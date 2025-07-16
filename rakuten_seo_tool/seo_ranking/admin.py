from django.contrib import admin
from .models import Keyword, RankingResult, TopProduct, SearchLog


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'user', 'rakuten_shop_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'user']
    search_fields = ['keyword', 'user__email', 'rakuten_shop_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('user', 'keyword', 'rakuten_shop_id', 'is_active')
        }),
        ('対象商品', {
            'fields': ('target_product_url', 'target_product_id')
        }),
        ('日時', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(RankingResult)
class RankingResultAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'rank', 'is_found', 'total_results', 'checked_at']
    list_filter = ['is_found', 'checked_at', 'keyword__user']
    search_fields = ['keyword__keyword', 'keyword__user__email']
    readonly_fields = ['checked_at']
    
    fieldsets = (
        ('検索結果', {
            'fields': ('keyword', 'rank', 'is_found', 'total_results')
        }),
        ('エラー情報', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('日時', {
            'fields': ('checked_at',)
        })
    )


class TopProductInline(admin.TabularInline):
    model = TopProduct
    extra = 0
    readonly_fields = ['collected_at']


@admin.register(TopProduct)
class TopProductAdmin(admin.ModelAdmin):
    list_display = ['rank', 'product_name', 'shop_name', 'price', 'is_own_product', 'collected_at']
    list_filter = ['is_own_product', 'collected_at', 'ranking_result__keyword__user']
    search_fields = ['product_name', 'shop_name', 'ranking_result__keyword__keyword']
    readonly_fields = ['collected_at']
    
    fieldsets = (
        ('商品情報', {
            'fields': ('ranking_result', 'rank', 'product_name', 'product_url', 'product_id')
        }),
        ('店舗情報', {
            'fields': ('shop_name', 'shop_id', 'is_own_product')
        }),
        ('詳細情報', {
            'fields': ('price', 'review_count', 'review_average', 'image_url')
        }),
        ('日時', {
            'fields': ('collected_at',)
        })
    )


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'user', 'execution_time', 'pages_checked', 'products_found', 'success', 'created_at']
    list_filter = ['success', 'created_at', 'user']
    search_fields = ['keyword', 'user__email']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('検索情報', {
            'fields': ('user', 'keyword', 'success')
        }),
        ('実行統計', {
            'fields': ('execution_time', 'pages_checked', 'products_found')
        }),
        ('エラー詳細', {
            'fields': ('error_details',),
            'classes': ('collapse',)
        }),
        ('日時', {
            'fields': ('created_at',)
        })
    )


# RankingResultAdminにTopProductInlineを追加
RankingResultAdmin.inlines = [TopProductInline]
