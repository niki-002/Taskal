# Taskal

Taskalは、日々のタスクをシンプルに管理するためのタスク管理Webアプリです。FastAPI・PostgreSQL・Javascriptを用いて、タスクの作成・一覧表示・削除ができる構成で実装しました。バックエンドAPIとフロントエンドを分けて開発し、CRUD処理とDB連携の基礎を学ぶことを目的に制作しました。

## 作成背景

Webエンジニアとして必要なバックエンド開発の基礎を身につけるために作成しました。特に、API設計、データベース連携、フロントエンドとの接続、テストの流れを一通り経験することを目的としています。最小構成のタスク管理アプリを題材にすることで、基本的なCRUD処理を明確に理解できるようにしました。

## 主な機能

- タスク作成
- タスク一覧表示
- タスク削除

## 技術スタック

### フロントエンド
- HTML
- CSS
- javascript
 
### バックエンド
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT, pwdlib

### データベース
- PostgreSQL

### テスト
- pytest

### バージョン管理
- Git
- GitHub

## ディレクトリ構造

```
Taskal
  ├── api                       # バックエンド
  │   │
  │   ├── core                  # 設定関連
  │   │   ├── __init__.py
  │   │   └── config.py         # 設定ファイル
  │   │
  │   ├── models                # SQLAlchemyモデル(DB構造)
  │   │   ├── __init__.py
  │   │   ├── auth.py           # ユーザーテーブル定義
  │   │   ├── Base.py           # ベーステーブル定義(Base)
  │   │   └── task.py           # タスクテーブル
  │   │
  │   ├── routers               # APIのURLエンドポイント定義
  │   │   ├── __init__.py
  │   │   ├── auth.py           # 認証処理エンドポイント定義
  │   │   └── task.py           # タスクCRUD処理エンドポイント定義
  │   │
  │   ├── schemas               # Pydanticスキーマ(APIのリクエスト・レスポンス)
  │   │   ├── __init__.py
  │   │   ├── auth.py           # 認証処理スキーマ
  │   │   └── task.py           # タスクCRUD処理スキーマ
  │   │
  │   ├── services              # 実際の処理・DB操作定義
  │   │   ├── __init__.py    
  │   │   ├── auth_service.py   # 認証処理・DB操作定義
  │   │   └── task_service.py   # タスク処理・DB操作定義
  │   │
  │   ├── __init__.py
  │   ├── db.py                 # DB接続管理
  │   └── main.py               # API起動ファイル
  │
  ├── frontend                  # フロントエンド
  │   ├── index.html
  │   ├── style.css
  │   └── main.js
  │
  └── tests                     # テスト用
      ├── conftest.py           # 共通処理
      ├── test_auth.py          # 認証処理テスト
      └── test_task.py          # タスク処理テスト
```

## セットアップ

### 前提環境

- Python 3.12 以上
- PostgreSQL
- Git

### 1. リポジトリをクローン

```bash
git clone <リポジトリURL>
```

### 2. 仮想環境を作成・有効化

```bash
cd Taskal
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 必要パッケージをインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数を設定

```.env```ファイルを作成し、以下を設定します。
```bash
DATABASE_URL=
TEST_DATABASE_URL=

SECRET_KEY = 
ALGORITHM = 
ACCESS_TOKEN_EXPIRE_MINUTES = 
```

### 5. サーバーの起動

#### 開発モード
```bash
fastapi dev api/main.py
```

#### 本番モード
```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```
APIドキュメントは以下でアクセスします。
- Swagger UI：https://127.0.0.1:8000/docs

#### テストの実行
```bash
pytest
```

## 主要エンドポイント
- ```GET /api/tasks```：タスク一覧取得
- ```POST /api/tasks```：タスク作成
- ```DELETE /api/tasks/{task_id}```：タスク削除

## 工夫した点

- FastAPIを用いてREST APIとしてタスク操作を実装したこと
- SQLAlchemyを使ってPostgreSQLと接続したこと
- フロントエンドから非同期通信でAPIを呼び出す構成にしたこと
- pytestを用いてCRUDの動作確認を行えるようにしたこと
- テストDBを分けることで、本番用データを壊さず検証できるようにしたこと

## 今後の改善点

- チェックボックスのバグ修正
- スマホデバイス対応
- カテゴリ分類機能追加
- 締切日や優先度、進捗機能の追加
- 検索・絞り込み・並び替え機能の追加
- 非同期処理化
- ログイン機能追加
- UI/UXの改善
- マイグレーション