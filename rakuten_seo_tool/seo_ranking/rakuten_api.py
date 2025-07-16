import requests
import time
import logging
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode
from django.conf import settings
from .models import SearchLog

logger = logging.getLogger(__name__)


class RakutenSearchAPI:
    """楽天市場商品検索API"""
    
    BASE_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
    GENRE_URL = "https://app.rakuten.co.jp/services/api/IchibaGenre/Search/20120723"
    TAG_URL = "https://app.rakuten.co.jp/services/api/IchibaTag/Search/20140222"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.RAKUTEN_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Rakuten SEO Tool/1.0'
        })
        # キャッシュ
        self._genre_cache = {}
        self._tag_cache = {}
    
    def _process_image_url(self, image_url: str, size: str = "300x300") -> str:
        """画像URLのサイズパラメータを調整"""
        if not image_url:
            return image_url
        
        # ?_ex=128x128のようなサイズパラメータを削除または変更
        import re
        
        # 既存のサイズパラメータを削除
        processed_url = re.sub(r'\?_ex=\d+x\d+', '', image_url)
        
        # 新しいサイズパラメータを追加（オプション）
        if size and size != "original":
            if '?' in processed_url:
                processed_url += f'&_ex={size}'
            else:
                processed_url += f'?_ex={size}'
        
        return processed_url
    
    def _sanitize_keyword(self, keyword: str) -> str:
        """キーワードを楽天API用にサニタイズ"""
        # 基本的なサニタイズ処理
        sanitized = keyword.strip()
        
        # 連続する空白を単一の空白に変換
        import re
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # 楽天APIで問題となる可能性のある文字をチェック・置換
        words = sanitized.split()
        processed_words = []
        for word in words:
            # 単体の小文字lは問題となることがあるため、より具体的に
            if word.lower() == 'l':
                processed_words.append('Lサイズ')  # より具体的な表現に
            elif word.lower() == 'm':
                processed_words.append('Mサイズ')
            elif word.lower() == 's':
                processed_words.append('Sサイズ')
            # 1文字のアルファベットの場合は全て大文字に
            elif len(word) == 1 and word.isalpha():
                processed_words.append(word.upper())
            else:
                processed_words.append(word)
        
        result = ' '.join(processed_words)
        logger.info(f"Keyword sanitized: '{keyword}' -> '{result}'")
        return result
    
    def get_genre_name(self, genre_id: str) -> str:
        """ジャンルIDからジャンル名を取得"""
        if not genre_id:
            return ''
        
        # キャッシュから取得
        if genre_id in self._genre_cache:
            return self._genre_cache[genre_id]
        
        try:
            params = {
                'format': 'json',
                'applicationId': self.api_key,
                'genreId': genre_id
            }
            
            response = self.session.get(self.GENRE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'current' in data and data['current']:
                genre_name = data['current'].get('genreName', '')
                # キャッシュに保存
                self._genre_cache[genre_id] = genre_name
                return genre_name
                
        except Exception as e:
            logger.error(f"Failed to get genre name for ID {genre_id}: {e}")
        
        return genre_id  # 取得失敗時はIDをそのまま返す
    
    def get_multiple_tag_names(self, tag_ids_list, genre_id: str = '') -> dict:
        """複数のタグIDからタグ名を一括取得"""
        if not tag_ids_list:
            return {}
        
        # リスト形式に変換
        if isinstance(tag_ids_list, str):
            if ',' in tag_ids_list:
                tag_ids = [tag_id.strip() for tag_id in tag_ids_list.split(',') if tag_id.strip()]
            else:
                tag_ids = [tag_ids_list] if tag_ids_list else []
        else:
            tag_ids = [str(tag_id) for tag_id in tag_ids_list if str(tag_id)]
        
        if not tag_ids:
            return {}
        
        # 最大10個まで制限
        tag_ids = tag_ids[:10]
        
        # 未キャッシュのタグIDを特定
        uncached_tag_ids = []
        result = {}
        
        for tag_id in tag_ids:
            cache_key = f"{tag_id}_{genre_id}" if genre_id else tag_id
            if cache_key in self._tag_cache:
                result[tag_id] = self._tag_cache[cache_key]
            else:
                uncached_tag_ids.append(tag_id)
        
        # 未キャッシュのタグIDがある場合はAPI呼び出し
        if uncached_tag_ids:
            # 方法1: ジャンルIDでタグ一覧を取得（ジャンルIDがある場合）
            if genre_id:
                result.update(self._get_tags_by_genre(genre_id, uncached_tag_ids))
            
            # 方法2: 個別のタグIDで取得（残ったタグID）
            remaining_tag_ids = [tid for tid in uncached_tag_ids if tid not in result]
            if remaining_tag_ids:
                result.update(self._get_tags_by_tag_ids(remaining_tag_ids, genre_id))
        
        return result
    
    def _get_tags_by_genre(self, genre_id: str, target_tag_ids: list) -> dict:
        """ジャンルIDでタグ一覧を取得（注意：楽天タグAPIにはgenreIdパラメータは存在しない）"""
        result = {}
        logger.info(f"Skipping genre-based tag retrieval - Rakuten Tag API doesn't support genreId parameter")
        return result
    
    def _get_tags_by_tag_ids(self, tag_ids: list, genre_id: str = '') -> dict:
        """個別のタグIDでタグ情報を取得"""
        result = {}
        
        # 最大10個ずつ処理
        for i in range(0, len(tag_ids), 10):
            batch_tag_ids = tag_ids[i:i+10]
            
            try:
                # API制限対策：1.5秒待機（最初のバッチ以外）
                if i > 0:
                    time.sleep(1.5)
                
                params = {
                    'format': 'json',
                    'applicationId': self.api_key,
                    'tagId': ','.join(batch_tag_ids)
                }
                
                response = self.session.get(self.TAG_URL, params=params, timeout=10)
                
                # 429エラー（Too Many Requests）のハンドリング
                if response.status_code == 429:
                    logger.warning(f"Tag API rate limit hit for tagIds {batch_tag_ids}, waiting 3 seconds...")
                    time.sleep(3)
                    # 1回だけリトライ
                    response = self.session.get(self.TAG_URL, params=params, timeout=10)
                
                # 404エラー（タグが存在しない）のハンドリング
                if response.status_code == 404:
                    logger.warning(f"Tag API returned 404 for tagIds {batch_tag_ids} - tags may not exist")
                    # 404の場合は元のIDを返して続行
                    for tag_id in batch_tag_ids:
                        cache_key = f"{tag_id}_{genre_id}" if genre_id else tag_id
                        self._tag_cache[cache_key] = tag_id
                        result[tag_id] = tag_id
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"Tag API (by tagIds) response keys: {list(data.keys())}")
                logger.info(f"Tag API (by tagIds) FULL response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                # デバッグ用：レスポンス構造を詳細に確認
                if 'tagGroup' in data:
                    logger.info(f"Found tagGroup structure")
                    if 'tags' in data['tagGroup']:
                        logger.info(f"Found tags in tagGroup: {data['tagGroup']['tags']}")
                else:
                    logger.info(f"No tagGroup found, checking other structures...")
                
                # レスポンス構造を解析
                self._parse_tag_response(data, batch_tag_ids, result, genre_id)
                
            except Exception as e:
                logger.error(f"Failed to get tags by tagIds {batch_tag_ids}: {e}")
                # エラー時は元のIDを返す
                for tag_id in batch_tag_ids:
                    result[tag_id] = tag_id
        
        return result
    
    def _parse_tag_response(self, data: dict, target_tag_ids: list, result: dict, genre_id: str = ''):
        """タグAPIレスポンスを解析してタグ名を抽出"""
        try:
            logger.info(f"Parsing tag response for target IDs: {target_tag_ids}")
            
            # 様々なレスポンス構造に対応
            tags_found = []
            
            # パターン1: tagGroup -> tags -> tag (公式ドキュメント)
            if 'tagGroup' in data and data['tagGroup']:
                tag_group = data['tagGroup']
                logger.info(f"Found tagGroup: {tag_group}")
                
                if 'tags' in tag_group and tag_group['tags']:
                    tags_data = tag_group['tags']
                    
                    # tags内のtagを抽出
                    if 'tag' in tags_data:
                        tag_items = tags_data['tag']
                        if isinstance(tag_items, list):
                            tags_found.extend(tag_items)
                        else:
                            tags_found.append(tag_items)
                    elif isinstance(tags_data, list):
                        tags_found.extend(tags_data)
            
            # パターン2: 直接tags配列
            elif 'tags' in data and data['tags']:
                if isinstance(data['tags'], list):
                    tags_found.extend(data['tags'])
                elif 'tag' in data['tags']:
                    tag_items = data['tags']['tag']
                    if isinstance(tag_items, list):
                        tags_found.extend(tag_items)
                    else:
                        tags_found.append(tag_items)
            
            # パターン3: 他の可能な構造
            else:
                # レスポンス全体をチェックして、tagIdとtagNameを含むオブジェクトを探す
                def find_tags_recursive(obj, path=""):
                    found = []
                    if isinstance(obj, dict):
                        if 'tagId' in obj and 'tagName' in obj:
                            found.append(obj)
                            logger.info(f"Found tag at {path}: {obj}")
                        else:
                            for key, value in obj.items():
                                found.extend(find_tags_recursive(value, f"{path}.{key}"))
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            found.extend(find_tags_recursive(item, f"{path}[{i}]"))
                    return found
                
                tags_found = find_tags_recursive(data)
                logger.info(f"Recursive search found {len(tags_found)} tags")
            
            # 見つかったタグを処理
            logger.info(f"Processing {len(tags_found)} found tags")
            for tag in tags_found:
                self._extract_tag_info(tag, target_tag_ids, result, genre_id)
            
            # 見つからなかったタグIDは元のIDを返す
            for tag_id in target_tag_ids:
                if tag_id not in result:
                    cache_key = f"{tag_id}_{genre_id}" if genre_id else tag_id
                    self._tag_cache[cache_key] = tag_id
                    result[tag_id] = tag_id
                    logger.warning(f"Tag ID {tag_id} not found in response, using ID as name")
                    
        except Exception as e:
            logger.error(f"Error parsing tag response: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # エラー時は元のIDを返す
            for tag_id in target_tag_ids:
                if tag_id not in result:
                    result[tag_id] = tag_id
    
    def _extract_tag_info(self, tag: dict, target_tag_ids: list, result: dict, genre_id: str = ''):
        """タグ情報を抽出してresultに格納"""
        tag_id = str(tag.get('tagId', ''))
        tag_name = tag.get('tagName', '')
        
        if tag_id in target_tag_ids and tag_name:
            cache_key = f"{tag_id}_{genre_id}" if genre_id else tag_id
            self._tag_cache[cache_key] = tag_name
            result[tag_id] = tag_name
            logger.info(f"Found tag: {tag_id} -> {tag_name}")
    
    def get_tag_names(self, tag_ids_list, genre_id: str = '') -> str:
        """タグIDリストからタグ名を取得"""
        if not tag_ids_list:
            return ''
        
        # 一括でタグ名を取得（ジャンルIDも渡す）
        tag_name_dict = self.get_multiple_tag_names(tag_ids_list, genre_id)
        
        # リスト形式に変換
        if isinstance(tag_ids_list, str):
            if ',' in tag_ids_list:
                tag_ids = [tag_id.strip() for tag_id in tag_ids_list.split(',') if tag_id.strip()]
            else:
                tag_ids = [tag_ids_list] if tag_ids_list else []
        else:
            tag_ids = [str(tag_id) for tag_id in tag_ids_list if str(tag_id)]
        
        # タグ名のリストを作成
        tag_names = []
        for tag_id in tag_ids:
            tag_name = tag_name_dict.get(tag_id, tag_id)
            tag_names.append(tag_name)
        
        return ', '.join(tag_names)
    
    def search_products(self, keyword: str, page: int = 1, per_page: int = 30) -> Dict:
        """楽天市場で商品を検索"""
        # キーワードをサニタイズ
        sanitized_keyword = self._sanitize_keyword(keyword)
        
        params = {
            'format': 'json',
            'keyword': sanitized_keyword,
            'applicationId': self.api_key,
            'page': page,
            'hits': per_page,
            'sort': 'standard',  # 標準順
            'imageFlag': 1,      # 商品画像URL取得のため
            'availability': 1,   # 在庫のある商品のみ
        }
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            
            # ステータスコードをチェックしてエラー詳細を取得
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    logger.error(f"Rakuten API 400 error for keyword '{keyword}': {error_data}")
                    # 楽天APIの400エラーの場合、空の結果を返す
                    return {'Items': [], 'hits': 0, 'page': page, 'first': 1, 'last': 1}
                except:
                    logger.error(f"Rakuten API 400 error for keyword '{keyword}': {response.text}")
                    return {'Items': [], 'hits': 0, 'page': page, 'first': 1, 'last': 1}
            
            response.raise_for_status()
            
            data = response.json()
            
            # レスポンスの構造を確認
            if 'Items' not in data:
                logger.error(f"API response missing 'Items' field: {data}")
                return {'Items': [], 'hits': 0, 'page': page, 'first': 1, 'last': 1}
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            # ネットワークエラーの場合も空の結果を返す
            return {'Items': [], 'hits': 0, 'page': page, 'first': 1, 'last': 1}
        except Exception as e:
            logger.error(f"Unexpected error in search_products: {e}")
            raise
    
    def find_product_rank(self, keyword: str, target_shop_id: str, target_product_id: str = None, 
                         target_product_url: str = None, max_pages: int = 10) -> Tuple[Optional[int], List[Dict], int]:
        """
        指定されたキーワードで商品の順位を検索
        
        Args:
            keyword: 検索キーワード
            target_shop_id: 対象店舗ID
            target_product_id: 対象商品ID（オプション）
            target_product_url: 対象商品URL（オプション）
            max_pages: 最大検索ページ数（デフォルト10ページ = 300商品）
            
        Returns:
            Tuple[順位または None, 上位10商品のリスト, 総商品数]
        """
        start_time = time.time()
        found_rank = None
        all_products = []
        top_products = []
        total_count = 0
        
        try:
            for page in range(1, max_pages + 1):
                logger.info(f"Searching page {page} for keyword: {keyword}")
                
                # APIリクエスト制限を考慮して少し待機
                if page > 1:
                    time.sleep(0.5)
                
                try:
                    search_result = self.search_products(keyword, page=page, per_page=30)
                    
                    # 最初のページで総商品数を取得
                    if page == 1:
                        # 楽天APIの総商品数フィールドを確認
                        total_count = (search_result.get('count') or 
                                     search_result.get('hits') or 
                                     search_result.get('totalCount') or 
                                     search_result.get('pageCount', 0) * 30)  # ページ数から推定
                        logger.info(f"Total count from API: {total_count} (raw response keys: {list(search_result.keys())})")
                    
                    if not search_result.get('Items'):
                        logger.warning(f"No items found on page {page}")
                        break
                    
                    # 商品を処理
                    for item_index, item_data in enumerate(search_result['Items']):
                        item = item_data.get('Item', {})
                        
                        # 現在の順位を計算
                        current_rank = (page - 1) * 30 + item_index + 1
                        
                        # 自社商品かどうかを先にチェック
                        is_match = False
                        
                        # 店舗IDでマッチング
                        if item.get('shopCode') == target_shop_id:
                            is_match = True
                        
                        # 商品IDでマッチング（指定されている場合）
                        if target_product_id and item.get('itemCode') == target_product_id:
                            is_match = True
                        
                        # 商品URLでマッチング（指定されている場合）
                        if target_product_url and item.get('itemUrl') == target_product_url:
                            is_match = True
                        
                        # 商品情報を構築（is_own_productフラグを含む）
                        # 楽天APIの正確なフィールド名を使用
                        genre_id = item.get('genreId', '')
                        # タグAPIを無効化（パフォーマンス改善のため）
                        # tag_ids = item.get('tagIds', [])
                        
                        product_info = {
                            'rank': current_rank,
                            'product_name': item.get('itemName', ''),
                            'catchcopy': item.get('catchcopy', ''),  # キャッチコピー
                            'product_url': item.get('itemUrl', ''),
                            'product_id': item.get('itemCode', ''),
                            'shop_name': item.get('shopName', ''),
                            'shop_id': item.get('shopCode', ''),
                            'price': item.get('itemPrice', 0),
                            'review_count': item.get('reviewCount', 0),
                            'review_average': item.get('reviewAverage', 0),
                            'image_url': self._process_image_url(
                                item.get('mediumImageUrls', [{}])[0].get('imageUrl', '') if item.get('mediumImageUrls') else '',
                                size="original"  # オリジナルサイズまたは大きなサイズを使用
                            ),
                            'point_rate': item.get('pointRate', 1),  # ポイント倍率
                            'genre_id': genre_id,     # ジャンルID
                            'genre_name': self.get_genre_name(genre_id),  # ジャンル名
                            'tag_ids': '',  # タグAPIを無効化
                            'tag_names': '',  # タグAPIを無効化
                            'product_spec': item.get('itemCaption', ''),  # 商品説明
                            'is_own_product': is_match
                        }
                        
                        # デバッグ用：APIから取得した全データをログ出力
                        if current_rank <= 3:  # 上位3商品のみログ出力
                            logger.info(f"Rank {current_rank} API data keys: {list(item.keys())}")
                            logger.info(f"Rank {current_rank} full item data: {item}")
                            logger.info(f"Rank {current_rank} catchcopy: {item.get('catchcopy', 'NOT_FOUND')}")
                            logger.info(f"Rank {current_rank} pointRate: {item.get('pointRate', 'NOT_FOUND')}")
                            logger.info(f"Rank {current_rank} genreId: {item.get('genreId', 'NOT_FOUND')}")
                            logger.info(f"Rank {current_rank} itemCaption: {item.get('itemCaption', 'NOT_FOUND')}")
                            # タグAPIを無効化したため、タグ関連のログも削除
                            # logger.info(f"Rank {current_rank} tagIds: {item.get('tagIds', 'NOT_FOUND')}")
                            # logger.info(f"Rank {current_rank} tagNames: {item.get('tagNames', 'NOT_FOUND')}")
                        
                        all_products.append(product_info)
                        
                        # 上位10商品を保存
                        if len(top_products) < 10:
                            top_products.append(product_info)
                            logger.debug(f"Added product to top 10: rank={current_rank}, is_own={is_match}, name={product_info['product_name'][:30]}...")
                        
                        # 自社商品が見つかった場合
                        if is_match:
                            # 最高順位（最も小さい数値）を記録
                            if found_rank is None or current_rank < found_rank:
                                found_rank = current_rank
                                logger.info(f"Found target product at rank {current_rank} (new best rank)")
                            else:
                                logger.info(f"Found target product at rank {current_rank} (current best: {found_rank})")
                        
                        # 上位10件を収集した場合は検索終了（自社商品発見とは独立）
                        if len(top_products) >= 10:
                            execution_time = time.time() - start_time
                            logger.info(f"Collected 10 top products, ending search. Found rank: {found_rank}")
                            return found_rank, top_products, total_count
                    
                    # 検索結果が30件未満の場合は最後のページ
                    if len(search_result.get('Items', [])) < 30:
                        logger.info(f"Reached end of results at page {page}")
                        break
                
                except Exception as e:
                    logger.error(f"Error processing page {page}: {e}")
                    continue
            
            execution_time = time.time() - start_time
            logger.info(f"Search completed in {execution_time:.2f}s, checked {len(all_products)} products")
            logger.info(f"Collected {len(top_products)} top products, found_rank={found_rank}, total_count={total_count}")
            
            return found_rank, top_products, total_count
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Search failed after {execution_time:.2f}s: {e}")
            return None, [], 0
    
    def get_product_details(self, product_url: str) -> Dict:
        """商品詳細情報を取得"""
        # 楽天商品詳細APIは別途実装が必要
        # 現在は基本的な情報のみ返す
        return {
            'product_url': product_url,
            'details': 'Product details would be fetched here'
        }


class RakutenSearchManager:
    """楽天検索管理クラス"""
    
    def __init__(self, user):
        self.user = user
        self.api = RakutenSearchAPI()
    
    def execute_keyword_search(self, keyword_obj) -> 'RankingResult':
        """キーワード検索を実行して結果を保存"""
        from .models import RankingResult, TopProduct
        
        start_time = time.time()
        
        # 検索ログを作成
        search_log = SearchLog.objects.create(
            user=self.user,
            keyword=keyword_obj.keyword,
            success=False  # 初期値
        )
        
        try:
            # 楽天市場で検索実行
            found_rank, top_products, total_count = self.api.find_product_rank(
                keyword=keyword_obj.keyword,
                target_shop_id=keyword_obj.rakuten_shop_id,
                target_product_id=keyword_obj.target_product_id,
                target_product_url=keyword_obj.target_product_url,
                max_pages=10  # 300商品まで検索
            )
            
            # 結果を保存
            ranking_result = RankingResult.objects.create(
                keyword=keyword_obj,
                rank=found_rank,
                total_results=len(top_products),
                total_products=total_count,
                is_found=found_rank is not None
            )
            
            # 上位10商品を保存
            for product_data in top_products:
                TopProduct.objects.create(
                    ranking_result=ranking_result,
                    rank=product_data['rank'],
                    product_name=product_data['product_name'],
                    catchcopy=product_data.get('catchcopy', ''),
                    product_url=product_data['product_url'],
                    product_id=product_data['product_id'],
                    shop_name=product_data['shop_name'],
                    shop_id=product_data['shop_id'],
                    price=product_data['price'],
                    review_count=product_data['review_count'],
                    review_average=product_data['review_average'],
                    image_url=product_data['image_url'],
                    point_rate=product_data.get('point_rate', 1),
                    genre_id=product_data.get('genre_id', ''),
                    genre_name=product_data.get('genre_name', ''),
                    tag_ids=product_data.get('tag_ids', ''),
                    tag_names=product_data.get('tag_names', ''),
                    product_spec=product_data.get('product_spec', ''),
                    is_own_product=product_data['is_own_product']
                )
            
            # 検索ログを更新
            execution_time = time.time() - start_time
            search_log.execution_time = execution_time
            search_log.pages_checked = 10  # 最大10ページ
            search_log.products_found = len(top_products)
            search_log.success = True
            search_log.save()
            
            logger.info(f"Search completed successfully for keyword: {keyword_obj.keyword}")
            return ranking_result
            
        except Exception as e:
            # エラーログを更新
            execution_time = time.time() - start_time
            search_log.execution_time = execution_time
            search_log.error_details = str(e)
            search_log.save()
            
            # エラー結果を保存
            ranking_result = RankingResult.objects.create(
                keyword=keyword_obj,
                rank=None,
                total_results=0,
                is_found=False,
                error_message=str(e)
            )
            
            logger.error(f"Search failed for keyword: {keyword_obj.keyword}, error: {e}")
            raise