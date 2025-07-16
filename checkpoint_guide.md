# チェックポイント作成・復元ガイド

## 現在のプロジェクトの状態

- ✅ Gitリポジトリ初期化済み
- ✅ 初回コミット完了（コミットID: ec42914）
- ✅ .gitignore設定済み（センシティブ情報を除外）

## チェックポイントの作成方法

### 1. 現在の作業を保存
```bash
# 変更を確認
git status

# 変更をステージング
git add .

# コミット
git commit -m "説明的なメッセージ"
```

### 2. チェックポイント（タグ）を作成
```bash
# バージョンタグ
git tag -a v0.1.0 -m "基本機能実装完了"

# 日付タグ
git tag -a checkpoint-20250116 -m "2025年1月16日の状態"

# 作業前のバックアップ
git tag -a before-major-change -m "大規模変更前のバックアップ"
```

### 3. GitHubにプッシュ（設定後）
```bash
# すべてのタグをプッシュ
git push origin --tags

# 特定のタグのみプッシュ
git push origin v0.1.0
```

## チェックポイントへの復元方法

### 方法1: 安全な確認（推奨）
```bash
# タグ一覧を表示
git tag -l

# 特定のタグの詳細を確認
git show v0.1.0

# 一時的にその時点のコードを確認（読み取り専用）
git checkout v0.1.0

# 最新の状態に戻る
git checkout main
```

### 方法2: 新しいブランチで過去の状態を確認
```bash
# 過去の状態で新しいブランチを作成
git checkout -b check-old-version v0.1.0

# 確認後、mainブランチに戻る
git checkout main

# 不要になったブランチを削除
git branch -d check-old-version
```

### 方法3: 完全な復元（注意！現在の変更が失われます）
```bash
# 現在の状態をバックアップ
git branch backup-current

# 特定のチェックポイントに完全に戻す
git reset --hard v0.1.0

# もし間違えた場合は、バックアップから復元
git reset --hard backup-current
```

## 実践的な使用例

### 開発フローでの活用
```bash
# 1. 新機能開発前にチェックポイント作成
git tag -a before-new-feature -m "新機能開発前"

# 2. 開発作業...

# 3. もし問題が発生したら
git checkout before-new-feature  # 確認
git reset --hard before-new-feature  # 完全に戻す
```

### 定期的なバックアップ
```bash
# 週次バックアップ（cronやカレンダーリマインダーで実行）
git tag -a weekly-$(date +%Y%m%d) -m "週次バックアップ $(date +%Y/%m/%d)"
```

## トラブルシューティング

### コミットし忘れた変更がある場合
```bash
# 現在の変更を一時保存
git stash

# チェックポイントに移動
git checkout v0.1.0

# 元に戻って変更を復元
git checkout main
git stash pop
```

### 間違えて重要なファイルを削除した場合
```bash
# 特定のファイルだけ過去の状態から復元
git checkout v0.1.0 -- path/to/important/file.py
```

## 推奨されるタグ命名規則

1. **バージョン番号**: `v1.0.0`, `v1.1.0`
2. **日付ベース**: `checkpoint-20250116`, `backup-20250116`
3. **機能ベース**: `feature-auth-complete`, `before-ui-redesign`
4. **リリース**: `release-production`, `release-staging`

## 次のステップ

1. 定期的にコミットする習慣をつける
2. 重要な変更の前後でタグを作成
3. GitHubと連携してクラウドバックアップ
4. チーム開発の場合はブランチ戦略を検討