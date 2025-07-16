# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Recent Work History (2025年7月12日)

### Fixed Issues
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

### Modified Files
- `/templates/seo_ranking/ranking_detail.html`
- `/seo_ranking/views.py`
- `/templates/seo_ranking/rpp_detail.html`
- `/seo_ranking/views_rpp.py`

### Technical Notes
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