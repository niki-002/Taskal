# Taskal v2 Architecture

## 1. はじめに
Taskalは、予定・タスク・バイトのシフト・収支を統合して管理するWebアプリケーションである。

バックエンドはFastAPI、フロントエンドはTypeScript+React、データベースはPostgreSQL、ORMとしてSQLAlchemyを利用する。

フロントエンドからFastAPIのRestAPIを呼び出し、FastAPIがService層とRepository層を経由してDBにアクセスする。

GoogleCalenderとの連携は外部API連携として、Integration層に分離する。

## 2. 技術スタック
- フロントエンド
    - TypeScript
    - React
    - Tailwind CSS
- バックエンド
    - Python
    - FastAPI(RestAPI実装)
    - SQLAlchemy(Pythonコード上でDB操作)
    - Pydantic(入出力スキーマ)
    - Alembic(DBスキーマ変更をmigrationとして管理)
- DB
    - PostgreSQL
- 認証
    - Auth0
- 外部API
    - Google Calender API
- テスト
    - pytest
    - FastAPI TestClient

## 3. ディレクトリ構成
```
api/
├── routers/
│   ├── auth.py
│   ├── tasks.py
│   ├── schedules.py
│   ├── shifts.py
│   ├── account.py
│   └── transactions.py
│   
├── services/
│   ├── auth_service.py
│   ├── task_service.py
│   ├── schedule_service.py
│   ├── shift_service.py
│   └── transaction_service.py
│
├── repositories/
│   ├── user_repository.py
│   ├── task_repository.py
│   ├── schedule_repository.py
│   └── transaction_repository.py
│
├── integrations/
│   └── google_calendar.py
│
├── models/
├── schemas/
├── config.py
├── database.py
└── main.py
```
### routers
HTTPエンドポイント定義
### services
アプリケーションのロジック定義
### Repository
DBアクセスの定義
### Integration
外部API連携を定義

## 4.レイヤー間の依存関係
```
Router
  ↓
Service
  ↓
Repository
  ↓
Database
```
外部APIについては、
```
Router
  ↓
Service
  ↓
Integration
  ↓
Google Calendar API
```

## 5.ドメインごとの責務
### schedule
スケジュールを登録・管理する
- タイトル
- 種類
- カテゴリ
- 開始・終了日時（期限）
- （場所）
### task
「schedule」でのジャンル「課題」または「タスク」で登録された期限をつきのタスクを管理する
- 期限
- 完了状態
### Shift
「schedule」でのジャンル「バイト」または「インターン」で登録されたシフトを管理する
- 開始・終了日時
- 時給
- 場所
### Account
ユーザの所有する資産の保存先
- 残高
### Transaction
実際に発生した金銭移動
- 収入
- 支出
### PlannedTransaction
- 支出見込
- 収入見込

## 6.残高計算
残高は初期残高の差し引きから算出する。

## 7.見込と実績
Taskalでは見込の値と実際に発生した値を分離する。

## 8.Google Calenderとの連携
同期方向は以下のみとする。
```
Taskal → Google Calender
```
```
Taskal予定作成
→ Googleイベント作成

Taskal予定更新
→ Googleイベント更新

Taskal予定削除
→ Googleイベント削除
```

## 9.認証認可
## 10.エラーハンドリング
## 11.テスト