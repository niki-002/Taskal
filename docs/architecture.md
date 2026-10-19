# Taskal v2 Architecture

## 1. はじめに
Taskalは、予定・タスク・バイトのシフト・収支を統合して管理するWebアプリケーションである。

バックエンドはFastAPI、フロントエンドはTypeScript+React、データベースはPostgreSQL、ORMとしてSQLAlchemyを利用する。

フロントエンドからFastAPIのRestAPIを呼び出し、FastAPIがService層とRepository層を経由してDBにアクセスする。

GoogleCalenderとの連携は外部API連携として、Integration層に分離する。

## 2. 技術スタック
- フロントエンド
    - TypeScript
    - React（Vite、React Router）
    - Tailwind CSS
- バックエンド
    - Python
    - FastAPI(RestAPI実装)
    - SQLAlchemy(Pythonコード上でDB操作。asyncio拡張＋asyncpgで非同期に扱う)
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
│   ├── auth.py
│   ├── task.py
│   ├── schedule.py
│   ├── shift.py
│   └── transaction.py
│
├── repositories/
│   ├── user.py
│   ├── task.py
│   ├── schedule.py
│   └── transaction.py
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
ファイル名はドメイン名とし、`_service`・`_repository` のようなディレクトリ名の接尾辞は付けない（例: `services/schedule.py`、`repositories/schedule.py`）。

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

### 実装方針
バックエンドはオブジェクト指向で書く。各層の責務は上記のとおりで、ここではその書き方を決める。

#### クラスの構成
| 層 | クラス名 | コンストラクタで受け取るもの | 返すもの |
| --- | --- | --- | --- |
| Router | （関数で書く） | - | Serviceの戻り値 |
| Service | `XxxService` | Repository・Integration | `schemas` のレスポンス |
| Repository | `XxxRepository` | DBセッション（`AsyncSession`） | `models` のインスタンス |
| Integration | `XxxClient` | 設定値・認証情報 | 外部APIの結果 |

- `Xxx` はドメイン名（ファイル名と同じ）。例: `services/schedule.py` の `ScheduleService`
- エラーは `app.core.errors` の `AppError` のサブクラスで表す。HTTPのステータスコードはそのクラスが持つ

#### 依存の受け取り方
- 依存するものはすべてコンストラクタで受け取る。クラスの中で別のクラスのインスタンスを作らない（テストで差し替えられるようにするため）
- 各クラスと同じファイルに、インスタンスを作る関数 `get_xxx_service` と、`Depends` 付きの型 `XxxServiceDep` を置く。RouterやServiceの依存には `XxxServiceDep`・`XxxRepositoryDep` を使う
- 複数のRepositoryを使うServiceは、そのすべてをコンストラクタで受け取る。`get_db` は1リクエストで1回しか呼ばれないため、同じリクエスト内のRepositoryは同じDBセッションを共有する
- リクエストをまたいで状態を共有するもの（公開鍵のキャッシュなど）は、モジュールにインスタンスを1つだけ作り、`get_xxx` でそれを返す（例: `services/auth.py` の `TokenVerifier`）

```python
# repositories/schedule.py
class ScheduleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, schedule_id: int, owner_id: int) -> Schedule | None:
        return await self.db.scalar(...)


def get_schedule_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> ScheduleRepository:
    return ScheduleRepository(db)


ScheduleRepositoryDep = Annotated[ScheduleRepository, Depends(get_schedule_repository)]


# services/schedule.py
class ScheduleService:
    def __init__(self, repository: ScheduleRepository):
        self.repository = repository

    async def get_schedule(self, schedule_id: int, current_user: User) -> ScheduleResponse:
        schedule = await self.repository.get_by_id(schedule_id, current_user.id)
        ...


def get_schedule_service(repository: ScheduleRepositoryDep) -> ScheduleService:
    return ScheduleService(repository)


ScheduleServiceDep = Annotated[ScheduleService, Depends(get_schedule_service)]


# routers/schedule.py
@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    service: ScheduleServiceDep,
    current_user: CurrentUserDep
):
    return await service.get_schedule(schedule_id, current_user)
```

#### 非同期処理
バックエンドは `async`/`await` で書く。DBには `create_async_engine`・`async_sessionmaker` で作った `AsyncSession`（ドライバはasyncpg）でアクセスする。
- DBアクセスやI/Oを含むRepository・Service・Routerのメソッドは `async def` にし、呼び出し側で `await` する。I/Oを含まない処理（レスポンスへの変換など）は通常の `def` のままでよい
- インスタンスを作るだけの `get_xxx_service`・`get_xxx_repository` は `def` のままにする
- `AsyncSession` では属性アクセス時の遅延ロード（暗黙の同期I/O）ができず、`MissingGreenlet` になる。そのため次のようにする
    - レスポンスで使うrelationshipは、クエリで `selectinload` などを指定して一緒に読み込む（例: `repositories/task.py` の `selectinload(Task.schedule)`）
    - セッションは `expire_on_commit=False` で作る。commit後にDB側で決まる値（`server_default` など）が必要な場合は `await db.refresh(obj)` で読み直す。relationshipも読み直す場合は `await db.refresh(obj, ["属性名", "relationship名"])` のように名前を指定する
- 同期処理しかないライブラリ（`PyJWKClient` による公開鍵の取得など）は、イベントループを止めないよう `run_in_threadpool` でスレッドプールに逃がす
- Alembicのマイグレーションは同期ドライバ（psycopg2）のまま実行する。環境変数 `DATABASE_URL` は `postgresql+psycopg2://...` で設定し、アプリ側で `settings.async_database_url`（asyncpgに差し替えたURL）を使う
- テストでは `TestClient` がイベントループを持つため、テスト関数は通常の `def` で書ける。Serviceの単体テストやRepositoryを直接呼ぶテストは `@pytest.mark.anyio` を付けた `async def` で書く

#### import
- クラスと `Dep` 付きの型は名前で直接importする。モジュールごとimportしない
  ```python
  from app.schemas.schedule import ScheduleCreate, ScheduleResponse
  from app.services.auth import CurrentUserDep
  from app.services.schedule import ScheduleServiceDep
  ```
- 例外として、`main.py` でRouterを登録するときだけは `from app.routers import schedule` のようにモジュールをimportし、`schedule.router` を使う

#### メソッド
- 外から呼ばないメソッドは名前の先頭に `_` を付ける
- インスタンスの状態を使わない処理は `@staticmethod`、別の値からインスタンスを作る処理は `@classmethod` にする（例: `Page.from_rows`、`PageParams.from_query`）
- 状態を持たない共通処理も、モジュールの関数にせず、関係するクラスのメソッドにまとめる（例: `Cursor.encode`、`AppError.to_response`）

#### 関数のままにするもの
FastAPIに関数として渡す必要があるものだけは関数で書く。
- Routerのエンドポイント
- インスタンスを作る関数（`get_xxx_service` など）と `get_current_user`・`get_db`
- 例外ハンドラ

#### テスト
- Serviceの単体テストでは、コンストラクタに偽のRepository・Integration（メソッドは `async def`）を渡し、DBや外部APIなしで検証する
- APIのテストでは `TestClient` でエンドポイントを呼び、テスト用DBを使って検証する

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