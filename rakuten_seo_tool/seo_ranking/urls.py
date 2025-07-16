from django.urls import path
from . import views
from . import views_rpp

app_name = 'seo_ranking'

urlpatterns = [
    # ダッシュボード
    path('', views.dashboard, name='dashboard'),
    
    # SEOキーワード管理
    path('keywords/', views.keyword_list, name='keyword_list'),
    path('keywords/create/', views.keyword_create, name='keyword_create'),
    path('keywords/bulk-create/', views.keyword_bulk_create, name='keyword_bulk_create'),
    path('keywords/<int:keyword_id>/edit/', views.keyword_edit, name='keyword_edit'),
    path('keywords/<int:keyword_id>/delete/', views.keyword_delete, name='keyword_delete'),
    path('keywords/<int:keyword_id>/search/', views.keyword_search, name='keyword_search'),
    path('keywords/bulk-search/', views.bulk_keyword_search, name='bulk_keyword_search'),
    
    # SEO順位結果
    path('keywords/<int:keyword_id>/results/', views.ranking_results, name='ranking_results'),
    path('results/<int:result_id>/', views.ranking_detail, name='ranking_detail'),
    path('results/<int:result_id>/export-csv/', views.export_ranking_csv, name='export_ranking_csv'),
    path('results/<int:result_id>/update-memo/', views.update_ranking_memo, name='update_ranking_memo'),
    
    # SEO検索ログ
    path('logs/', views.search_logs, name='search_logs'),
    
    # RPPキーワード管理
    path('rpp/keywords/', views_rpp.rpp_keyword_list, name='rpp_keyword_list'),
    path('rpp/keywords/create/', views_rpp.rpp_keyword_create, name='rpp_keyword_create'),
    path('rpp/keywords/bulk-create/', views_rpp.rpp_keyword_bulk_create, name='rpp_keyword_bulk_create'),
    path('rpp/keywords/<int:keyword_id>/edit/', views_rpp.rpp_keyword_edit, name='rpp_keyword_edit'),
    path('rpp/keywords/<int:keyword_id>/delete/', views_rpp.rpp_keyword_delete, name='rpp_keyword_delete'),
    path('rpp/search/<int:keyword_id>/', views_rpp.rpp_keyword_search, name='rpp_keyword_search'),
    path('rpp/bulk-search/', views_rpp.rpp_bulk_search, name='rpp_bulk_search'),
    
    # RPP順位結果
    path('rpp/results/<int:keyword_id>/', views_rpp.rpp_results, name='rpp_results'),
    path('rpp/detail/<int:result_id>/', views_rpp.rpp_detail, name='rpp_detail'),
    path('rpp/export/<int:result_id>/', views_rpp.export_rpp_csv, name='export_rpp_csv'),
    path('rpp/memo/update/<int:result_id>/', views_rpp.update_rpp_memo, name='update_rpp_memo'),
    
    # RPP検索ログ
    path('rpp/logs/', views_rpp.rpp_search_logs, name='rpp_search_logs'),
    
    # RPP全店舗データ（マスター限定）
    path('rpp/all-data/', views_rpp.rpp_all_data, name='rpp_all_data'),
]