// バックエンドの backend/app/schemas/task.py に対応する型

// 日付は "YYYY-MM-DD" 形式の文字列
export type DateString = string

// POST /api/tasks のリクエスト（TaskCreate）
export interface TaskCreate {
  title: string // 1〜200文字
  description: string // 1000文字まで
  limit: DateString
}

// PUT /api/tasks/{task_id} のリクエスト（TaskUpdate）
export type TaskUpdate = TaskCreate

// タスクAPIのレスポンス（TaskResponse）
export interface Task {
  id: number
  owner_id: number
  title: string
  description: string
  limit: DateString
  done_flag: boolean
}
