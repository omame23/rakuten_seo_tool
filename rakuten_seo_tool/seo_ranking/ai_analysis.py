"""
AI分析ユーティリティ
Claude APIを使用して商品データを分析し、改善提案を生成する
"""

import json
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class ClaudeAnalyzer:
    """Claude APIを使用した商品分析クラス"""
    
    def __init__(self):
        self.api_key = settings.CLAUDE_API_KEY
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
    
    def analyze_ranking_data(self, keyword: str, own_product_data: Dict, competitor_data: List[Dict]) -> Dict[str, Any]:
        """
        検索順位データを分析し、改善提案を生成
        
        Args:
            keyword: 検索キーワード
            own_product_data: 自社商品データ（順位情報含む）
            competitor_data: 競合商品データのリスト（上位10位）
            
        Returns:
            分析結果を含む辞書
        """
        try:
            # 分析用プロンプトを生成
            analysis_prompt = self._create_analysis_prompt(keyword, own_product_data, competitor_data)
            
            # Claude APIに分析を依頼
            response = self._call_claude_api(analysis_prompt)
            
            if response:
                # 分析結果をパース
                analysis_result = self._parse_analysis_response(response)
                return {
                    'success': True,
                    'analysis': analysis_result,
                    'error': None
                }
            else:
                # API呼び出し失敗時もフォールバック分析を提供
                fallback_analysis = self._get_fallback_analysis(keyword, own_product_data, competitor_data)
                return {
                    'success': False,
                    'analysis': fallback_analysis,
                    'error': 'AI分析が利用できません（APIクレジット不足またはサービス一時停止）'
                }
                
        except Exception as e:
            logger.error(f"AI分析エラー: {e}")
            # エラー時もフォールバック分析を提供
            fallback_analysis = self._get_fallback_analysis(keyword, own_product_data, competitor_data)
            return {
                'success': False,
                'analysis': fallback_analysis,
                'error': f'AI分析が利用できません（詳細分析にはクレジット追加が必要）'
            }
    
    def _create_analysis_prompt(self, keyword: str, own_product: Dict, competitors: List[Dict]) -> str:
        """分析用プロンプトを作成"""
        
        # 自社商品の情報
        own_rank = own_product.get('rank', '圏外')
        own_name = own_product.get('product_name', '')
        own_price = own_product.get('price', 0)
        own_catchcopy = own_product.get('catchcopy', '')
        own_review_count = own_product.get('review_count', 0)
        own_review_average = own_product.get('review_average', 0)
        
        # 競合商品の要約統計
        competitor_prices = [c.get('price', 0) for c in competitors if c.get('price')]
        avg_price = sum(competitor_prices) / len(competitor_prices) if competitor_prices else 0
        
        competitor_reviews = [c.get('review_count', 0) for c in competitors]
        avg_reviews = sum(competitor_reviews) / len(competitor_reviews) if competitor_reviews else 0
        
        # 上位3位の商品情報
        top3_products = competitors[:3]
        top3_info = ""
        for i, product in enumerate(top3_products, 1):
            top3_info += f"""
{i}位: {product.get('product_name', '不明')}
価格: ¥{product.get('price', 0):,}
キャッチコピー: {product.get('catchcopy', 'なし')}
レビュー: {product.get('review_count', 0)}件 (平均{product.get('review_average', 0)})
"""
        
        prompt = f"""
あなたは楽天市場のSEO専門家です。以下のデータを分析して、具体的で実行可能な改善提案を提供してください。

## 検索キーワード
"{keyword}"

## 自社商品の現状
- 検索順位: {own_rank}位
- 商品名: {own_name}
- 価格: ¥{own_price:,}
- キャッチコピー: {own_catchcopy}
- レビュー: {own_review_count}件 (平均{own_review_average})

## 競合分析（上位10位の統計）
- 平均価格: ¥{avg_price:,.0f}
- 平均レビュー数: {avg_reviews:.1f}件

## 上位3位の商品詳細
{top3_info}

## 分析してほしい内容
以下の形式でJSON形式の分析結果を返してください：

```json
{{
  "overall_assessment": "自社商品の現在の市場ポジションの総合評価（100文字以内）",
  "competitive_analysis": {{
    "price_competitiveness": "価格競争力の分析（50文字以内）",
    "title_analysis": "商品名・キーワード最適化の分析（50文字以内）",
    "review_analysis": "レビュー状況の分析（50文字以内）"
  }},
  "improvement_suggestions": [
    {{
      "category": "商品名最適化",
      "priority": "高",
      "suggestion": "具体的な改善提案（100文字以内）",
      "expected_impact": "期待される効果（50文字以内）"
    }},
    {{
      "category": "価格戦略",
      "priority": "中",
      "suggestion": "具体的な改善提案（100文字以内）",
      "expected_impact": "期待される効果（50文字以内）"
    }},
    {{
      "category": "キャッチコピー",
      "priority": "中",
      "suggestion": "具体的な改善提案（100文字以内）",
      "expected_impact": "期待される効果（50文字以内）"
    }}
  ],
  "keyword_optimization": {{
    "current_keyword_usage": "現在のキーワード使用状況の評価",
    "recommended_keywords": ["推奨キーワード1", "推奨キーワード2", "推奨キーワード3"],
    "keyword_placement_tips": "キーワード配置のコツ（100文字以内）"
  }},
  "next_steps": [
    "優先順位順の具体的な次のステップ1（50文字以内）",
    "優先順位順の具体的な次のステップ2（50文字以内）",
    "優先順位順の具体的な次のステップ3（50文字以内）"
  ]
}}
```

分析は楽天市場のSEOルールに基づいて、実用的で実行しやすい提案を心がけてください。
"""
        
        return prompt
    
    def _call_claude_api(self, prompt: str) -> Optional[str]:
        """Claude APIを呼び出し"""
        try:
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data['content'][0]['text']
            else:
                logger.error(f"Claude API エラー: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Claude API リクエストエラー: {e}")
            return None
        except Exception as e:
            logger.error(f"Claude API 予期しないエラー: {e}")
            return None
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Claude APIの応答をパース"""
        try:
            # JSONブロックを抽出
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                # JSONブロックが見つからない場合、全体をJSONとして解析を試行
                return json.loads(response_text)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
            logger.error(f"レスポンステキスト: {response_text}")
            
            # JSONの解析に失敗した場合、デフォルトの分析結果を返す
            return {
                "overall_assessment": "AI分析の解析に失敗しました。手動で確認をお願いします。",
                "competitive_analysis": {
                    "price_competitiveness": "分析データが不足しています",
                    "title_analysis": "分析データが不足しています", 
                    "review_analysis": "分析データが不足しています"
                },
                "improvement_suggestions": [
                    {
                        "category": "商品名最適化",
                        "priority": "高",
                        "suggestion": "キーワードを含む商品名への変更を検討してください",
                        "expected_impact": "検索順位向上"
                    }
                ],
                "keyword_optimization": {
                    "current_keyword_usage": "データ解析エラー",
                    "recommended_keywords": ["検索キーワード"],
                    "keyword_placement_tips": "商品名とキャッチコピーにキーワードを配置"
                },
                "next_steps": [
                    "商品名の見直し",
                    "キャッチコピーの改善",
                    "価格戦略の検討"
                ]
            }
        except Exception as e:
            logger.error(f"予期しない解析エラー: {e}")
            # 解析エラー時は基本的なフォールバック分析を返す
            return {
                "overall_assessment": "AI分析の解析に失敗しましたが、手動で確認を行うことをお勧めします。",
                "competitive_analysis": {
                    "price_competitiveness": "データ解析エラーが発生しました",
                    "title_analysis": "データ解析エラーが発生しました", 
                    "review_analysis": "データ解析エラーが発生しました"
                },
                "improvement_suggestions": [
                    {
                        "category": "基本最適化",
                        "priority": "高",
                        "suggestion": "商品名にメインキーワードを含めることを確認してください",
                        "expected_impact": "検索可視性向上"
                    }
                ],
                "keyword_optimization": {
                    "current_keyword_usage": "データ解析エラー",
                    "recommended_keywords": [],
                    "keyword_placement_tips": "商品名とキャッチコピーにキーワードを配置"
                },
                "next_steps": [
                    "AI分析の再実行",
                    "手動での競合分析",
                    "キーワード戦略の見直し"
                ]
            }
    
    def _get_fallback_analysis(self, keyword: str = "", own_product: Dict = None, competitors: List[Dict] = None) -> Dict[str, Any]:
        """AI分析が失敗した場合のフォールバック分析（実際のデータを使用した基本分析）"""
        
        # デフォルト値の設定
        if own_product is None:
            own_product = {}
        if competitors is None:
            competitors = []
            
        # 基本統計の計算
        competitor_prices = [c.get('price', 0) for c in competitors if c.get('price', 0) > 0]
        avg_price = sum(competitor_prices) / len(competitor_prices) if competitor_prices else 0
        
        competitor_reviews = [c.get('review_count', 0) for c in competitors if c.get('review_count', 0) > 0]
        avg_review_count = sum(competitor_reviews) / len(competitor_reviews) if competitor_reviews else 0
        
        competitor_ratings = [c.get('review_average', 0) for c in competitors if c.get('review_average', 0) > 0]
        avg_rating = sum(competitor_ratings) / len(competitor_ratings) if competitor_ratings else 0
        
        own_rank = own_product.get('rank', '圏外')
        own_price = own_product.get('price', 0)
        own_reviews = own_product.get('review_count', 0)
        own_rating = own_product.get('review_average', 0)
        
        # 価格競争力の分析
        price_analysis = "データ不足"
        if own_price > 0 and avg_price > 0:
            if own_price < avg_price * 0.8:
                price_analysis = "競合より安価で価格競争力あり"
            elif own_price > avg_price * 1.2:
                price_analysis = "競合より高価、価格見直しを検討"
            else:
                price_analysis = "競合と同程度の価格帯"
        
        # レビュー分析
        review_analysis = "データ不足"
        if own_reviews > 0 and avg_review_count > 0:
            if own_reviews < avg_review_count * 0.5:
                review_analysis = "レビュー数が少ない、顧客満足度向上が必要"
            elif own_reviews > avg_review_count * 1.5:
                review_analysis = "レビュー数が豊富で信頼性が高い"
            else:
                review_analysis = "競合と同程度のレビュー数"
        
        # 商品名分析
        title_analysis = "キーワード最適化の確認が必要"
        if keyword and own_product.get('product_name'):
            keywords_in_title = sum(1 for kw in keyword.split() if kw.lower() in own_product['product_name'].lower())
            if keywords_in_title > 0:
                title_analysis = f"検索キーワードが{keywords_in_title}個含まれています"
            else:
                title_analysis = "検索キーワードが商品名に含まれていません"
        
        # 改善提案の生成
        suggestions = []
        
        # 順位による提案
        if isinstance(own_rank, int):
            if own_rank > 10:
                suggestions.append({
                    "category": "順位改善",
                    "priority": "高",
                    "suggestion": "現在の順位が低いため、商品名とキャッチコピーの最適化が急務です",
                    "expected_impact": "検索順位の大幅向上"
                })
            elif own_rank > 5:
                suggestions.append({
                    "category": "順位向上",
                    "priority": "中",
                    "suggestion": "上位5位以内を目指して商品の差別化を図りましょう",
                    "expected_impact": "より多くの顧客への露出"
                })
        else:
            suggestions.append({
                "category": "検索可視性",
                "priority": "高",
                "suggestion": "現在圏外のため、基本的なSEO対策が必要です",
                "expected_impact": "検索結果への表示"
            })
        
        # 価格による提案
        if own_price > 0 and avg_price > 0:
            if own_price > avg_price * 1.3:
                suggestions.append({
                    "category": "価格戦略",
                    "priority": "中",
                    "suggestion": "競合より価格が高いため、付加価値の訴求または価格調整を検討",
                    "expected_impact": "価格競争力の向上"
                })
        
        # レビューによる提案
        if own_reviews < 10:
            suggestions.append({
                "category": "レビュー獲得",
                "priority": "中",
                "suggestion": "レビュー数を増やすため、購入後のフォローアップを強化しましょう",
                "expected_impact": "信頼性と検索順位の向上"
            })
        
        # キーワード最適化提案
        suggestions.append({
            "category": "キーワード最適化",
            "priority": "高",
            "suggestion": f"「{keyword}」の各キーワードを商品名に自然に組み込みましょう",
            "expected_impact": "検索マッチング率の向上"
        })
        
        return {
            "overall_assessment": f"AI分析は現在利用できませんが、基本分析によると改善の余地があります。特に{keyword}に関するSEO最適化を重点的に行うことをお勧めします。",
            "competitive_analysis": {
                "price_competitiveness": price_analysis,
                "title_analysis": title_analysis,
                "review_analysis": review_analysis
            },
            "improvement_suggestions": suggestions,
            "keyword_optimization": {
                "current_keyword_usage": f"「{keyword}」の使用状況を詳細分析するにはAI機能が必要です",
                "recommended_keywords": keyword.split() if keyword else [],
                "keyword_placement_tips": "商品名の前半、キャッチコピー、商品説明に重要キーワードを配置"
            },
            "next_steps": [
                "商品名にメインキーワードを含める",
                "競合商品の価格とレビューを調査",
                "キャッチコピーでの差別化を図る"
            ]
        }


def get_ai_analysis(keyword_obj, ranking_result, top_products) -> Dict[str, Any]:
    """
    AI分析の実行とデータ整形を行う便利関数
    
    Args:
        keyword_obj: Keywordモデルのインスタンス
        ranking_result: RankingResultモデルのインスタンス  
        top_products: TopProductモデルのクエリセット
        
    Returns:
        AI分析結果の辞書
    """
    analyzer = ClaudeAnalyzer()
    
    # 自社商品データの準備
    own_product_data = {
        'rank': ranking_result.rank if ranking_result.is_found else '圏外',
        'product_name': keyword_obj.target_product_url,  # 実際の商品名データがあれば使用
        'price': 0,  # 自社商品の価格データがあれば設定
        'catchcopy': '',  # 自社商品のキャッチコピーがあれば設定
        'review_count': 0,  # 自社商品のレビュー数があれば設定
        'review_average': 0  # 自社商品のレビュー平均があれば設定
    }
    
    # 競合商品データの準備
    competitor_data = []
    for product in top_products:
        competitor_data.append({
            'rank': product.rank,
            'product_name': product.product_name,
            'price': product.price or 0,
            'catchcopy': product.catchcopy or '',
            'review_count': product.review_count or 0,
            'review_average': float(product.review_average or 0)
        })
    
    # AI分析の実行
    return analyzer.analyze_ranking_data(
        keyword=keyword_obj.keyword,
        own_product_data=own_product_data,
        competitor_data=competitor_data
    )