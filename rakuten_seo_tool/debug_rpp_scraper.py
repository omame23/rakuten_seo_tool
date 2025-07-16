"""
RPPスクレイピングのデバッグスクリプト
実際の楽天検索結果を取得してHTML構造を確認する
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

def debug_rpp_search(keyword):
    """指定キーワードで楽天検索を実行してHTML構造をデバッグ"""
    
    # セッション作成
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    # 楽天検索URLを構築
    encoded_keyword = quote(keyword)
    url = f"https://search.rakuten.co.jp/search/mall/{encoded_keyword}/"
    
    print(f"検索URL: {url}")
    print(f"検索キーワード: {keyword}")
    print("=" * 80)
    
    try:
        # ページを取得
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        print(f"レスポンスステータス: {response.status_code}")
        print(f"コンテンツ長: {len(response.content)} bytes")
        print("=" * 80)
        
        # BeautifulSoupでHTML解析
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 検索結果の商品一覧エリアを探す
        print("検索結果コンテナを探しています...")
        
        # よく使われるクラス名のパターンを確認
        container_patterns = [
            'searchresult',
            'search-result',
            'productList',
            'product-list',
            'itemList',
            'item-list',
            'productItem',
            'product-item',
            'searchItem',
            'search-item'
        ]
        
        containers_found = []
        for pattern in container_patterns:
            elements = soup.find_all(['div', 'ul', 'ol', 'section'], 
                                   class_=re.compile(pattern, re.I))
            if elements:
                containers_found.extend([(pattern, elem) for elem in elements])
        
        print(f"見つかったコンテナ: {len(containers_found)}個")
        
        # 各コンテナの内容を調査
        for i, (pattern, container) in enumerate(containers_found[:3]):  # 最初の3個のみ
            print(f"\n--- コンテナ {i+1} (パターン: {pattern}) ---")
            print(f"タグ: {container.name}")
            print(f"クラス: {container.get('class', [])}")
            
            # 商品アイテムを探す
            items = container.find_all(['div', 'li', 'article'], limit=5)
            print(f"子要素数: {len(items)}")
            
            for j, item in enumerate(items[:2]):  # 最初の2個のみ詳細表示
                print(f"\n  アイテム {j+1}:")
                print(f"  クラス: {item.get('class', [])}")
                
                # PRマーカーを探す
                pr_markers = item.find_all(text=re.compile(r'PR|広告|Ad|スポンサー', re.I))
                if pr_markers:
                    print(f"  PRマーカー発見: {pr_markers}")
                
                # 商品名を探す
                title_elem = item.find(['a', 'h1', 'h2', 'h3', 'h4'])
                if title_elem:
                    title = title_elem.get_text(strip=True)[:100]
                    print(f"  商品名: {title}")
                
                # 店舗名を探す
                shop_patterns = ['shop', 'store', 'seller', 'merchant']
                for shop_pattern in shop_patterns:
                    shop_elem = item.find(['span', 'div', 'a'], 
                                        class_=re.compile(shop_pattern, re.I))
                    if shop_elem:
                        shop_name = shop_elem.get_text(strip=True)
                        print(f"  店舗名候補 ({shop_pattern}): {shop_name}")
                        break
        
        # PRや広告関連のテキストを全体検索
        print("\n" + "=" * 80)
        print("PR/広告関連テキストの全体検索:")
        
        pr_texts = soup.find_all(text=re.compile(r'PR|広告|Ad|スポンサー|Sponsored', re.I))
        print(f"PR関連テキスト: {len(pr_texts)}個発見")
        
        for i, pr_text in enumerate(pr_texts[:10]):  # 最初の10個のみ
            parent = pr_text.parent
            print(f"{i+1}. テキスト: '{pr_text.strip()}'")
            print(f"   親要素: {parent.name if parent else 'None'}")
            print(f"   親クラス: {parent.get('class', []) if parent else 'None'}")
        
        # stepmarket店舗の商品を検索
        print("\n" + "=" * 80)
        print("stepmarket店舗の商品を検索:")
        
        stepmarket_elements = soup.find_all(text=re.compile(r'stepmarket', re.I))
        print(f"stepmarket関連要素: {len(stepmarket_elements)}個発見")
        
        for i, elem_text in enumerate(stepmarket_elements):
            parent = elem_text.parent
            print(f"{i+1}. テキスト: '{elem_text.strip()}'")
            print(f"   親要素: {parent.name if parent else 'None'}")
            print(f"   親クラス: {parent.get('class', []) if parent else 'None'}")
            
            # この要素の周辺にPRマーカーがあるかチェック
            if parent:
                ancestor = parent.find_parent(['div', 'li', 'article'])
                if ancestor:
                    pr_in_ancestor = ancestor.find_all(text=re.compile(r'PR|広告|Ad', re.I))
                    if pr_in_ancestor:
                        print(f"   同一商品内のPRマーカー: {pr_in_ancestor}")
        
        print("\n検索完了")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # ペットブランケットで検索
    debug_rpp_search("ペットブランケット")