# ステーブルコイン入門 — 学習サイト

ステーブルコインの「歴史・現状・未来」をやさしく学べる1ページの学習サイトです。
初心者から実務者まで対象。市場データ（時価総額・価格）は CoinGecko の公開API から**ページを開くたびに自動取得**します。

🌐 **公開ページ:** https://yoshidai55.github.io/stablecoin-guide/

## 構成

| ファイル | 内容 |
|---|---|
| `index.html` | サイト本体（HTML/CSS/JS すべて1ファイルに同梱） |
| `news.json` | 最新ニュース（GitHub Actions が毎日自動更新） |
| `archive.html` | ニュース・アーカイブ（重要ニュース強調＋月別一覧＋検索） |
| `archive.json` | アーカイブ用データ（出てきたニュースを全件累積） |
| `scripts/update_news.py` | RSSからニュースを取得する更新スクリプト |
| `.github/workflows/update-news.yml` | 毎日5時(JST)に上記を実行するワークフロー |
| `README.md` | このファイル |

## 自動更新の仕組み

- **市場データ（時価総額・価格）** … 訪問者がページを開くたびにJavaScriptがCoinGecko APIから最新値を取得（メンテ不要）。
- **ニュース** … GitHub Actions が **毎日5時(JST)** に複数の暗号資産メディアのRSSからステーブルコイン関連記事を収集し、`news.json` を自動更新・自動コミット。ページは `news.json` を読み込んで表示します。**PC・アプリの起動は不要**で、GitHubのサーバー上で完結します。

## セットアップ手順

### 1. GitHubへアップロード
このフォルダの中身（`.github` フォルダ含む）を GitHub リポジトリにアップロードします。
`.github` などの隠しフォルダもアップロード対象に含めてください。

### 2. GitHub Pages を有効化
リポジトリの **Settings → Pages** で、Source =「Deploy from a branch」、Branch = `main` / `/(root)` に設定して保存。
数分後に `https://<ユーザー名>.github.io/<リポジトリ名>/` で公開されます。

### 3. Actions の書き込み権限を確認
**Settings → Actions → General → Workflow permissions** で
**「Read and write permissions」** を選択して保存（自動コミットに必要）。

### 4. 動作確認
**Actions** タブ →「Update stablecoin news」→ **Run workflow** で手動実行できます。
成功すると `news.json` が更新され、Pages にも自動反映されます。以後は毎日自動で更新されます。

> RSSに該当ニュースが無い日は `news.json` を更新せず、前回の内容を維持します。

## ライセンス・免責

教育目的のコンテンツです。投資・法務・税務上の助言ではありません。
