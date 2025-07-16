#!/usr/bin/env python
"""
楽天市場API検索機能のテストスクリプト
"""
import os
import sys
import django
from django.conf import settings

# Django設定の初期化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inspice_seo_tool.settings')
django.setup()

from seo_ranking.rakuten_api import RakutenSearchAPI

def test_rakuten_search():
    print("楽天市場API検索テストを開始します...")
    
    # APIキーの確認
    api_key = settings.RAKUTEN_API_KEY
    if not api_key:
        print("エラー: RAKUTEN_API_KEYが設定されていません")
        return
    
    print(f"APIキー: {api_key}")
    
    # 検索APIを初期化
    search_api = RakutenSearchAPI(api_key)
    
    try:
        # テスト検索実行
        keyword = "コーヒー"
        print(f"キーワード '{keyword}' で検索中...")
        
        result = search_api.search_products(keyword, page=1, per_page=10)
        
        if 'Items' in result:
            print(f"検索成功: {len(result['Items'])}件の商品が見つかりました")
            
            # 最初の商品の詳細を表示
            if result['Items']:
                first_item = result['Items'][0]['Item']
                print(f"1位の商品: {first_item.get('itemName', 'N/A')}")
                print(f"店舗名: {first_item.get('shopName', 'N/A')}")
                print(f"価格: {first_item.get('itemPrice', 'N/A')}円")
        else:
            print("検索結果が空です")
            print("レスポンス:", result)
            
    except Exception as e:
        print(f"検索エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rakuten_search()