# Taskal

Taskalは、日々のタスクをシンプルに管理するためのタスク管理Webアプリです。FastAPI・PostgreSQL・TypeScript + Reactを用いて、タスクの作成・一覧表示・削除ができる構成で実装しました。バックエンドAPIとフロントエンドを分けて開発し、CRUD処理とDB連携の基礎を学ぶことを目的に制作しました。

## 作成背景

Webエンジニアとして必要なバックエンド開発の基礎を身につけるために作成しました。特に、API設計、データベース連携、フロントエンドとの接続、テストの流れを一通り経験することを目的としています。最小構成のタスク管理アプリを題材にすることで、基本的なCRUD処理を明確に理解できるようにしました。

## 主な機能

- タスク作成
- タスク一覧表示
- タスク削除

## 技術スタック

### フロントエンド
- TypeScript
- React
- Vite
- React Router
- Auth0（`@auth0/auth0-react`）
- ESLint / Prettier
 
### バックエンド
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Auth0（PyJWTでアクセストークンを検証）

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
  ├── frontend                  # フロントエンド（Vite + React + TypeScript）
  │   ├── public
  │   │   └── icon.svg
  │   ├── src
  │   │   ├── api               # fetchラッパー（client.ts）、タスクAPI関数（tasks.ts）
  │   │   ├── types             # APIの型定義
  │   │   ├── components        # TaskForm, TaskList, TaskItem, LoginButton など
  │   │   ├── pages             # LoginPage, RegisterPage, TasksPage
  │   │   ├── hooks             # useApi（トークン付きfetch）など
  │   │   ├── styles            # CSS
  │   │   ├── config.ts         # Auth0の設定値・画面のパス
  │   │   ├── App.tsx           # ルーティング定義
  │   │   └── main.tsx          # エントリーポイント
  │   ├── index.html
  │   ├── package.json
  │   ├── eslint.config.js
  │   ├── tsconfig.json
  │   └── vite.config.ts        # 開発サーバー・/apiのプロキシ設定
  │
  └── tests                     # テスト用
      ├── conftest.py           # 共通処理
      ├── test_auth.py          # 認証処理テスト
      └── test_task.py          # タスク処理テスト
```

## セットアップ

### 前提環境

- Python 3.12 以上
- Node.js 20.19 以上（または 22.12 以上）
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

AUTH0_DOMAIN=
AUTH0_AUDIENCE=
AUTH0_EMAIL_CLAIM=   # 任意（既定値: https://taskal.app/email）

# フロントエンド（Vite）用
VITE_AUTH0_DOMAIN=
VITE_AUTH0_CLIENT_ID=
VITE_AUTH0_AUDIENCE=
```

フロントエンドもリポジトリ直下の `.env` を読み込みます（`VITE_` で始まる変数だけがブラウザに公開されます）。

#### Auth0の設定

ログイン・新規登録・パスワード再設定はAuth0が担当し、APIはAuth0が発行したアクセストークンのみで認証します。

1. Auth0の **APIs** でAPIを作成し、Identifierを `AUTH0_AUDIENCE` に設定（署名アルゴリズムはRS256）
2. **Applications** で「Single Page Application」を作成し、以下を設定
    - Allowed Callback URLs：`http://localhost:5173`
    - Allowed Logout URLs：`http://localhost:5173/login`
    - Allowed Web Origins：`http://localhost:5173`
    - Refresh Token Rotation：有効
3. `.env` の `VITE_AUTH0_DOMAIN`・`VITE_AUTH0_CLIENT_ID`・`VITE_AUTH0_AUDIENCE` にテナントのDomain、SPAのClient ID、APIのIdentifierを設定
4. （任意）Taskal側のユーザーにメールアドレスを保存する場合は、Post Login Actionでアクセストークンにクレームを追加

```js
exports.onExecutePostLogin = async (event, api) => {
  api.accessToken.setCustomClaim("https://taskal.app/email", event.user.email);
};
```

初回アクセス時に、アクセストークンの `sub` をもとにTaskal側のユーザーが自動作成されます。

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

テストは `backend/` ディレクトリで実行します（`backend/pytest.ini` で `app` パッケージを読み込めるようにしています）。テスト用DBは `TEST_DATABASE_URL` が指すDBを使い、テストのたびにマイグレーションの適用とテーブルの削除を行います。

```bash
cd backend
pip install -r requirements-dev.txt   # pytest・httpx を含む開発用パッケージ
pytest
```

### Docker での開発・テスト

`.env.example` をもとにリポジトリ直下に `.env.docker` を作成し、以下を実行します。

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head   # 開発用DBにマイグレーションを適用
docker compose exec backend pytest                 # テストを実行
```

- `backend` は開発用イメージ（`backend/Dockerfile` の `dev` ステージ）でビルドされ、`pytest`・`httpx` がインストールされます
- テスト用DB（`TEST_DATABASE_URL` のDB名。例：`taskal_test`）は、DBボリュームの初回作成時に `db/init/01-create-test-db.sh` で自動作成されます

#### 既存のDBボリュームを使っている場合

初期化スクリプトはDBボリュームの初回作成時にしか実行されないため、それ以前から環境を使っている場合はテスト用DBを手動で作成します。

```bash
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" taskal_test'
```

`database "taskal_test" already exists` と表示された場合は作成済みです。

### 6. フロントエンドの起動

バックエンド（`http://localhost:8000`）を起動した状態で、別のターミナルで実行します。

```bash
cd frontend
npm install
npm run dev
```

ブラウザで http://localhost:5173 を開きます。`/api` へのリクエストは Vite の開発サーバーがバックエンドへプロキシします。

| コマンド | 内容 |
| --- | --- |
| `npm run dev` | 開発サーバーを起動 |
| `npm run build` | 型チェック（`tsc`）と本番ビルド（`frontend/dist`） |
| `npm run lint` | ESLint |
| `npm run format` | Prettierで整形 |

#### 画面
- `/login`：ログイン画面
- `/register`：新規登録画面
- `/`：タスク一覧画面（未ログイン時は `/login` へリダイレクト）

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
- UI/UXの改善
- 認証機能をAuth0へ移行