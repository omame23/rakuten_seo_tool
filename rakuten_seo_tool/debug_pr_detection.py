"""
[PR]マーク付き商品の検出をデバッグするスクリプト
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

def debug_pr_detection(keyword):
    """[PR]マーク付き商品の検出方法をデバッグ"""
    
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
        
        # [PR]マークを含む全ての要素を検索
        print("[PR]マーク付き要素の詳細調査:")
        print("-" * 40)
        
        # 様々なパターンでPRマークを検索
        pr_patterns = [
            re.compile(r'\[PR\]', re.I),
            re.compile(r'PR', re.I),
            re.compile(r'広告', re.I),
            re.compile(r'Ad', re.I),
            re.compile(r'スポンサー', re.I)
        ]
        
        all_pr_elements = []
        
        for pattern in pr_patterns:
            elements = soup.find_all(text=pattern)
            for elem in elements:
                parent = elem.parent if elem.parent else None
                if parent:
                    all_pr_elements.append({
                        'text': elem.strip(),
                        'parent_tag': parent.name,
                        'parent_class': parent.get('class', []),
                        'parent_id': parent.get('id', ''),
                        'pattern': pattern.pattern
                    })
        
        print(f"発見されたPR関連要素: {len(all_pr_elements)}個")
        
        for i, elem in enumerate(all_pr_elements, 1):
            print(f"\n{i}. テキスト: '{elem['text']}'")
            print(f"   パターン: {elem['pattern']}")
            print(f"   親タグ: {elem['parent_tag']}")
            print(f"   親クラス: {elem['parent_class']}")
            print(f"   親ID: {elem['parent_id']}")
            
            # この要素から商品情報を辿れるかチェック
            try:
                parent_soup = BeautifulSoup(str(elem), 'html.parser') if isinstance(elem, str) else elem
                # 商品URLを持つ最も近いリンク要素を探す
                link_elem = None
                current = elem.get('parent')
                
                # 上方向に辿って商品リンクを探す
                for _ in range(10):  # 最大10階層まで
                    if not current:
                        break
                    
                    # 楽天商品URLを持つリンクを探す
                    links = current.find_all('a', href=re.compile(r'item\.rakuten\.co\.jp'))
                    if links:
                        link_elem = links[0]
                        break
                    
                    current = current.parent
                
                if link_elem:
                    product_url = link_elem.get('href', '')
                    product_name = link_elem.get_text(strip=True)[:50]
                    print(f"   → 関連商品URL: {product_url}")
                    print(f"   → 商品名: {product_name}")
                    
                    # 店舗IDを抽出
                    url_match = re.search(r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)', product_url)
                    if url_match:
                        shop_id = url_match.group(1)
                        product_id = url_match.group(2)
                        print(f"   → 店舗ID: {shop_id}")
                        print(f"   → 商品ID: {product_id}")
                else:
                    print(f"   → 関連商品URL: 見つからず")
            except Exception as e:
                print(f"   → エラー: {e}")
        
        print("\n" + "=" * 80)
        print("特定の[PR]マーク付きリンクの詳細調査:")
        print("-" * 40)
        
        # より具体的に[PR]マーク付きのリンクを探す
        pr_links = soup.find_all('a', text=re.compile(r'\[PR\]'))
        
        print(f"[PR]マーク付きリンク: {len(pr_links)}個発見")
        
        for i, link in enumerate(pr_links, 1):
            print(f"\n{i}. [PR]リンク:")
            print(f"   テキスト: {link.get_text()[:100]}")
            print(f"   href: {link.get('href', '')}")
            print(f"   クラス: {link.get('class', [])}")
            
            # 商品URLかチェック
            href = link.get('href', '')
            if 'item.rakuten.co.jp' in href:
                url_match = re.search(r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)', href)
                if url_match:
                    print(f"   → 店舗ID: {url_match.group(1)}")
                    print(f"   → 商品ID: {url_match.group(2)}")
                    print(f"   ★ これは広告商品です")
        
        print("\n検索完了")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    debug_pr_detection("ペットブランケット")