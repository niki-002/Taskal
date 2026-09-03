# Taskal v2 API 設計書

> **文書ステータス: 設計案**
>
> この文書は、現在実装されているAPIの説明ではありません。
> `requirements.md`、`architecture.md`、`er-diagram.md` を基にしたTaskal v2向けのAPI仕様です。
> 実装開始前に「15. ER図・企画書へ反映が必要な事項」を確定してください。

## 1. APIの目的

Taskal v2 APIは、予定を中心として次の情報を一元管理します。

- カレンダーに表示するスケジュール
- スケジュールと連動するタスク
- バイト・インターンなどのシフト
- 現金、銀行口座などの資産
- 将来発生する収支見込
- 実際に発生した収支
- TaskalからGoogle Calendarへの一方向同期

## 2. 基本仕様

| 項目 | 仕様 |
| --- | --- |
| ベースパス | `/api/v1` |
| 通信形式 | HTTPS |
| リクエスト・レスポンス | `application/json` |
| 認証 | Auth0が発行するJWT Access Token |
| 日時 | ISO 8601、タイムゾーン必須 |
| 日付 | `YYYY-MM-DD` |
| 金額 | 1円を1とする整数 |
| フィールド名 | `snake_case` |
| ID | 正の整数 |

`v1` はTaskal v2で新しく設計するAPI契約の初版を表します。アプリのバージョン番号とは独立して管理します。

日時の保存はUTCとし、APIでは `2026-09-10T09:00:00+09:00` または
`2026-09-10T00:00:00Z` のようにタイムゾーンを必須とします。

### 2.1 リソースの関係

| リソース | 関係 |
| --- | --- |
| User | Schedule、Account、PlannedTransaction、Transactionを所有する |
| Schedule | TaskまたはShiftを最大1件持つ |
| Schedule | PlannedTransactionと関連付けられる |
| Account | Transactionを複数持つ |
| PlannedTransaction | 実績化されたTransactionを最大1件持つ |

### 2.2 スケジュール種別

`kind` はアプリ内部の処理を決める値、`category` はユーザー向けの分類です。

| `kind` | 用途 | `category` の例 |
| --- | --- | --- |
| `event` | 通常の予定 | `class`、`private` |
| `task` | 期限と完了状態を持つ予定 | `assignment`、`work` |
| `shift` | 時給などを持つ勤務予定 | `part_time`、`internship` |
| `payment` | 支払いに関する予定 | `subscription`、`rent` |

`category` は任意文字列とし、ユーザーが自由に分類できる設計とします。

## 3. 認証・ユーザー

### 3.1 Auth0認証

ログイン、サインアップ、パスワード再設定はAuth0が担当します。Taskal APIはパスワードを受け取りません。

認証が必要なすべてのリクエストに、Auth0が発行したAccess Tokenを指定します。

```http
Authorization: Bearer <access_token>
```

APIはJWTの署名、`iss`、`aud`、有効期限を検証します。初回アクセス時にAuth0の
`sub` を使ってTaskal側のUserを作成します。

Google OAuthコールバックを除くすべてのエンドポイントでAuth0認証が必要です。
コールバックではBearer Tokenの代わりに、連携開始時に発行した `state` を検証します。

### 3.2 ユーザー情報取得

```http
GET /api/v1/users/me
```

#### 成功レスポンス

`200 OK`

```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "taskal-user",
  "created_at": "2026-09-01T10:00:00Z"
}
```

### 3.3 ユーザー情報更新

```http
PATCH /api/v1/users/me
```

#### リクエスト

```json
{
  "username": "new-taskal-user"
}
```

#### 成功レスポンス

`200 OK`

```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "new-taskal-user",
  "created_at": "2026-09-01T10:00:00Z"
}
```

メールアドレスの変更はAuth0側で行い、Taskal側にはAuth0から同期します。

## 4. 共通仕様

### 4.1 一覧レスポンス

一覧APIはカーソル方式でページングします。

```json
{
  "items": [],
  "next_cursor": null
}
```

| クエリ | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `limit` | integer | `50` | 1〜100件 |
| `cursor` | string | なし | 前回レスポンスの `next_cursor` |

### 4.2 エラーレスポンス

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "入力内容を確認してください。",
    "details": [
      {
        "field": "end_at",
        "reason": "must_be_after_start_at"
      }
    ]
  }
}
```

### 4.3 共通ステータスコード

| ステータス | 用途 |
| --- | --- |
| `200 OK` | 取得・更新成功 |
| `201 Created` | 作成成功 |
| `202 Accepted` | 非同期処理を受け付けた |
| `204 No Content` | 削除成功 |
| `400 Bad Request` | リクエストの形式や業務ルールが不正 |
| `401 Unauthorized` | Access Tokenがない、または不正 |
| `404 Not Found` | リソースが存在しない、または他ユーザーが所有している |
| `409 Conflict` | 実績化済みなど、現在の状態では操作できない |
| `422 Unprocessable Content` | フィールドの型・必須・範囲が不正 |
| `502 Bad Gateway` | Google Calendarなど外部APIとの通信に失敗 |

他ユーザーのリソースを指定した場合も、リソースの存在を外部へ知らせないため `404` を返します。
所有ユーザーはAccess Tokenから決定するため、作成・更新リクエストに `user_id` は指定しません。

## 5. エンドポイント一覧

### Users

| メソッド | パス | 概要 |
| --- | --- | --- |
| `GET` | `/users/me` | 自分のユーザー情報を取得 |
| `PATCH` | `/users/me` | 自分のユーザー情報を更新 |

### Schedules

| メソッド | パス | 概要 |
| --- | --- | --- |
| `GET` | `/schedules` | カレンダー期間内の予定一覧を取得 |
| `POST` | `/schedules` | 通常予定または支払い予定を作成 |
| `GET` | `/schedules/{schedule_id}` | 予定を1件取得 |
| `PATCH` | `/schedules/{schedule_id}` | 予定の共通項目を更新 |
| `DELETE` | `/schedules/{schedule_id}` | 予定を削除 |

### Tasks

| メソッド | パス | 概要 |
| --- | --- | --- |
| `GET` | `/tasks` | タスク一覧を取得 |
| `POST` | `/tasks` | ScheduleとTaskを同時に作成 |
| `GET` | `/tasks/{schedule_id}` | タスクを1件取得 |
| `PATCH` | `/tasks/{schedule_id}` | ScheduleとTaskを同時に更新 |
| `DELETE` | `/tasks/{schedule_id}` | TaskとScheduleを削除 |

### Shifts

| メソッド | パス | 概要 |
| --- | --- | --- |
| `GET` | `/shifts` | シフト一覧を取得 |
| `POST` | `/shifts` | ScheduleとShiftを同時に作成 |
| `GET` | `/shifts/{schedule_id}` | シフトを1件取得 |
| `PATCH` | `/shifts/{schedule_id}` | ScheduleとShiftを同時に更新 |
| `DELETE` | `/shifts/{schedule_id}` | ShiftとScheduleを削除 |

### Accounts

| メソッド | パス | 概要 |
| --- | --- | --- |
| `GET` | `/accounts` | 資産一覧と現在残高を取得 |
| `POST` | `/accounts` | 資産を作成 |
| `GET` | `/accounts/{account_id}` | 資産を1件取得 |
| `PATCH` | `/accounts/{account_id}` | 資産を更新 |
| `DELETE` | `/accounts/{account_id}` | 資産を無効化 |

### Planned transactions

| メソッド | パス | 概要 |
| --- | --- | --- |
| `GET` | `/planned-transactions` | 収支見込一覧を取得 |
| `POST` | `/planned-transactions` | 収支見込を作成 |
| `GET` | `/planned-transactions/{planned_transaction_id}` | 収支見込を1件取得 |
| `PATCH` | `/planned-transactions/{planned_transaction_id}` | 収支見込を更新 |
| `DELETE` | `/planned-transactions/{planned_transaction_id}` | 収支見込を削除 |
| `POST` | `/planned-transactions/{planned_transaction_id}/actualize` | 見込を実績化 |

### Transactions

| メソッド | パス | 概要 |
| --- | --- | --- |
| `GET` | `/transactions` | 収支実績一覧を取得 |
| `POST` | `/transactions` | 収支実績を個別登録 |
| `GET` | `/transactions/{transaction_id}` | 収支実績を1件取得 |
| `PATCH` | `/transactions/{transaction_id}` | 収支実績を更新 |
| `DELETE` | `/transactions/{transaction_id}` | 収支実績を削除 |
| `GET` | `/finance/summary` | 残高・収支見込の集計を取得 |

### Google Calendar

| メソッド | パス | 概要 |
| --- | --- | --- |
| `GET` | `/integrations/google-calendar/status` | 連携状態を取得 |
| `POST` | `/integrations/google-calendar/connect` | OAuth連携を開始 |
| `GET` | `/integrations/google-calendar/callback` | Google OAuthコールバック |
| `DELETE` | `/integrations/google-calendar` | 連携を解除 |
| `POST` | `/integrations/google-calendar/resync` | 全予定の再同期を開始 |

以降のパスはすべて `/api/v1` を省略して記載します。

## 6. Schedules API

### 6.1 Scheduleレスポンス

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `id` | integer | スケジュールID |
| `title` | string | タイトル。1〜200文字 |
| `description` | string / null | 詳細。最大2000文字 |
| `start_at` | datetime | 開始日時 |
| `end_at` | datetime | 終了日時 |
| `kind` | string | `event`、`task`、`shift`、`payment` |
| `category` | string / null | ユーザー向け分類 |
| `task` | object / null | Taskの詳細 |
| `shift` | object / null | Shiftの詳細 |
| `google_sync_status` | string | `not_connected`、`pending`、`synced`、`failed` |
| `created_at` | datetime | 作成日時 |
| `updated_at` | datetime | 更新日時 |

### 6.2 予定一覧取得

```http
GET /schedules?from=2026-09-01T00:00:00%2B09:00&to=2026-10-01T00:00:00%2B09:00
```

| クエリ | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `from` | datetime | はい | 表示期間の開始 |
| `to` | datetime | はい | 表示期間の終了。境界は含まない |
| `kind` | string | いいえ | 種別で絞り込み。複数指定可 |
| `category` | string | いいえ | カテゴリで絞り込み |

期間と少なくとも一部が重なる予定を、`start_at` の昇順で返します。

#### 成功レスポンス

`200 OK`

```json
{
  "items": [
    {
      "id": 10,
      "title": "ソフトウェア演習",
      "description": "第3回",
      "start_at": "2026-09-08T09:00:00+09:00",
      "end_at": "2026-09-08T10:30:00+09:00",
      "kind": "event",
      "category": "class",
      "task": null,
      "shift": null,
      "google_sync_status": "synced",
      "created_at": "2026-09-01T10:00:00Z",
      "updated_at": "2026-09-01T10:00:00Z"
    }
  ],
  "next_cursor": null
}
```

### 6.3 通常予定・支払い予定作成

```http
POST /schedules
```

#### リクエスト

```json
{
  "title": "ゼミ",
  "description": "進捗発表",
  "start_at": "2026-09-10T13:00:00+09:00",
  "end_at": "2026-09-10T14:30:00+09:00",
  "kind": "event",
  "category": "class"
}
```

`kind=task` は `POST /tasks`、`kind=shift` は `POST /shifts` を使います。
これによりScheduleと拡張データを1回のトランザクションで作成します。

#### バリデーション

- `end_at` は `start_at` より後であること
- `kind` は `event` または `payment` であること
- `title` は1〜200文字であること

#### 成功レスポンス

`201 Created`。本文はScheduleレスポンスです。

### 6.4 予定1件取得

```http
GET /schedules/{schedule_id}
```

`kind=task` の場合は `task`、`kind=shift` の場合は `shift` に詳細を含めます。

### 6.5 予定更新

```http
PATCH /schedules/{schedule_id}
```

#### リクエスト

```json
{
  "title": "ゼミ（教室変更）",
  "start_at": "2026-09-10T14:00:00+09:00",
  "end_at": "2026-09-10T15:30:00+09:00"
}
```

指定したフィールドだけを更新します。`kind` は作成後に変更できません。
TaskまたはShift固有の情報は、それぞれのAPIで更新します。

### 6.6 予定削除

```http
DELETE /schedules/{schedule_id}
```

`204 No Content` を返します。関連するTaskまたはShiftも同時に削除します。
関連する収支見込は金銭情報を守るため削除せず、`schedule_id` を `null` にします。
収支実績も、元の収支見込との関係を維持したまま残します。

## 7. Tasks API

Taskは単独では存在せず、`kind=task` のScheduleと同じ `schedule_id` を主キーとして持ちます。

### 7.1 タスク一覧取得

```http
GET /tasks?done=false&due_to=2026-09-30T23:59:59%2B09:00
```

| クエリ | 型 | 説明 |
| --- | --- | --- |
| `done` | boolean | 完了状態 |
| `due_from` | datetime | 期限の開始 |
| `due_to` | datetime | 期限の終了 |
| `category` | string | Scheduleのカテゴリ |

期限の昇順で返します。

### 7.2 タスク作成

```http
POST /tasks
```

#### リクエスト

```json
{
  "schedule": {
    "title": "レポート提出",
    "description": "確率論レポート",
    "start_at": "2026-09-08T18:00:00+09:00",
    "end_at": "2026-09-08T19:00:00+09:00",
    "category": "assignment"
  },
  "due_date": "2026-09-12T23:59:00+09:00"
}
```

`kind` はサーバー側で `task`、`done_flag` は `false` に設定します。

#### 成功レスポンス

`201 Created`

```json
{
  "schedule_id": 11,
  "due_date": "2026-09-12T23:59:00+09:00",
  "done_flag": false,
  "schedule": {
    "id": 11,
    "title": "レポート提出",
    "description": "確率論レポート",
    "start_at": "2026-09-08T18:00:00+09:00",
    "end_at": "2026-09-08T19:00:00+09:00",
    "kind": "task",
    "category": "assignment",
    "google_sync_status": "pending",
    "created_at": "2026-09-02T04:00:00Z",
    "updated_at": "2026-09-02T04:00:00Z"
  }
}
```

### 7.3 タスク取得・更新・削除

```http
GET /tasks/{schedule_id}
PATCH /tasks/{schedule_id}
DELETE /tasks/{schedule_id}
```

PATCHではTaskとScheduleの項目を同時に更新できます。

```json
{
  "done_flag": true,
  "due_date": "2026-09-13T23:59:00+09:00",
  "schedule": {
    "title": "レポート提出済み"
  }
}
```

DELETEはTaskだけでなく、対応するScheduleも削除して `204 No Content` を返します。

## 8. Shifts API

Shiftは単独では存在せず、`kind=shift` のScheduleと同じ `schedule_id` を主キーとして持ちます。

### 8.1 シフト一覧取得

```http
GET /shifts?from=2026-09-01T00:00:00%2B09:00&to=2026-10-01T00:00:00%2B09:00
```

Scheduleの `start_at` の昇順で返します。

### 8.2 シフト作成

```http
POST /shifts
```

#### リクエスト

```json
{
  "schedule": {
    "title": "カフェ勤務",
    "description": null,
    "start_at": "2026-09-15T10:00:00+09:00",
    "end_at": "2026-09-15T18:00:00+09:00",
    "category": "part_time"
  },
  "hourly_wage": 1300,
  "break_minutes": 60,
  "workplace": "新宿店"
}
```

`kind` はサーバー側で `shift` に設定します。

#### バリデーション

- `hourly_wage` は0以上の整数
- `break_minutes` は0以上で、勤務時間を超えない整数
- `workplace` は最大200文字

#### 成功レスポンス

`201 Created`

```json
{
  "schedule_id": 12,
  "hourly_wage": 1300,
  "break_minutes": 60,
  "workplace": "新宿店",
  "estimated_income": 9100,
  "schedule": {
    "id": 12,
    "title": "カフェ勤務",
    "description": null,
    "start_at": "2026-09-15T10:00:00+09:00",
    "end_at": "2026-09-15T18:00:00+09:00",
    "kind": "shift",
    "category": "part_time",
    "google_sync_status": "pending",
    "created_at": "2026-09-02T04:00:00Z",
    "updated_at": "2026-09-02T04:00:00Z"
  }
}
```

`estimated_income` は
`(勤務時間（分）- break_minutes) × hourly_wage ÷ 60` を1円単位で算出した読み取り専用フィールドです。
端数の丸め方法は実装前に確定します。

### 8.3 シフト取得・更新・削除

```http
GET /shifts/{schedule_id}
PATCH /shifts/{schedule_id}
DELETE /shifts/{schedule_id}
```

PATCHではShiftとScheduleの項目を同時に更新できます。

```json
{
  "hourly_wage": 1350,
  "break_minutes": 60,
  "schedule": {
    "end_at": "2026-09-15T19:00:00+09:00"
  }
}
```

DELETEはShiftだけでなく、対応するScheduleも削除して `204 No Content` を返します。

## 9. Accounts API

### 9.1 Accountのデータ構造

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `id` | integer | 資産ID |
| `name` | string | 資産名。1〜100文字 |
| `type` | string | `cash`、`bank`、`e_money`、`other` |
| `initial_balance` | integer | 登録時点の初期残高 |
| `current_balance` | integer | 初期残高と収支実績から計算した現在残高 |
| `is_active` | boolean | 現在使用している資産か |
| `created_at` | datetime | 作成日時 |
| `updated_at` | datetime | 更新日時 |

`current_balance` は次の式で計算し、DBには保存しません。

```text
initial_balance
+ incomeのTransaction合計
- expenseのTransaction合計
```

### 9.2 資産一覧・取得

```http
GET /accounts?is_active=true
GET /accounts/{account_id}
```

### 9.3 資産作成

```http
POST /accounts
```

```json
{
  "name": "生活用口座",
  "type": "bank",
  "initial_balance": 120000
}
```

成功時は `201 Created` とAccountレスポンスを返します。

### 9.4 資産更新

```http
PATCH /accounts/{account_id}
```

```json
{
  "name": "メイン口座",
  "is_active": true
}
```

`initial_balance` の変更は過去のすべての残高に影響するため、初回登録後は変更不可とします。
残高を訂正する場合はTransactionとして調整額を登録します。

### 9.5 資産削除

```http
DELETE /accounts/{account_id}
```

取引履歴を保護するため物理削除せず、`is_active=false` に更新して `204 No Content` を返します。

## 10. Planned Transactions API

収支見込は、将来発生する予定の収入・支出です。Scheduleと関連しない単独の見込も登録できます。

### 10.1 データ構造

| フィールド | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `id` | integer | レスポンスのみ | 取引予定ID |
| `schedule_id` | integer / null | いいえ | 関連するSchedule |
| `account_id` | integer / null | いいえ | 入出金予定のAccount |
| `type` | string | はい | `income` または `expense` |
| `amount` | integer | はい | 1以上の金額 |
| `expected_date` | date | はい | 取引予定日 |
| `description` | string / null | いいえ | 詳細。最大1000文字 |
| `actualized` | boolean | レスポンスのみ | 実績化済みか |
| `created_at` | datetime | レスポンスのみ | 作成日時 |
| `updated_at` | datetime | レスポンスのみ | 更新日時 |

### 10.2 一覧取得

```http
GET /planned-transactions?from=2026-09-01&to=2026-09-30&type=expense&actualized=false
```

`account_id`、`schedule_id` でも絞り込めます。`expected_date` の昇順で返します。

### 10.3 作成

```http
POST /planned-transactions
```

```json
{
  "schedule_id": 12,
  "account_id": 3,
  "type": "income",
  "amount": 9100,
  "expected_date": "2026-09-25",
  "description": "9月15日 カフェ勤務分"
}
```

成功時は `201 Created` を返します。`schedule_id` と `account_id` は、指定した場合に自分のリソースである必要があります。

### 10.4 取得・更新・削除

```http
GET /planned-transactions/{planned_transaction_id}
PATCH /planned-transactions/{planned_transaction_id}
DELETE /planned-transactions/{planned_transaction_id}
```

実績化済みの収支見込は変更・削除できず、`409 Conflict` を返します。

### 10.5 実績化

```http
POST /planned-transactions/{planned_transaction_id}/actualize
```

収支見込から収支実績を1件作成します。

```json
{
  "account_id": 3,
  "amount": 9200,
  "category": "salary",
  "description": "9月15日 カフェ勤務分",
  "occurred_at": "2026-09-25T12:00:00+09:00"
}
```

`type` は収支見込から引き継ぎます。`amount` と `description` は実績値で上書きできます。
作成したTransactionの `planned_transaction_id` を設定します。元の収支見込に
`schedule_id` がある場合の `source` は `schedule`、ない場合は `planned_transaction` とします。

成功時は `201 Created` とTransactionレスポンスを返します。同じ見込を複数回実績化しようとした場合は
`409 Conflict` を返します。

### 10.6 スケジュールから収支を登録する流れ

予定から収支を登録する場合は、次の関連を使います。

1. Schedule、TaskまたはShiftを作成する
2. 必要な場合だけ、`schedule_id` を指定してPlannedTransactionを作成する
3. 金額が確定したら、PlannedTransactionを実績化してTransactionを作成する

支払い予定やシフトに収支見込が不要な場合は、手順2以降を省略できます。
Scheduleと関連しない実績は `POST /transactions` で個別登録します。

## 11. Transactions API

### 11.1 データ構造

| フィールド | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `id` | integer | レスポンスのみ | 取引ID |
| `account_id` | integer | はい | 入出金先のAccount |
| `planned_transaction_id` | integer / null | レスポンスのみ | 元の収支見込 |
| `type` | string | はい | `income` または `expense` |
| `amount` | integer | はい | 1以上の金額 |
| `category` | string / null | いいえ | ユーザー向け分類 |
| `description` | string / null | いいえ | 詳細。最大1000文字 |
| `source` | string | レスポンスのみ | `manual`、`schedule`、`planned_transaction` |
| `occurred_at` | datetime | はい | 取引発生日時 |
| `created_at` | datetime | レスポンスのみ | 作成日時 |
| `updated_at` | datetime | レスポンスのみ | 更新日時 |

金額は常に正数とし、加算・減算は `type` で判断します。

### 11.2 一覧取得

```http
GET /transactions?from=2026-09-01T00:00:00%2B09:00&to=2026-10-01T00:00:00%2B09:00
```

`account_id`、`type`、`category`、`source` でも絞り込めます。
`occurred_at` の降順で返します。

### 11.3 個別登録

```http
POST /transactions
```

```json
{
  "account_id": 3,
  "type": "expense",
  "amount": 850,
  "category": "food",
  "description": "昼食",
  "occurred_at": "2026-09-02T12:30:00+09:00"
}
```

成功時は `201 Created` を返し、`source` はサーバー側で `manual` に設定します。

### 11.4 取得・更新・削除

```http
GET /transactions/{transaction_id}
PATCH /transactions/{transaction_id}
DELETE /transactions/{transaction_id}
```

Transactionを更新・削除すると、そのAccountの `current_balance` に直ちに反映されます。
収支見込から作られたTransactionを削除した場合、元の収支見込は未実績化状態へ戻します。

## 12. Finance Summary API

```http
GET /finance/summary?as_of=2026-09-30
```

#### 成功レスポンス

`200 OK`

```json
{
  "as_of": "2026-09-30",
  "current_balance": 245000,
  "planned_income": 85000,
  "planned_expense": 32000,
  "projected_balance": 298000,
  "accounts": [
    {
      "account_id": 3,
      "name": "メイン口座",
      "current_balance": 220000,
      "projected_balance": 273000
    },
    {
      "account_id": 4,
      "name": "現金",
      "current_balance": 25000,
      "projected_balance": 25000
    }
  ]
}
```

```text
projected_balance
= current_balance
+ as_ofまでの未実績化planned_income
- as_ofまでの未実績化planned_expense
```

`account_id=null` の収支見込は全体の見込には含めますが、口座別の見込には含めません。

## 13. Google Calendar連携

同期方向は `Taskal → Google Calendar` のみです。Google Calendar側での変更はTaskalへ取り込みません。

### 13.1 連携状態取得

```http
GET /integrations/google-calendar/status
```

```json
{
  "connected": true,
  "calendar_id": "primary",
  "last_synced_at": "2026-09-02T05:00:00Z"
}
```

### 13.2 連携開始

```http
POST /integrations/google-calendar/connect
```

```json
{
  "redirect_uri": "https://app.taskal.example/settings/integrations"
}
```

`200 OK`

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

フロントエンドは `authorization_url` へ遷移します。Googleからのコールバックは次のAPIが受け取ります。

```http
GET /integrations/google-calendar/callback?code=...&state=...
```

コールバック成功時は保存していた `redirect_uri` へ `302 Found` でリダイレクトします。
`redirect_uri` は事前に許可したTaskalフロントエンドのURLだけを受け付けます。

### 13.3 連携解除

```http
DELETE /integrations/google-calendar
```

Googleの認可を取り消し、保存済みトークンを削除します。既に作成されたGoogle Calendarイベントは削除しません。

### 13.4 再同期

```http
POST /integrations/google-calendar/resync
```

`202 Accepted`

```json
{
  "status": "accepted"
}
```

### 13.5 自動同期

Scheduleの作成・更新・削除時に、対応するGoogle Calendarイベントを非同期で作成・更新・削除します。

- TaskalのDB更新を先に確定する
- 同期処理中は `google_sync_status=pending`
- 成功時は `synced`
- 失敗時は `failed` とし、自動リトライまたは再同期の対象にする
- Google Calendarの障害によってTaskal上の予定作成を失敗させない

## 14. 主な業務ルール

### Schedule

- `end_at > start_at`
- `kind` は作成後に変更不可
- `kind=task` にはTaskが必ず1件存在
- `kind=shift` にはShiftが必ず1件存在
- TaskとShiftを同じScheduleへ同時に設定できない

### Account・収支

- 金額はすべて1円単位の整数
- PlannedTransactionとTransactionの `amount` は1以上
- 指定するAccount、Schedule、PlannedTransactionはすべて自分の所有物であること
- 実績化済みのPlannedTransactionは変更・削除不可
- Accountは履歴保護のため物理削除しない
- 残高はTransactionから都度計算し、PlannedTransactionは現在残高に含めない

### 削除

- Schedule削除時はTaskまたはShiftをCASCADE削除
- Schedule削除時、PlannedTransactionの `schedule_id` は `null` にする
- Account削除時は `is_active=false` にする
- ユーザー所有リソースの一括削除方針は別途定める

## 15. その他考慮すべき事項

### 15.1 Schedule削除時の金融データ

金融履歴を残すには、PLANNED_TRANSACTIONSの `schedule_id` をnullableにし、
外部キーを `ON DELETE SET NULL` とする必要があります。

### 15.2 Google Calendar連携情報

現行ER図にはGoogle連携情報がありません。少なくとも次の保存領域が必要です。

- Google Calendar接続情報
- 暗号化したRefresh Token
- 対象Calendar ID
- Scheduleに対応するGoogle Event ID
- `google_sync_status`
- 最終同期日時
- 非同期リトライ用のOutboxまたはJob

しかし、最初からは連携機能を実装しないので今はこのままでOK。

### 15.3 列挙値とDB制約

次の値はAPIとDBの両方で制約をそろえる必要があります。

- `schedules.kind`: `event`、`task`、`shift`、`payment`
- `planned_transactions.type`: `income`、`expense`
- `transactions.type`: `income`、`expense`
- `transactions.source`: `manual`、`schedule`、`planned_transaction`
- `accounts.type`: `cash`、`bank`、`e_money`、`other`

### 15.4 その他設計事項

- Shiftの見込収入に端数が出た場合の丸め方法
- `category` はユーザー定義マスタを作る
- Google Calendar連携解除時に既存イベントを残す
- ユーザー退会時の金融履歴とGoogle Calendarイベントの扱いは削除する
- 定期的な予定、サブスクリプションの繰り返しルールは今は考えずに実行
- タイムゾーンをユーザーごとに設定する

## 16. バックエンドの責務

`architecture.md` のレイヤー構成に従い、各層は次を担当します。

| 層 | 主な責務 |
| --- | --- |
| Router | HTTP入出力、認証依存、ステータスコード |
| Service | 業務ルール、複数リソースのトランザクション制御 |
| Repository | SQLAlchemyを使ったDBアクセス |
| Integration | Google Calendar APIとの通信 |

Task・ShiftとScheduleの同時作成、収支見込の実績化など、複数テーブルを変更する処理は
Service層で1つのDBトランザクションとして実行します。
