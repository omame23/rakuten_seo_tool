# GitHub連携手順

## 1. GitHubリポジトリとの接続

GitHubでリポジトリを作成した後、以下のコマンドを実行してください：

```bash
# GitHubのリモートリポジトリを追加
git remote add origin https://github.com/YOUR_USERNAME/rakuten_seo_tool.git

# 現在のブランチ名をmainに変更（GitHubのデフォルトに合わせる）
git branch -M main

# GitHubにプッシュ
git push -u origin main
```

※ `YOUR_USERNAME` は実際のGitHubユーザー名に置き換えてください

## 2. 認証設定

初回プッシュ時にGitHubの認証が必要です：

### Personal Access Token（推奨）
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 「Generate new token」をクリック
3. 権限: `repo` にチェック
4. トークンをコピーして保存（再表示されません）
5. パスワード入力時にこのトークンを使用

## 3. 基本的なGit操作

### 変更をコミット
```bash
git add .                      # 全ての変更をステージング
git commit -m "コミットメッセージ"  # コミット
git push                       # GitHubにプッシュ
```

### チェックポイント（タグ）の作成
```bash
# バージョンタグを作成
git tag -a v1.0 -m "Version 1.0: 初期リリース"
git push origin v1.0

# 日付ベースのタグ
git tag -a checkpoint-20250116 -m "2025年1月16日のチェックポイント"
git push origin checkpoint-20250116
```

### 特定のチェックポイントに戻る
```bash
# タグ一覧を確認
git tag -l

# 特定のタグの状態を確認（読み取り専用）
git checkout v1.0

# 元に戻る
git checkout main

# 完全にその時点に戻す（注意：現在の変更は失われます）
git reset --hard v1.0
```

### ブランチを使った安全な開発
```bash
# 新機能開発用のブランチを作成
git checkout -b feature/new-feature

# 作業後、mainにマージ
git checkout main
git merge feature/new-feature
```

## 4. よく使うコマンド

```bash
git status              # 現在の状態を確認
git log --oneline      # コミット履歴を簡潔に表示
git diff               # 変更内容を確認
git pull               # GitHubから最新を取得
```

## 5. .gitignoreの確認

センシティブな情報が含まれないよう、以下のファイルが除外されていることを確認：
- .env
- *.pyc
- db.sqlite3
- venv/
- dump.rdb
- APIキーを含むファイル