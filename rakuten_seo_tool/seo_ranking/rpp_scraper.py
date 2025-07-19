"""
RPP広告順位スクレイピング機能
楽天検索結果ページから[PR]マーク付きの広告商品を抽出する
"""

import time
import logging
import re
import json
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote, urljoin
import requests
from bs4 import BeautifulSoup
from django.utils import timezone

logger = logging.getLogger(__name__)


class RPPScraper:
    """楽天RPP広告スクレイピングクラス"""
    
    def __init__(self, delay_between_requests: float = 1.0):
        """
        初期化
        
        Args:
            delay_between_requests: リクエスト間の待機時間（秒）
        """
        self.delay = delay_between_requests
        self.session = requests.Session()
        
        # User-Agentを設定（一般的なブラウザを模倣）
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def search_rpp_ads(self, keyword: str, max_pages: int = 3) -> Tuple[List[Dict], bool]:
        """
        指定キーワードでRPP広告を検索
        
        Args:
            keyword: 検索キーワード
            max_pages: 最大検索ページ数（デフォルト3ページ、最大15位まで）
            
        Returns:
            Tuple[広告リスト, 成功フラグ]
        """
        ads = []
        overall_rank = 1
        
        try:
            for page in range(1, max_pages + 1):
                logger.debug(f"RPP検索: {keyword} - ページ {page}")
                
                # ページのスクレイピング
                page_ads = self._scrape_page(keyword, page)
                
                if not page_ads:
                    # 広告が見つからない場合、次のページをチェック
                    logger.debug(f"ページ {page} でRPP広告が見つかりませんでした")
                    continue
                
                # 全体順位を設定
                for ad in page_ads:
                    # 15位まででカットオフ
                    if overall_rank > 15:
                        logger.info(f"15位に達したため広告処理を終了")
                        break
                    
                    ad['rank'] = overall_rank
                    ad['page_number'] = page
                    overall_rank += 1
                    ads.append(ad)
                
                # 15位に達したら検索終了
                if overall_rank > 15:
                    logger.debug(f"15位に達したため検索を終了")
                    break
                
                # リクエスト間隔を空ける
                if page < max_pages:
                    time.sleep(self.delay)
            
            logger.info(f"RPP検索完了: {keyword} - 総広告数: {len(ads)}")
            return ads, True
            
        except Exception as e:
            logger.error(f"RPP検索エラー ({keyword}): {e}")
            return ads, False
    
    def _scrape_page(self, keyword: str, page: int) -> List[Dict]:
        """
        指定ページから広告を抽出
        
        Args:
            keyword: 検索キーワード
            page: ページ番号
            
        Returns:
            広告データのリスト
        """
        try:
            # 楽天検索URLを構築
            encoded_keyword = quote(keyword)
            url = f"https://search.rakuten.co.jp/search/mall/{encoded_keyword}/"
            
            if page > 1:
                url += f"?p={page}"
            
            logger.debug(f"リクエスト URL: {url}")
            
            # ページを取得
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # BeautifulSoupでHTML解析
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # RPP広告を抽出
            ads = self._extract_rpp_ads(soup, page)
            
            return ads
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ページ取得エラー (page {page}): {e}")
            return []
        except Exception as e:
            logger.error(f"ページ解析エラー (page {page}): {e}")
            return []
    
    def _extract_rpp_ads(self, soup: BeautifulSoup, page: int) -> List[Dict]:
        """
        BeautifulSoupオブジェクトからRPP広告を抽出
        
        Args:
            soup: BeautifulSoupオブジェクト
            page: ページ番号
            
        Returns:
            広告データのリスト
        """
        ads = []
        position_on_page = 1
        
        try:
            # まず__INITIAL_STATE__からRPP広告情報を抽出
            script_tags = soup.find_all('script')
            initial_state_found = False
            
            for script in script_tags:
                if script.string and 'window.__INITIAL_STATE__' in script.string:
                    try:
                        # JavaScriptコードからJSONデータを抽出
                        script_content = script.string
                        start_index = script_content.find('window.__INITIAL_STATE__ = ') + len('window.__INITIAL_STATE__ = ')
                        
                        # JSONの終端を見つける（次の;</の手前まで）
                        end_index = script_content.find(';\n', start_index)
                        if end_index == -1:
                            end_index = len(script_content)
                        
                        json_str = script_content[start_index:end_index].strip()
                        
                        initial_state = json.loads(json_str)
                        
                        # itemsを取得（再帰的検索を含む）
                        items = []
                        
                        # まず通常のパスを試す
                        data = initial_state.get('data', {})
                        if data and isinstance(data, dict):
                            ichiba_search = data.get('ichibaSearch', {})
                            if ichiba_search and isinstance(ichiba_search, dict):
                                items = ichiba_search.get('items', [])
                        
                        # 通常のパスで見つからない場合は効率的な検索を実行
                        if not items:
                            def find_items_optimized(obj, max_depth=5, current_depth=0):
                                """効率化された商品リスト検索（深度制限付き）"""
                                if current_depth > max_depth:
                                    return None
                                    
                                if isinstance(obj, dict):
                                    # よく使われるキー名を優先的にチェック
                                    priority_keys = ['items', 'products', 'itemList', 'results']
                                    for key in priority_keys:
                                        value = obj.get(key)
                                        if isinstance(value, list) and value:
                                            return value
                                    
                                    # 'items'キーが最も可能性が高いので、限定的に再帰
                                    for key, value in obj.items():
                                        if 'item' in key.lower() or 'product' in key.lower():
                                            if isinstance(value, list) and value:
                                                return value
                                            elif isinstance(value, dict):
                                                result = find_items_optimized(value, max_depth, current_depth + 1)
                                                if result:
                                                    return result
                                elif isinstance(obj, list) and len(obj) > 0:
                                    # 最初の要素のみチェック（パフォーマンス重視）
                                    if len(obj) > 0:
                                        result = find_items_optimized(obj[0], max_depth, current_depth + 1)
                                        if result:
                                            return result
                                return None
                            
                            items = find_items_optimized(initial_state) or []
                        
                        logger.debug(f"検索結果アイテム数: {len(items)}")
                        
                        for i, item in enumerate(items, 1):
                            # アイテムがNoneでないかチェック
                            if not item or not isinstance(item, dict):
                                continue
                                
                            # CPC情報をチェックしてRPP広告かどうか判定
                            item_options = item.get('itemOptions')
                            if not item_options or not isinstance(item_options, dict):
                                continue
                                
                            cpc_info = item_options.get('cpc')
                            if not cpc_info or not isinstance(cpc_info, dict):
                                continue
                            
                            # "type": "grp07rpp"がRPP広告の印
                            if cpc_info.get('type') == 'grp07rpp':
                                # RPP広告として商品情報を抽出
                                shop_info = item.get('shop')
                                if not shop_info or not isinstance(shop_info, dict):
                                    shop_info = {}
                                
                                original_url = item.get('originalItemUrl', '')
                                
                                # 商品名が意味のあるものかチェック（フィルタリング用）
                                product_name = item.get('name', '')
                                if not product_name or product_name in ['すべてのジャンル', '']:
                                    continue
                                
                                ad_data = {
                                    'product_name': product_name,
                                    'product_url': original_url,
                                    'price': item.get('price'),
                                    'shop_name': shop_info.get('urlCode', ''),  # shop.urlCodeから店舗IDを取得
                                    'image_url': '',
                                    'catchcopy': item.get('subtitle', ''),
                                    'position_on_page': len(ads) + 1,  # 有効な広告の連番
                                    'page_number': page,
                                    'product_id': ''
                                }
                                
                                # 画像URL
                                images = item.get('images', [])
                                if images and isinstance(images, list) and len(images) > 0:
                                    first_image = images[0]
                                    if isinstance(first_image, dict):
                                        ad_data['image_url'] = first_image.get('url', '')
                                
                                # originalItemUrlから商品IDを抽出
                                if original_url:
                                    url_match = re.search(r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)', original_url)
                                    if url_match:
                                        # shop.urlCodeが空の場合はURLから抽出
                                        if not ad_data['shop_name']:
                                            ad_data['shop_name'] = url_match.group(1)
                                        ad_data['product_id'] = url_match.group(2)
                                
                                ads.append(ad_data)
                                
                                logger.debug(f"RPP広告検出: {ad_data['position_on_page']}位 - {product_name[:30]} (店舗: {ad_data['shop_name']})")
                                position_on_page += 1
                        
                        initial_state_found = True
                        break
                        
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        logger.debug(f"__INITIAL_STATE__解析エラー: {e}")
                        continue
            
            # __INITIAL_STATE__が見つからない場合は従来のJSON-LD方式
            if not initial_state_found:
                logger.debug("__INITIAL_STATE__が見つからないため、JSON-LD方式にフォールバック")
                script_tags = soup.find_all('script', type='application/ld+json')
                for script in script_tags:
                    try:
                        data = json.loads(script.string)
                        if data.get('@type') == 'ItemList':
                            items = data.get('itemListElement', [])
                            for item in items:
                                product_data = item.get('item', {})
                                position = item.get('position')
                                
                                if product_data:
                                    # JSON-LDから基本情報を抽出
                                    ad_data = {
                                        'product_name': product_data.get('name', ''),
                                        'product_url': product_data.get('url', ''),
                                        'price': None,
                                        'shop_name': '',
                                        'image_url': '',
                                        'catchcopy': '',
                                        'position_on_page': position or position_on_page,
                                        'page_number': page,
                                        'product_id': ''
                                    }
                                    
                                    # 価格情報
                                    offers = product_data.get('offers', {})
                                    if offers.get('price'):
                                        ad_data['price'] = offers['price']
                                    
                                    # 画像URL
                                    images = product_data.get('image', [])
                                    if images:
                                        ad_data['image_url'] = images[0] if isinstance(images, list) else images
                                    
                                    # 商品URLから店舗IDと商品IDを抽出
                                    if ad_data['product_url']:
                                        # 楽天商品URLのパターン: https://item.rakuten.co.jp/shop_id/product_id/
                                        url_match = re.search(r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)', ad_data['product_url'])
                                        if url_match:
                                            ad_data['shop_name'] = url_match.group(1)
                                            ad_data['product_id'] = url_match.group(2)
                                    
                                    ads.append(ad_data)
                                    position_on_page += 1
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug(f"JSON-LD解析エラー: {e}")
                        continue
            
            # JSON-LDで見つからない場合は従来の方法を使用
            if not ads:
                # [PR]マークを持つ要素を直接検索
                pr_links = soup.find_all('a', class_=re.compile(r'title-link', re.I))
                for link in pr_links:
                    # [PR]テキストを含むかチェック
                    if '[PR]' in link.get_text():
                        ad_data = self._extract_product_info_from_link(link, page, position_on_page)
                        if ad_data:
                            ads.append(ad_data)
                            position_on_page += 1
                
                # 通常の商品コンテナからも検索
                product_containers = soup.find_all(['div', 'li'], class_=re.compile(r'searchresult|product|item', re.I))
                
                for container in product_containers:
                    # [PR]マークまたは「広告」「Ad」などの表示を探す
                    ad_marker = container.find(['span', 'div', 'p', 'a'], 
                                             text=re.compile(r'\[PR\]|広告|Ad|スポンサー', re.I))
                    
                    if not ad_marker:
                        # class名やdata属性でも判定
                        if not (container.get('class') and 
                               any('ad' in str(cls).lower() or 'pr' in str(cls).lower() 
                                   for cls in container.get('class', []))):
                            continue
                    
                    # 広告と判定された場合、商品情報を抽出
                    ad_data = self._extract_product_info(container, page, position_on_page)
                    
                    if ad_data:
                        ads.append(ad_data)
                        position_on_page += 1
            
            logger.debug(f"ページ {page} でRPP広告 {len(ads)} 件を発見")
            
            # 現在のページでstepmarketが含まれているかもログ出力
            stepmarket_found = [ad for ad in ads if 'stepmarket' in ad.get('shop_name', '').lower()]
            if stepmarket_found:
                logger.debug(f"stepmarket商品を {len(stepmarket_found)} 件発見")
                for ad in stepmarket_found:
                    logger.debug(f"  - {ad.get('position_on_page')}位: {ad.get('product_name', '')[:50]}")
            
            return ads
            
        except Exception as e:
            logger.error(f"RPP広告抽出エラー (page {page}): {e}")
            return []
    
    def _extract_product_info(self, container, page: int, position: int) -> Optional[Dict]:
        """
        商品コンテナから商品情報を抽出
        
        Args:
            container: 商品のHTMLコンテナ
            page: ページ番号
            position: ページ内位置
            
        Returns:
            商品データの辞書 または None
        """
        try:
            # 商品名を抽出
            product_name_elem = container.find(['a', 'h3', 'h2'], 
                                             class_=re.compile(r'title|name|product', re.I))
            if not product_name_elem:
                product_name_elem = container.find('a')
            
            if not product_name_elem:
                return None
            
            product_name = product_name_elem.get_text(strip=True)
            product_url = product_name_elem.get('href', '')
            
            # 相対URLを絶対URLに変換
            if product_url.startswith('/'):
                product_url = urljoin('https://search.rakuten.co.jp', product_url)
            
            # 価格を抽出
            price = None
            price_elem = container.find(['span', 'div'], 
                                      class_=re.compile(r'price|yen', re.I))
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d,]+', price_text.replace(',', ''))
                if price_match:
                    try:
                        price = int(price_match.group().replace(',', ''))
                    except ValueError:
                        pass
            
            # 店舗名を抽出
            shop_name = ""
            shop_elem = container.find(['span', 'div', 'a'], 
                                     class_=re.compile(r'shop|store|seller', re.I))
            if shop_elem:
                shop_name = shop_elem.get_text(strip=True)
            
            # 画像URLを抽出
            image_url = ""
            img_elem = container.find('img')
            if img_elem:
                image_url = img_elem.get('src') or img_elem.get('data-src', '')
                if image_url.startswith('/'):
                    image_url = urljoin('https://search.rakuten.co.jp', image_url)
            
            # キャッチコピーを抽出
            catchcopy = ""
            catchcopy_elem = container.find(['span', 'div'], 
                                          class_=re.compile(r'catch|description|subtitle', re.I))
            if catchcopy_elem:
                catchcopy = catchcopy_elem.get_text(strip=True)
            
            # 商品IDを抽出（URLから）
            product_id = ""
            if product_url:
                # 楽天商品URLのパターン: https://item.rakuten.co.jp/shop_id/product_id/
                url_match = re.search(r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)', product_url)
                if url_match:
                    product_id = url_match.group(2)
            
            return {
                'product_name': product_name,
                'product_url': product_url,
                'product_id': product_id,
                'price': price,
                'shop_name': shop_name,
                'image_url': image_url,
                'catchcopy': catchcopy,
                'position_on_page': position,
                'page_number': page,
                'collected_at': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"商品情報抽出エラー: {e}")
            return None
    
    def _extract_product_info_from_link(self, link, page: int, position: int) -> Optional[Dict]:
        """
        [PR]リンクから商品情報を抽出
        
        Args:
            link: [PR]リンク要素
            page: ページ番号
            position: ページ内位置
            
        Returns:
            商品データの辞書 または None
        """
        try:
            product_name = link.get_text(strip=True).replace('[PR]', '').strip()
            product_url = link.get('href', '')
            
            # 相対URLを絶対URLに変換
            if product_url.startswith('/'):
                product_url = urljoin('https://search.rakuten.co.jp', product_url)
            
            # 商品IDを抽出（URLから）
            product_id = ""
            shop_name = ""
            if product_url:
                url_match = re.search(r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)', product_url)
                if url_match:
                    shop_name = url_match.group(1)
                    product_id = url_match.group(2)
            
            if not product_name or not product_url:
                return None
            
            return {
                'product_name': product_name,
                'product_url': product_url,
                'product_id': product_id,
                'price': None,
                'shop_name': shop_name,
                'image_url': '',
                'catchcopy': '',
                'position_on_page': position,
                'page_number': page,
                'collected_at': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"[PR]リンク商品情報抽出エラー: {e}")
            return None
    
    def find_own_product_rank(self, ads: List[Dict], target_shop_id: str, 
                             target_product_url: str = None) -> Optional[int]:
        """
        広告リストから自社商品の順位を検索
        
        Args:
            ads: 広告データのリスト
            target_shop_id: 対象店舗ID
            target_product_url: 対象商品URL（任意）
            
        Returns:
            順位 または None（見つからない場合）
        """
        for ad in ads:
            # 店舗IDで判定
            if target_shop_id.lower() in ad.get('shop_name', '').lower():
                return ad.get('rank')
            
            # 商品URLでも判定（提供されている場合）
            if target_product_url and ad.get('product_url'):
                if target_product_url in ad['product_url'] or ad['product_url'] in target_product_url:
                    return ad.get('rank')
        
        return None
    
    def close(self):
        """セッションを閉じる"""
        if hasattr(self, 'session'):
            self.session.close()


def scrape_rpp_ranking(keyword: str, target_shop_id: str, 
                      target_product_url: str = None, max_pages: int = 3) -> Dict:
    """
    RPP広告順位を検索する便利関数
    
    Args:
        keyword: 検索キーワード
        target_shop_id: 対象店舗ID
        target_product_url: 対象商品URL（任意）
        max_pages: 最大検索ページ数（デフォルト3ページ、最大15位まで）
        
    Returns:
        検索結果の辞書
    """
    scraper = RPPScraper()
    
    try:
        start_time = time.time()
        
        # RPP広告を検索
        ads, success = scraper.search_rpp_ads(keyword, max_pages)
        
        execution_time = time.time() - start_time
        
        if not success:
            return {
                'success': False,
                'rank': None,
                'is_found': False,
                'total_ads': 0,
                'ads': [],
                'execution_time': execution_time,
                'error': 'スクレイピングに失敗しました'
            }
        
        # 自社商品の順位を検索
        own_rank = scraper.find_own_product_rank(ads, target_shop_id, target_product_url)
        
        return {
            'success': True,
            'rank': own_rank,
            'is_found': own_rank is not None,
            'total_ads': len(ads),
            'ads': ads,
            'execution_time': execution_time,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"RPP順位検索エラー: {e}")
        return {
            'success': False,
            'rank': None,
            'is_found': False,
            'total_ads': 0,
            'ads': [],
            'execution_time': 0,
            'error': str(e)
        }
    finally:
        scraper.close()