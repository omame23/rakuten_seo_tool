"""
最終的なRPP広告検出デバッグ
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inspice_seo_tool.settings')
django.setup()

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re
import json

def debug_rpp_final(keyword):
    """RPP広告検出の最終デバッグ"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    encoded_keyword = quote(keyword)
    url = f"https://search.rakuten.co.jp/search/mall/{encoded_keyword}/"
    
    print(f"検索URL: {url}")
    print(f"検索キーワード: {keyword}")
    print("=" * 80)
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # __INITIAL_STATE__を検索
        script_tags = soup.find_all('script')
        
        for script in script_tags:
            if script.string and 'window.__INITIAL_STATE__' in script.string:
                print("__INITIAL_STATE__を発見!")
                
                script_content = script.string
                start_index = script_content.find('window.__INITIAL_STATE__ = ') + len('window.__INITIAL_STATE__ = ')
                end_index = script_content.find(';\n', start_index)
                if end_index == -1:
                    end_index = len(script_content)
                
                json_str = script_content[start_index:end_index].strip()
                
                try:
                    initial_state = json.loads(json_str)
                    
                    # データ構造を詳しく調査
                    print("データ構造調査:")
                    data = initial_state.get('data', {})
                    print(f"data keys: {list(data.keys())}")
                    
                    ichiba_search = data.get('ichibaSearch', {})
                    print(f"ichibaSearch keys: {list(ichiba_search.keys())}")
                    
                    items = ichiba_search.get('items', [])
                    print(f"検索結果アイテム数: {len(items)}")
                    
                    # itemsが空の場合、他の場所にアイテムがあるかチェック
                    if not items:
                        print("\nitemsが空です。他の場所を探しています...")
                        
                        # ネストした構造を探す
                        def find_items_recursive(obj, path=""):
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    new_path = f"{path}.{key}" if path else key
                                    if key == 'items' and isinstance(value, list) and value:
                                        print(f"items found at: {new_path} (length: {len(value)})")
                                        return value
                                    result = find_items_recursive(value, new_path)
                                    if result:
                                        return result
                            elif isinstance(obj, list):
                                for i, value in enumerate(obj):
                                    result = find_items_recursive(value, f"{path}[{i}]")
                                    if result:
                                        return result
                            return None
                        
                        items = find_items_recursive(initial_state) or []
                        print(f"見つかったアイテム数: {len(items)}")
                    
                    print("-" * 40)
                    
                    rpp_count = 0
                    for i, item in enumerate(items, 1):
                        item_options = item.get('itemOptions', {})
                        cpc_info = item_options.get('cpc', {})
                        
                        product_name = item.get('name', '')
                        shop_info = item.get('shop', {})
                        original_url = item.get('originalItemUrl', '')
                        
                        print(f"\n{i}. 商品: {product_name[:50]}")
                        print(f"   CPC Type: {cpc_info.get('type', 'なし')}")
                        print(f"   Shop Name: {shop_info.get('name', 'なし')}")
                        print(f"   Shop URL Code: {shop_info.get('urlCode', 'なし')}")
                        print(f"   Original URL: {original_url}")
                        print(f"   Price: {item.get('price', 'なし')}")
                        
                        if cpc_info.get('type') == 'grp07rpp':
                            rpp_count += 1
                            print(f"   → RPP広告 #{rpp_count}")
                            
                            # 店舗IDをチェック
                            shop_code = shop_info.get('urlCode', '')
                            if shop_code == 'stepmarket':
                                print(f"   ★★★ stepmarket商品発見! RPP広告順位: {rpp_count}位 ★★★")
                            
                            # URLからも店舗IDを確認
                            if original_url:
                                url_match = re.search(r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)', original_url)
                                if url_match:
                                    url_shop = url_match.group(1)
                                    product_id = url_match.group(2)
                                    print(f"   URL店舗ID: {url_shop}, 商品ID: {product_id}")
                                    
                                    if url_shop == 'stepmarket':
                                        print(f"   ★★★ stepmarket商品発見! (URL解析) RPP広告順位: {rpp_count}位 ★★★")
                    
                    print(f"\n総RPP広告数: {rpp_count}")
                    break
                    
                except json.JSONDecodeError as e:
                    print(f"JSON解析エラー: {e}")
                break
        
        print("\n検索完了")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    debug_rpp_final("ペットブランケット")