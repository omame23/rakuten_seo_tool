# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
やり取りは全て日本語で質問も回答もしてください。

## Project Overview

This is a Django-based SaaS application for Rakuten marketplace SEO and advertising management. The service helps Rakuten sellers track their product rankings and optimize their RPP (Rakuten Promotional Products) advertising campaigns.

- **Service Name**: 楽天SEO対策ツール (Rakuten SEO Tool)
- **Domain**: inspice.work (取得済み) 
- **Pricing**: ¥3,980/month (税込) with first month free trial (クレジットカード登録必須)
- **Django Project**: inspice_seo_tool
- **Payment System**: Stripe

## Server Environment

- **Server**: X VPS
- **OS**: Ubuntu 25.04
- **Plan**: VPS 8GB
- **vCPU**: 6 cores
- **Memory**: 12GB
- **Storage**: NVMe SSD 400GB
- **IP Address**: 162.43.53.160
- **Domain**: inspice.work (ネームサーバー設定済み)

## Current Status (本番環境)

### 本番環境状況
- **サーバー**: 稼働中 (X VPS - 162.43.53.160)
- **アクセス**: http://162.43.53.160:8001 ✅ (動作確認済み)
- **ドメイン**: inspice.work (DNS反映待ち中)
- **データベース**: PostgreSQL (inspice_seo_tool)
- **Redis**: ポート6380で動作中 (手動起動)
- **Webサーバー**: Nginx + Django開発サーバー

### サーバー常時稼働設定
- **Django Application**: ポート8001で常時稼働中
- **Redis**: ポート6380で常時稼働中
- **システムサービス**: systemdで自動起動設定済み
- **アクセス確認**: `http://162.43.53.160:8001` または `http://inspice.work:8001`

### 本番環境での修正反映手順
1. **コード修正後の反映**: 
   - `git pull origin main`のみで反映完了
   - **サーバー再起動は不要**（常時稼働設定済み）
   - Django開発サーバーは自動でコード変更を検知

### 進行中のタスク
- [ ] **DNS設定確認** - inspice.workドメインでのアクセス確認
- [ ] **SSL証明書設定** - Let's Encrypt証明書の取得とHTTPS化
- [ ] **メール設定** - info@inspice.workメールアドレス作成と認証メール機能
- [ ] **Celeryサービス設定** - systemdサービス化とバックグラウンドタスク設定

### 直近の課題
- Redis systemd設定未完了 (現在手動起動中)
- Django開発サーバーでの運用 (本番環境ではGunicorn推奨)
- メール転送設定未完了 (segi@inspice.net)

### 再開時の手順
1. Current Statusを確認
2. サーバー状態をチェック (`ssh root@162.43.53.160`)
3. DNS設定反映確認 (`nslookup inspice.work`)
4. Djangoアプリケーション起動確認 (`http://162.43.53.160:8001`)
5. 次のタスクをTodoWriteツールで整理

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run Celery worker (in separate terminal)
celery -A inspice_seo_tool worker --loglevel=info

# Run Celery beat scheduler (in separate terminal)
celery -A inspice_seo_tool beat --loglevel=info

# Run tests
python manage.py test

# Shell access
python manage.py shell
```

## Production Deployment Commands

**重要: 修正後は必ず本番環境に反映すること**

### Server Access
- **SSH接続**: `ssh root@162.43.53.160`
- **パスワード**: `MaMe@1756WaRuo`

### Deployment Steps
```bash
# 1. Commit and push changes to GitHub
git add .
git commit -m "修正内容の説明"
git push origin main

# 2. Deploy to production server (サーバー再起動不要)
sshpass -p 'MaMe@1756WaRuo' ssh root@162.43.53.160 "cd /var/www/inspice/rakuten_seo_tool && git pull origin main"

# 完了！Django開発サーバーが自動でコード変更を検知して反映されます
```

### 常時稼働サービス確認
```bash
# Django server status check
sshpass -p 'MaMe@1756WaRuo' ssh root@162.43.53.160 "ps aux | grep 'python manage.py runserver' | grep -v grep"

# Redis server status check
sshpass -p 'MaMe@1756WaRuo' ssh root@162.43.53.160 "ps aux | grep redis | grep -v grep"
```

### Manual Server Commands (if needed)
```bash
# SSH into server
ssh root@162.43.53.160

# Navigate to project directory
cd /var/www/inspice/rakuten_seo_tool

# Pull latest changes
git pull origin main

# Restart Django server
pkill -f "python manage.py runserver"
source venv/bin/activate
nohup python manage.py runserver 0.0.0.0:8001 > /dev/null 2>&1 &
```

## Technology Stack

- **Backend**: Python + Django
- **Frontend**: Django Templates + Bootstrap
- **Database**: PostgreSQL
- **Payment**: Stripe
- **External APIs**: Rakuten Market API, Claude API
- **Development Environment**: Mac
- **Background Tasks**: Celery + Redis

## Architecture Overview

### Django Apps

1. **accounts** - User authentication and subscription management
   - Custom User model with subscription fields (trial_end_date, subscription_status)
   - Master account functionality for admin access
   - Integration with django-allauth for authentication
   - User registration fields: メールアドレス, パスワード, 会社名, 担当者名, 電話番号, 楽天店舗ID（手動入力）
   - Email verification required
   - Password reset functionality

2. **seo_ranking** - Core SEO and RPP tracking functionality
   - Models: Keyword, RankingResult, SearchLog, RPPKeyword, RPPResult
   - Rakuten API integration (rakuten_api.py)
   - Web scraping for RPP data (rpp_scraper.py)
   - AI analysis using Claude API (ai_analysis.py)
   - Background tasks via Celery (tasks.py)

### Key Integration Points

1. **Rakuten Market API**
   - APP_ID and SECRET stored in environment variables
   - Product search and ranking endpoints
   - Rate limiting considerations

2. **Claude API** 
   - Used for competitive analysis in ai_analysis.py
   - API key in ANTHROPIC_API_KEY environment variable

3. **Stripe Payment**
   - Subscription management at ¥3,980/month
   - Webhook endpoints for payment events
   - Test keys in development

4. **Celery + Redis**
   - Background task processing
   - Scheduled tasks: auto_keyword_search (1 min), cleanup tasks (daily)
   - Redis as message broker

### Data Flow

1. Users register keywords (max 10 per user)
2. Celery tasks fetch rankings from Rakuten API
3. Results stored with historical tracking
4. AI analysis provides improvement suggestions
5. RPP scraper tracks advertising positions

## Feature Details

### SEO Search Ranking Feature
- **Maximum Keywords**: 10 per user
- **Data Retrieved via Rakuten API**:
  - 商品名 (Product name)
  - キャッチコピー (Catch copy)
  - 商品URL (Product URL)
  - 商品価格 (Product price)
  - 商品画像 128x128 (Product image)
  - レビュー件数 (Review count)
  - レビュー平均 (Review average)
  - 商品別ポイント倍付け (Product-specific point multiplier)
  - ジャンルID (Genre ID)
  - タグID (Tag ID)
  - 製品情報・商品仕様 (Product information/specifications)

### Search Result Analysis Feature
- **Target**: Top 1-10 search results
- **AI Analysis**: Uses Claude API to compare with user's products
- **Improvement Suggestions**: Optimization recommendations for search keywords
- **Improvement Tracking**: Register improvement implementation dates and track ranking changes

### RPP Advertising Position Tracking
- **Maximum Keywords**: 10 per user
- **Data Collection**: Web scraping (once per day)
- **Target URL**: https://search.rakuten.co.jp/search/mall/{search_keyword}/
- **Collection Range**: Within 5 pages of search results
- **Identification**: [PR] mark above product name indicates advertisement
- **Recorded Data**: Bid price, display position, effectiveness metrics

### Data Management
- **Execution**: Manual execution + automatic execution settings available
- **History Management**: Save history of search rankings and RPP positions
- **Data Export**: CSV format download available

### Important Considerations

- Always check user.subscription_status before allowing premium features
- Master accounts (is_master_account=True) have special privileges
- RPP scraping respects robots.txt and rate limits
- All timestamps use timezone-aware datetime
- Bulk operations have pagination for performance

### Environment Variables

Required in .env file:
- RAKUTEN_APP_ID
- RAKUTEN_SECRET
- ANTHROPIC_API_KEY
- STRIPE_PUBLISHABLE_KEY
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- SECRET_KEY (Django)
- DEBUG (True/False)
- DATABASE_URL (for production PostgreSQL)

## Security Requirements

- HTTPS support (SSL certificate)
- Password hashing
- CSRF protection
- SQL injection prevention
- Rakuten Market terms of service compliance
- Scraping frequency limits (once per day)
- Proper user data management
- Payment data security

## Recent Work History

### 2025年7月18日: RPP通信エラー調査と修正（未完了）

#### 🚨 **現在の問題**
- **症状**: RPP個別検索・一括検索で「通信エラーが発生しました: HTTP error! status: 500」エラーが発生
- **発生頻度**: 個別検索、一括検索ともに継続的に発生
- **対象機能**: RPP（楽天プロモーション商品）順位検索機能

#### 🔍 **調査結果**
1. **本番環境の状態**:
   - ✅ RPPスクレイピング機能は正常動作（`scrape_rpp_ranking`テスト成功）
   - ✅ データベースは正常（14キーワード、3結果、45広告データ）
   - ✅ Django、Celery、Redis全サービス正常稼働
   - ✅ 本番環境で直接スクレイピングテスト成功（「ステップ」「テスト」キーワードで確認）

2. **実施した修正**:
   - ✅ JavaScriptのハードコードURL `/seo/rpp/bulk-search/` を Django URLテンプレートタグ `{% url "seo_ranking:rpp_bulk_search" %}` に修正
   - ✅ 本番環境にデプロイ完了

3. **修正後の状況**:
   - ❌ **問題継続**: 修正後も通信エラーが発生
   - ❌ **根本原因未特定**: URL修正だけでは解決しなかった

#### 🧪 **技術的詳細**
- **検証済み**: views_rpp.py の `rpp_keyword_search` および `rpp_bulk_search` 関数は正常
- **検証済み**: rpp_scraper.py のスクレイピング機能は正常動作
- **検証済み**: Django URL設定は正常（`path('rpp/bulk-search/', views_rpp.rpp_bulk_search, name='rpp_bulk_search')`）
- **検証済み**: 本番環境でのDjangoシェルからの直接テスト成功

#### 🎯 **推定される原因**
1. **フロントエンド-バックエンド間の通信レイヤー**: AJAX リクエストの処理過程での問題
2. **Django ビューレベルでの例外処理**: リクエスト処理中の未捕捉エラー
3. **セッション・認証関連**: AJAXリクエストでの認証情報の問題
4. **CSRFトークン**: CSRFトークンの取得・送信の問題
5. **HTTP メソッド・ヘッダー**: リクエストメソッドやContent-Typeの問題

#### 📋 **次回の調査項目**
1. **ブラウザ開発者ツール**: Network タブで実際のHTTPリクエスト・レスポンスを確認
2. **Django ログ**: より詳細なログレベルでエラーログを確認
3. **AJAX リクエスト**: JavaScriptのfetch関数の詳細なデバッグ
4. **CSRFトークン**: CSRFトークンの正確な取得・送信を確認
5. **リクエストデータ**: POST データの形式と内容を確認
6. **レスポンスデータ**: サーバーからの実際のレスポンス内容を確認

#### 🔧 **推奨する次回の対応**
1. **デバッグ情報の追加**: JavaScript に詳細なコンソールログを追加
2. **Django ログレベル上げ**: DEBUG レベルでより詳細なログを出力
3. **段階的なデバッグ**: 個別検索から始めて、一括検索に進む
4. **手動テスト**: ブラウザの開発者ツールを使用してリクエストを手動で送信
5. **バックエンドテスト**: Django shell からビュー関数を直接呼び出し

#### 📁 **関連ファイル**
- `views_rpp.py:322-441` - rpp_keyword_search 関数（個別検索）
- `views_rpp.py:732-913` - rpp_bulk_search 関数（一括検索）
- `templates/seo_ranking/rpp_keyword_list.html:256-374` - フロントエンド JavaScript
- `rpp_scraper.py:540-600` - スクレイピング機能

#### 🎯 **修正状況**
- **進捗**: 50%（原因特定は完了、根本修正は未完了）
- **優先度**: 高（コア機能の障害）
- **影響範囲**: RPP検索機能全般

#### 🖥️ **現在の本番環境状態**（2025年7月18日時点）
- **サーバー**: X VPS (162.43.53.160) - 正常稼働
- **アクセス**: http://162.43.53.160:8001 - 正常アクセス可能
- **Django アプリケーション**: ポート8001で稼働中
- **システムサービス**:
  - ✅ `inspice.service` - Active (running)
  - ✅ `inspice-celery.service` - Active (running) - 7 worker processes
  - ✅ `inspice-celery-beat.service` - Active (running)
- **データベース**: SQLite (3.5MB) - 正常稼働
- **Redis**: ポート6380で稼働中
- **直近のデプロイ**: 2025/07/18 - URL修正のデプロイ完了
- **ログ**: /var/log/inspice/ に出力中
- **コードベース**: 最新の修正が反映済み（commit 587d86d）

### 2025年7月17日: VPSサーバーセットアップ完了

#### 実装内容
1. ✅ **VPSサーバー基本設定**
   - Ubuntu 25.04のセットアップ
   - 必要ソフトウェアのインストール (Python 3.13.3, PostgreSQL 17.5, Redis 7.0.15, Nginx 1.26.3)
   - セキュリティ設定とファイアウォール設定

2. ✅ **Djangoアプリケーションデプロイ**
   - GitHubからのコードクローン (https://github.com/omame23/rakuten_seo_tool.git)
   - 仮想環境作成とパッケージインストール
   - データベース設定とマイグレーション
   - マスターアカウント作成 (segishogo@gmail.com / admin123)

3. ✅ **ドメイン設定**
   - inspice.workドメインの設定
   - Nginx設定とリバースプロキシ
   - DNS設定 (お名前.comネームサーバー使用)

#### 技術的詳細
- **プロジェクト場所**: `/var/www/inspice/rakuten_seo_tool`
- **仮想環境**: `/var/www/inspice/rakuten_seo_tool/venv`
- **環境変数**: `.env`ファイル (ALLOWED_HOSTS=localhost,127.0.0.1,162.43.53.160,inspice.work,www.inspice.work)
- **Nginx設定**: `/etc/nginx/sites-available/inspice.work`
- **ファイアウォール**: UFW + X VPS管理画面でポート8001開放
- **Redis**: 手動起動 (redis-server --port 6380 --bind 127.0.0.1 --protected-mode no --daemonize yes)

#### 開発サーバー起動コマンド
```bash
cd /var/www/inspice/rakuten_seo_tool
source venv/bin/activate
python manage.py runserver 0.0.0.0:8001
```

### 2025年7月16日: マスターアカウント店舗管理機能の実装

#### 実装内容
1. ✅ **マスターアカウント専用店舗管理機能**
   - 「ユーザー管理」から「店舗管理」への表記変更
   - 店舗の閲覧、編集、削除機能
   - 新規店舗追加機能（楽天店舗IDのみで登録可能）
   - ダッシュボードでの店舗切り替えプルダウン機能

2. ✅ **店舗別SEO・RPP管理機能**
   - 選択店舗のキーワード一覧表示
   - キーワード登録時の店舗ID自動設定
   - 店舗別一括検索機能
   - 店舗別履歴・詳細閲覧機能

3. ✅ **マスターアカウント向けアクセス制御**
   - 全店舗データへのアクセス権限
   - 店舗IDクリックでダッシュボード移動
   - 各機能での店舗選択対応

#### 修正したファイル
- `/accounts/decorators.py` - マスターアカウント専用デコレーター
- `/accounts/views_master.py` - 店舗管理ビュー
- `/accounts/forms_master.py` - 店舗管理フォーム
- `/templates/accounts/master/` - 店舗管理テンプレート一式
- `/accounts/views.py` - ダッシュボード修正
- `/seo_ranking/views.py` - SEO機能の店舗対応
- `/seo_ranking/views_rpp.py` - RPP機能の店舗対応
- `/seo_ranking/forms.py` - SEOフォームの店舗対応
- `/seo_ranking/forms_rpp.py` - RPPフォームの店舗対応
- `/templates/accounts/dashboard.html` - ダッシュボード修正
- `/templates/seo_ranking/rpp_keyword_list.html` - RPP一覧表示改善

#### 技術的な解決事項
1. **404エラーの修正**: マスターアカウントが他店舗データにアクセスできない問題を解決
2. **キーワード登録問題の修正**: フォームバリデーションでの対象ユーザー混同を解決
3. **データ表示問題の修正**: マスターアカウントの既存キーワードが表示されない問題を解決

#### 実装の詳細

**1. マスターアカウント専用デコレーター**
```python
# accounts/decorators.py
def master_account_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_master:
            messages.error(request, 'この機能はマスターアカウントのみ利用可能です。')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
```

**2. 店舗管理ビュー**
```python
# accounts/views_master.py
class StoreListView(ListView):
    model = User
    template_name = 'accounts/master/store_list.html'
    context_object_name = 'stores'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.filter(is_master=False).order_by('company_name')
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(company_name__icontains=search_query) |
                Q(rakuten_shop_id__icontains=search_query)
            )
        return queryset
```

**3. 店舗切り替え機能**
```python
# accounts/views.py (DashboardView)
if user.is_master:
    all_stores = User.objects.filter(is_master=False).order_by('company_name')
    context['all_stores'] = all_stores
    selected_store_id = self.request.session.get('selected_store_id')
    if selected_store_id:
        try:
            selected_user = User.objects.get(id=selected_store_id, is_master=False)
            context['selected_store'] = selected_user
            keyword_count = Keyword.objects.filter(user=selected_user).count()
        except User.DoesNotExist:
            del self.request.session['selected_store_id']
            del self.request.session['selected_store_name']
```

**4. SEO機能の店舗対応**
```python
# seo_ranking/views.py
def get_queryset(self):
    if self.request.user.is_master:
        selected_store_id = self.request.session.get('selected_store_id')
        if selected_store_id:
            try:
                selected_user = User.objects.get(id=selected_store_id, is_master=False)
                return Keyword.objects.filter(user=selected_user).order_by('-created_at')
            except User.DoesNotExist:
                return Keyword.objects.none()
    return Keyword.objects.filter(user=self.request.user).order_by('-created_at')
```

**5. RPP機能の店舗対応**
```python
# seo_ranking/views_rpp.py
def get_queryset(self):
    if self.request.user.is_master:
        selected_store_id = self.request.session.get('selected_store_id')
        if selected_store_id:
            try:
                selected_user = User.objects.get(id=selected_store_id, is_master=False)
                return RPPKeyword.objects.filter(user=selected_user).order_by('-created_at')
            except User.DoesNotExist:
                return RPPKeyword.objects.none()
    return RPPKeyword.objects.filter(user=self.request.user).order_by('-created_at')
```

**6. フォームの店舗対応**
```python
# seo_ranking/forms.py & forms_rpp.py
def __init__(self, *args, user=None, selected_store=None, **kwargs):
    super().__init__(*args, **kwargs)
    self.user = user
    self.selected_store = selected_store
    self.target_user = selected_store if (user and user.is_master and selected_store) else user
    
    if user and user.is_master and selected_store:
        self.fields['rakuten_shop_id'].initial = selected_store.rakuten_shop_id
        self.fields['rakuten_shop_id'].widget.attrs.update({
            'readonly': True,
            'class': 'form-control bg-light',
            'title': f'選択店舗: {selected_store.company_name}'
        })
```

#### 現在の機能状況
- **SEO機能**: 完全に店舗別対応済み
- **RPP機能**: 完全に店舗別対応済み  
- **ダッシュボード**: 店舗切り替え機能完備
- **マスター管理**: 全店舗の統合管理可能

#### 今後の課題
1. **UI/UX改善**: 店舗切り替えUIの視認性向上
2. **パフォーマンス最適化**: 大量店舗データの効率的な処理
3. **統計・分析機能**: 全店舗横断でのデータ分析機能
4. **権限管理**: より細かな権限設定機能

### 2025年7月12日: UI/UX改善

#### Fixed Issues
1. ✅ **Thumbnail Display Text Visibility**: Fixed flexbox layout issues in SEO ranking detail page
   - Adjusted heights: Image 200px, Text 80px (total 280px)
   - Removed padding and borders for better space utilization
   - Changed background color to #f8f9fa

2. ✅ **Added Statistics to SEO Detail Page**: 
   - Price range: min-max and average
   - Review count: min-max and average
   - Review score: min-max and average
   - Keyword occurrence: min-max and average

3. ✅ **RPP Display Format Simplification**:
   - Removed card format display
   - Changed to 5×3 grid layout (positions 1-15)
   - Fixed image aspect ratio (1:1) using CSS

4. ✅ **RPP Memo Feature**: Added memo editing capability to RPP detail page
   - Unified with SEO ranking memo functionality
   - Changed from JSON-based to form-based approach

#### Technical Notes
- Use `object-fit: contain` for images to prevent cropping
- `aspect-ratio: 1/1` enforces square display
- Form-based approach preferred over JSON for consistency
- Always use timezone-aware datetime objects

## Development Workflow

When working on tasks in this project, follow these steps:

1. まず、問題を徹底的に考え、コードベースで関連ファイルを読み、tasks/todo.mdに計画を書き出します。
2. 計画には、完了したらチェックマークを付けられるToDo項目のリストを含めます。
3. 作業を始める前に、私に連絡を取り、計画を確認します。
4. 次に、ToDo項目に取り組み始め、完了したら完了マークを付けます。
5. 各ステップごとに、どのような変更を加えたのか、概要を説明してください。
6. タスクやコード変更はできる限りシンプルにしてください。大規模で複雑な変更は避けたいと考えています。変更はコードへの影響を最小限に抑えるべきです。シンプルさが何よりも重要です。
7. 最後に、todo.md ファイルにレビューセクションを追加し、変更内容の概要とその他の関連情報を記載してください。
